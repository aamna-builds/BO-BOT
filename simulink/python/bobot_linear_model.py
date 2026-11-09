"""BO-BOT linear model, controller analysis and graphs.

Builds the small-angle model of the robot (a wheeled inverted pendulum with DC-motor drive), closes the
same control law as the firmware, and writes the graphs to ../results/. The MATLAB script bobot_analysis.m
does the same calculation, so the two can be compared.

Run:  python bobot_linear_model.py          (needs numpy, scipy, matplotlib)
"""
import csv, os, json
import numpy as np
import scipy.signal as sg
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results")
DATA = os.path.join(HERE, "..", "data")
os.makedirs(OUT, exist_ok=True)
D2R = np.pi / 180.0

# ---------------------------------------------------------------- parameters (same values as simulation/web/index.html)
g = 9.81
mb, mw = 0.1925, 0.0032            # body mass (no shell), wheel mass, kg
l, e = 0.023733506, 0.000301299    # centre of mass above the axle / ahead of it, m
Iyy = 1.12044568e-4                # body pitch inertia about its centre of mass, kg m^2
r, track = 0.017, 0.078            # wheel radius, wheel spacing, m
Iwa = 4.964e-7                     # wheel inertia about its axle, kg m^2
# motor (GA12-N20, 6 V, 300 rpm, 50:1)
R, gear = 6.0 / 0.55, 50.0
w_nl = 300 * gear * 2 * np.pi / 60
Ke = (6.0 - 0.04 * R) / w_nl       # V s/rad at the motor shaft (= Nm/A); w_nl is the motor-shaft speed
eta = 0.7047695986087725           # gearbox efficiency (from stall torque 0.70 kg cm)
Jm = 2.5e-8 * gear ** 2            # rotor inertia reflected to the wheel, kg m^2
Vb = 8.3                           # battery voltage, V (2S, about 95 % charged)

# firmware gains (firmware/balance_bot/include/controller.h)
kp, kd, ki = 55.0, 0.35, 0.0       # PWM per deg, per deg/s
kp_v, ki_v = 20.0, 0.9             # deg of lean per m/s, per metre
kff = 1.0

# ---------------------------------------------------------------- model
# state x = [v, phi, phid]: wheel-axle speed (m/s), body angle from the balance point (rad), its rate (rad/s)
#   M [vdot, phiddot]' = [ Tt/r , -Tt + m g l phi ]'
#   Tt = k1 Vb u - k1 ke v / r + k1 ke phid           (total drive torque on both wheels, N m)
M00 = 2 * Iwa / r**2 + mb + 2 * mw + 2 * Jm / r**2
M01 = l * mb - 2 * Jm / r
M11 = Iyy + e**2 * mb + l**2 * mb + 2 * Jm
Mm = np.array([[M00, M01], [M01, M11]])
k1 = 2 * eta * gear * Ke / R       # N m per volt at standstill (both wheels)
ke = gear * Ke                     # back-EMF constant at the wheel (V s/rad)

# Tt = a_v v + a_p phid + b u
a_v, a_p, b_u = -k1 * ke / r, k1 * ke, k1 * Vb
F_v = np.array([a_v / r, -a_v])                 # how v enters the force vector
F_p = np.array([a_p / r, -a_p])                 # how phid enters
F_phi = np.array([0.0, g * mb * l])             # gravity term, multiplies phi
F_u = np.array([b_u / r, -b_u])                 # how u (duty, -1..1) enters
Minv = np.linalg.inv(Mm)
# state order [v, phi, phid]: rows are vdot, phid (kinematic), phiddot
A = np.array([
    [(Minv @ F_v)[0], (Minv @ F_phi)[0], (Minv @ F_p)[0]],
    [0.0, 0.0, 1.0],
    [(Minv @ F_v)[1], (Minv @ F_phi)[1], (Minv @ F_p)[1]],
])
B = np.array([[(Minv @ F_u)[0]], [0.0], [(Minv @ F_u)[1]]])

# ---------------------------------------------------------------- controller (same law as the firmware, small-signal)
# duty u = ( kp*(phi_deg - target) + kd*phid_deg ) / 255 + kff * vcmd * emf / Vb
# target = kp_v*(vcmd - vhat) + ki_v*xi,   xi' = vcmd - vhat
# vhat is the firmware's speed estimate: a 5-sample average (about 10 ms delay) then a 0.3 low-pass (11.7 ms), so one lag of tau_v.
# Leaving this lag out gives a wrong (unstable) answer: it is part of why the speed loop is stable.
emf = ke / r                                       # V per m/s
s2d = 1.0 / D2R
tau_v = 0.0217
# augmented state z = [v, phi, phid, xi, vhat]
Aa = np.zeros((5, 5)); Aa[:3, :3] = A; Aa[3, 4] = -1.0; Aa[4, 0] = 1 / tau_v; Aa[4, 4] = -1 / tau_v
Ba = np.zeros((5, 1)); Ba[:3, 0:1] = B
Bv = np.zeros((5, 1)); Bv[3, 0] = 1.0              # vcmd into xi'


def make_K(kp_, kd_, kpv_, kiv_):
    """u = Kz z + Kv vcmd"""
    Kz_ = np.array([[0.0, kp_ * s2d / 255, kd_ * s2d / 255, -kp_ * kiv_ / 255, kp_ * kpv_ / 255]])
    Kv_ = np.array([[-kp_ * kpv_ / 255 + kff * emf / Vb]])
    return Kz_, Kv_


# Control output reaches the motors late: 1 ms output delay plus on average half of the 5 ms control period.
# The delay is modelled with a first-order Pade approximation, y = 2 xd - u,  xd' = (2/Td)(u - xd).
Td = 0.0035


def closed(kp_, kd_, kpv_, kiv_, vscale=1.0):
    """Closed-loop matrices with the delay. State = [v, phi, phid, xi, vhat, xd]; input = vcmd."""
    Kz_, Kv_ = make_K(kp_, kd_, kpv_, kiv_)
    Bp = Ba * vscale
    Ac = np.zeros((6, 6)); Bc = np.zeros((6, 1))
    Ac[:5, :5] = Aa - Bp @ Kz_; Ac[:5, 5:6] = 2 * Bp
    Ac[5, :5] = (2 / Td) * Kz_[0]; Ac[5, 5] = -2 / Td
    Bc[:5] = Bv - Bp @ Kv_; Bc[5, 0] = (2 / Td) * Kv_[0, 0]
    return Ac, Bc, Kz_, Kv_


Acl, Bcl, Kz, Kv = closed(kp, kd, kp_v, ki_v)


def lin_sim(Ac, Bc, t, x0, ucmd=None):
    sys = sg.StateSpace(Ac, Bc, np.eye(Ac.shape[0]), np.zeros((Ac.shape[0], 1)))
    u = np.zeros_like(t) if ucmd is None else ucmd
    _, _, x = sg.lsim(sys, u, t, X0=x0)
    return x


def load(name):
    with open(os.path.join(DATA, name)) as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 130,
                     "axes.spines.top": False, "axes.spines.right": False})
C = {"a": "#d9442f", "b": "#2b8fd6", "c": "#7a5bc0", "d": "#2f9e6a", "k": "#444"}

# ---------------------------------------------------------------- numbers
ol = np.linalg.eigvals(A)
cl = np.linalg.eigvals(Acl)
summary = {
    "M": Mm.tolist(), "k1_Nm_per_V": k1, "ke_Vs_per_rad": ke, "emf_V_per_mps": emf,
    "A": A.tolist(), "B": B.flatten().tolist(),
    "open_loop_poles": [complex(x).__repr__() for x in ol],
    "closed_loop_poles": [complex(x).__repr__() for x in cl],
}
print("open-loop poles:", np.round(ol, 3))
print("closed-loop poles:", np.round(cl, 3))

# ---------------------------------------------------------------- figure 1: pole map
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].axhline(0, color="#999", lw=0.8); ax[0].axvline(0, color="#999", lw=0.8)
ax[0].plot(ol.real, ol.imag, "x", ms=10, mew=2, color=C["a"], label="open loop")
ax[0].set_title("Open-loop poles (no controller)"); ax[0].set_xlabel("real (1/s)"); ax[0].set_ylabel("imaginary (rad/s)")
for p in ol:
    ax[0].annotate(f"{p.real:.1f}", (p.real, p.imag), textcoords="offset points", xytext=(6, 6), fontsize=8)
ax[0].legend()
ax[1].axhline(0, color="#999", lw=0.8); ax[1].axvline(0, color="#999", lw=0.8)
ax[1].plot(cl.real, cl.imag, "x", ms=10, mew=2, color=C["b"], label="closed loop (firmware gains)")
ax[1].set_title("Closed-loop poles (a fast delay pole near -504 is off the left edge)", fontsize=9); ax[1].set_xlabel("real (1/s)"); ax[1].set_xlim(-110, 10)
for p in cl:
    ax[1].annotate(f"{p.real:.1f}{p.imag:+.1f}j" if abs(p.imag) > 1e-6 else f"{p.real:.1f}", (p.real, p.imag), textcoords="offset points", xytext=(6, 6), fontsize=8)
ax[1].legend()
fig.suptitle("Why the robot needs a controller: one open-loop pole is in the right half plane")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_poles.png")); plt.close(fig)

# ---------------------------------------------------------------- figure 2: validation against the nonlinear simulator
sim = load("sim_initial_tilt.csv")
t = sim["t_s"]
ss = sim["pitch_deg"][-100:].mean()                # the simulator settles about 1 deg off (sensor mount error)
x0 = np.array([0.0, (sim["pitch_deg"][0] - ss) * D2R, 0.0, 0.0, 0.0, 0.0])
xl = lin_sim(Acl, Bcl, t, x0)
fig, ax = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True)
ax[0].plot(t, sim["pitch_deg"] - ss, color=C["a"], lw=1.8, label="nonlinear simulator")
ax[0].plot(t, xl[:, 1] / D2R, "--", color=C["b"], lw=1.8, label="linear model")
ax[0].set_ylabel("pitch from rest (deg)"); ax[0].legend()
ax[1].plot(t, sim["speed_mps"], color=C["a"], lw=1.8, label="nonlinear simulator")
ax[1].plot(t, xl[:, 0], "--", color=C["b"], lw=1.8, label="linear model")
ax[1].set_ylabel("speed (m/s)"); ax[1].set_xlabel("time (s)")
fig.suptitle("Recovery from a 3 degree tilt: linear model against the simulator")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_tilt_recovery_validation.png")); plt.close(fig)
err = np.sqrt(np.mean((sim["pitch_deg"] - ss - xl[:, 1] / D2R) ** 2))
print(f"RMS pitch difference linear vs simulator: {err:.2f} deg")
summary["validation_rms_pitch_deg"] = float(err)

# ---------------------------------------------------------------- figure 3: speed command step
t2 = np.linspace(0, 4, 800)
vc = np.minimum(0.2, 0.6 * t2)           # the firmware ramps the speed command at 0.6 m/s per second
xs = lin_sim(Acl, Bcl, t2, np.zeros(6), vc)
u_duty = (Kz @ xs[:, :5].T).flatten() + (Kv * vc).flatten()
sim2 = load("sim_speed_step.csv")
fig, ax = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
ax[0].plot(t2, vc, color="#888", lw=1.2, label="command"); ax[0].plot(t2, xs[:, 0], "--", color=C["b"], lw=1.8, label="linear model")
ax[0].plot(sim2["t_s"], sim2["speed_mps"], color=C["a"], lw=1.6, label="nonlinear simulator"); ax[0].set_ylabel("speed (m/s)"); ax[0].legend()
ax[1].plot(t2, xs[:, 1] / D2R, "--", color=C["b"], lw=1.8); ax[1].plot(sim2["t_s"], sim2["pitch_deg"] - sim2["pitch_deg"][0], color=C["a"], lw=1.6)
ax[1].set_ylabel("pitch change (deg)")
ax[2].plot(t2, u_duty * 255, "--", color=C["b"], lw=1.8); ax[2].set_ylabel("PWM (of 255)"); ax[2].set_xlabel("time (s)")
fig.suptitle("Speed command 0 to 0.2 m/s (ramped at 0.6 m/s per second, as in the firmware)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "03_speed_step.png")); plt.close(fig)

# ---------------------------------------------------------------- figure 4: angle-loop Bode and margins
# Loop broken at the motor input. Only the angle loop (kp, kd) is considered; delay = 1 ms output delay + half a 5 ms sample.
Kang = np.array([[kp * s2d / 255, kd * s2d / 255]])
w = np.logspace(0, 3, 2000)
G = np.zeros_like(w, dtype=complex)
for i, wi in enumerate(w):
    xi = np.linalg.solve(1j * wi * np.eye(3) - A, B).flatten()   # angle loop only: speed loop open
    G[i] = -(Kang @ xi[1:3])[0]
Ld = G * np.exp(-1j * w * Td)


def margins(L):
    mag = np.abs(L); ph = np.unwrap(np.angle(L)) * 180 / np.pi
    out = {}
    idx = np.where((mag[:-1] > 1) & (mag[1:] <= 1))[0]
    if len(idx):
        i = idx[0]; out["wc"] = w[i]; out["pm"] = 180 + ph[i]
    return out, ph


mg0, ph0 = margins(G); mg1, ph1 = margins(Ld)
fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
ax[0].semilogx(w, 20 * np.log10(np.abs(G)), color=C["b"], lw=1.8); ax[0].axhline(0, color="#999", lw=0.8)
ax[0].set_ylabel("magnitude (dB)")
ax[1].semilogx(w, ph0, color=C["b"], lw=1.8, label="no delay")
ax[1].semilogx(w, ph1, color=C["a"], lw=1.8, label=f"with {Td * 1000:.1f} ms delay")
ax[1].axhline(-180, color="#999", lw=0.8); ax[1].set_ylabel("phase (deg)"); ax[1].set_xlabel("frequency (rad/s)"); ax[1].legend()
txt = []
if "wc" in mg0: txt.append(f"crossover {mg0['wc']:.0f} rad/s, phase margin {mg0['pm']:.0f} deg (no delay)")
if "wc" in mg1: txt.append(f"with delay: crossover {mg1['wc']:.0f} rad/s, phase margin {mg1['pm']:.0f} deg")
fig.suptitle("Angle loop (kp, kd) opened at the motor input\n" + "; ".join(txt), fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "04_angle_loop_bode.png")); plt.close(fig)
print("angle loop margins:", mg0, mg1)
summary["angle_loop_margins"] = {"no_delay": {k: float(v) for k, v in mg0.items()}, "with_delay": {k: float(v) for k, v in mg1.items()}}

# ---------------------------------------------------------------- figure 5: gain sweep (root locus style)
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
kps = np.linspace(0, 150, 301); pts = []
for kpi in kps:
    pts.append(np.linalg.eigvals(closed(kpi, kd, kp_v, ki_v)[0]))
pts = np.array(pts)
stable = np.all(pts.real < 0, axis=1)
sc = ax[0].scatter(pts.real.flatten(), pts.imag.flatten(), c=np.repeat(kps, 6), s=7, cmap="viridis")
ax[0].axvline(0, color="#999"); ax[0].set_xlabel("real (1/s)"); ax[0].set_ylabel("imaginary (rad/s)"); ax[0].set_title("Closed-loop poles as kp goes 0 to 150")
ax[0].set_xlim(-60, 10); plt.colorbar(sc, ax=ax[0], label="kp")
kmin = kps[stable][0] if stable.any() else None
ax[0].set_xlabel("real (1/s)")
kds = np.linspace(0, 1.2, 241); mx = []
for kdi in kds:
    mx.append(np.max(np.linalg.eigvals(closed(kp, kdi, kp_v, ki_v)[0]).real))
ax[1].plot(kds, mx, color=C["b"], lw=1.8); ax[1].axhline(0, color="#999", lw=0.8)
ax[1].axvline(kd, color=C["a"], ls="--", label=f"firmware kd = {kd}")
ax[1].set_xlabel("kd"); ax[1].set_ylabel("largest real part of any pole (1/s)"); ax[1].set_ylim(-1, 3); ax[1].legend()
ax[1].set_title("Stability against kd (kp = 55)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "05_gain_sweeps.png")); plt.close(fig)
kmax = kps[stable][-1] if stable.any() else None
kd_ok = kds[np.array(mx) < 0]
summary["stable_kp_range"] = [float(kmin), float(kmax)] if kmin is not None else None
summary["min_stable_kd"] = float(kd_ok[0]) if len(kd_ok) else None
print("stable kp range:", kmin, "to", kmax, "| smallest stable kd:", summary["min_stable_kd"])

# ---------------------------------------------------------------- figure 6: battery voltage / mass sensitivity
fig, ax = plt.subplots(figsize=(7, 4))
for Vbi, c_ in [(8.4, C["a"]), (7.4, C["b"]), (6.8, C["c"])]:
    p_ = np.linalg.eigvals(closed(kp, kd, kp_v, ki_v, vscale=Vbi / Vb)[0])
    ax.plot(p_.real, p_.imag, "x", ms=9, mew=2, color=c_, label=f"{Vbi} V")
ax.axvline(0, color="#999"); ax.set_xlabel("real (1/s)"); ax.set_ylabel("imaginary (rad/s)"); ax.legend(title="battery")
ax.set_title("Closed-loop poles as the battery runs down"); ax.set_xlim(-110, 5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "06_battery_sensitivity.png")); plt.close(fig)

# ---------------------------------------------------------------- nonlinear planar model (same equations, no small-angle step)
from scipy.integrate import solve_ivp
PWM_CAP, MAX_LEAN = 204.0, 10.0


def nonlin_rhs(t, z, vcmd=0.0):
    v, th, thd, xi, vh, xd = z
    phi = th + e / l                                   # controller measures angle from the balance point
    s_, c_ = np.sin(th), np.cos(th)
    target = np.clip(kp_v * (vcmd - vh) + ki_v * xi, -MAX_LEAN, MAX_LEAN)
    pwm = kp * (phi * s2d - target) + kd * thd * s2d + kff * vcmd * emf / Vb * 255
    u = np.clip(pwm, -PWM_CAP, PWM_CAP) / 255
    ya = 2 * xd - u                                    # delayed control (Pade)
    Tt = k1 * Vb * ya - k1 * ke * v / r + k1 * ke * thd
    m01 = c_ * l * mb - e * mb * s_ - 2 * Jm / r
    Mn = np.array([[M00, m01], [m01, M11]])
    f = np.array([Tt / r + thd ** 2 * (c_ * e + l * s_) * mb, -Tt + c_ * e * g * mb + g * l * mb * s_])
    vd, thdd = np.linalg.solve(Mn, f)
    return [vd, thd, thdd, vcmd - vh, (v - vh) / tau_v, (2 / Td) * (u - xd)]


def run_nl(th0_deg, T=2.5, vcmd=0.0):
    th0 = th0_deg * D2R - e / l
    ev = lambda t, z, *a: abs(z[1]) - 0.7              # stop when it has fallen (about 40 degrees)
    ev.terminal = True
    sol = solve_ivp(nonlin_rhs, [0, T], [0, th0, 0, 0, 0, 0], args=(vcmd,), max_step=0.002, events=ev, rtol=1e-6, atol=1e-8)
    return sol


fig, ax = plt.subplots(1, 2, figsize=(10, 4))
tt = np.linspace(0, 2.5, 1000)
for th0_, col in [(3, C["b"]), (8, C["d"]), (14, C["a"])]:
    sol = run_nl(th0_)
    ax[0].plot(sol.t, (sol.y[1] + e / l) / D2R, color=col, lw=1.8, label=f"nonlinear, start {th0_} deg")
    xl_ = lin_sim(Acl, Bcl, tt, np.array([0, th0_ * D2R, 0, 0, 0, 0]))
    ax[0].plot(tt, xl_[:, 1] / D2R, ":", color=col, lw=1.4)
ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("angle from balance point (deg)")
ax[0].set_title("Solid: nonlinear model. Dotted: linear model"); ax[0].legend(fontsize=8)
starts = np.arange(1, 39, 2.0); over = []; sat = []; fell = []
for th0_ in starts:
    sol = run_nl(th0_, T=3.0)
    fell.append(sol.status != 0 or abs((sol.y[1, -1] + e / l) / D2R) > 1.0)
    ph_ = (sol.y[1] + e / l) / D2R
    k0 = np.argmax(ph_ < 0) if (ph_ < 0).any() else len(ph_) - 1
    over.append(abs(ph_[k0:].min()) if k0 < len(ph_) - 1 else 0.0)
    pw = np.array([kp * (y[1] + e / l) * s2d + kd * y[2] * s2d for y in sol.y.T])   # angle-loop PWM request before the cap
    sat.append(100.0 * np.mean(np.abs(pw) > PWM_CAP))
ax[1].plot(starts, over, "o-", color=C["b"], lw=1.6, ms=4, label="overshoot past upright (deg)")
ax[1].set_xlabel("starting tilt (deg)"); ax[1].set_ylabel("overshoot (deg)", color=C["b"])
ax2 = ax[1].twinx(); ax2.plot(starts, sat, "s--", color=C["a"], lw=1.4, ms=4)
ax2.set_ylabel("time at the 80 % PWM limit (%)", color=C["a"]); ax2.spines["right"].set_visible(True); ax2.grid(False)
ax[1].set_title("Bigger tilts: more overshoot, motors at the limit")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "07_nonlinear_recovery.png")); plt.close(fig)
summary["tilts_that_fall_deg"] = [float(x) for x in starts[np.array(fell)]]
print("start tilts (deg) that do NOT recover in the nonlinear model:", summary["tilts_that_fall_deg"] or "none up to %g" % starts[-1])

with open(os.path.join(OUT, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print("graphs written to", os.path.abspath(OUT))
