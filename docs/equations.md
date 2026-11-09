# Equations and calculations

The balance robot is a **wheeled inverted pendulum**: a body that can tip forward and backward, sitting on two driven wheels.
This page gives the model behind the MATLAB / Simulink files in [`simulink/`](../simulink/) and the graphs in
[`simulink/results/`](../simulink/results/). Every number comes from the simulator and the firmware, so the three agree.

## 1. Symbols

| Symbol | Meaning | Value (no shell) |
|---|---|---|
| $m_b$ | body mass (everything except the wheels) | 0.1925 kg |
| $m_w$ | one wheel | 0.0032 kg |
| $l$ | centre of mass above the axle | 23.7 mm |
| $e$ | centre of mass ahead of the axle | 0.30 mm |
| $I_{yy}$ | body pitch inertia about its centre of mass | $1.12\times10^{-4}$ kg m² |
| $r$ | wheel radius | 17 mm |
| $I_{wa}$ | wheel inertia about its axle | $4.96\times10^{-7}$ kg m² |
| $J_m$ | motor rotor inertia seen at the wheel ($2.5\times10^{-8}\cdot 50^2$) | $6.25\times10^{-5}$ kg m² |
| $R$ | motor winding resistance (6 V / 0.55 A stall) | 10.9 Ω |
| $K_e = K_t$ | motor constant at the motor shaft | 3.54 mV s/rad |
| $\eta$ | gearbox efficiency (from the stall torque) | 0.70 |
| $N$ | gear ratio | 50 |
| $V_b$ | battery voltage | 8.3 V |

State: $v$ = axle speed (m/s), $\theta$ = body angle from vertical (rad, positive = leaning forward), $\dot\theta$ its rate.
The balance point is $\theta_0=-e/l$, so it is convenient to use $\varphi=\theta+e/l$, the angle **from the balance point**.

## 2. Motor

The controller sets a duty $u\in[-1,1]$ (PWM / 255), so the motor sees $uV_b$. With the wheel turning at $\omega_{rel}=v/r-\dot\theta$
relative to the body, each motor gives a wheel torque

$$T=\frac{\eta N K_t}{R}\Big(uV_b-N K_e\,\omega_{rel}\Big)$$

For both wheels, with $k_1=2\eta N K_t/R$ and $k_e=NK_e$:

$$T_t = k_1V_b\,u \;-\; \frac{k_1k_e}{r}\,v \;+\; k_1k_e\,\dot\theta$$

The middle term is the **back-EMF**: it acts like speed damping, and it is why the firmware adds a feed-forward of $v_{cmd}\,k_e/r$ volts.
Numbers: $k_1 = 0.0229$ N m/V, $k_e=0.177$ V s/rad, $k_e/r = 10.42$ V per m/s.

## 3. Equations of motion (planar)

Energy and Lagrange's equations (the simulator derives the same result with Kane's method, including steering) give

$$
\begin{bmatrix} M_{00} & M_{01}(\theta)\\ M_{01}(\theta) & M_{11}\end{bmatrix}
\begin{bmatrix}\dot v\\ \ddot\theta\end{bmatrix}=
\begin{bmatrix} T_t/r + \dot\theta^2 m_b(l\sin\theta + e\cos\theta)\\ -T_t + m_b g(l\sin\theta + e\cos\theta)\end{bmatrix}
$$

$$M_{00}=m_b+2m_w+\frac{2I_{wa}}{r^2}+\frac{2J_m}{r^2},\qquad
M_{01}=m_b(l\cos\theta-e\sin\theta)-\frac{2J_m}{r},\qquad
M_{11}=I_{yy}+m_b(l^2+e^2)+2J_m$$

Reading the equations: driving the wheels forward ($T_t>0$) accelerates the robot but also pushes the body **backward** (the $-T_t$ term).
Gravity ($m_bgl\sin\theta$) pushes a leaning body further over. This is why balancing needs a feedback loop.

## 4. Linear model

For small angles ($\sin\theta\approx\theta$, $\cos\theta\approx1$, $\dot\theta^2\approx0$), with state $x=[v,\ \varphi,\ \dot\varphi]^T$:

$$\dot x = A x + B u,\qquad A=\begin{bmatrix}-19.76&0.59&0.34\\0&0&1\\530.7&134.5&-9.02\end{bmatrix},\quad B=\begin{bmatrix}15.74\\0\\-422.8\end{bmatrix}$$

**Open-loop poles: −30.0, −9.4 and +10.6 s⁻¹.** The pole at +10.6 means a tilt grows by a factor of $e$ in about 0.09 s: the robot
falls in roughly a tenth of a second without control. See `01_poles.png`.

## 5. Control law (as in the firmware)

Every 5 ms (`controller.h`):

$$\text{target}=\mathrm{clamp}\big(k_{p,v}(v_{cmd}-\hat v)+k_{i,v}\xi,\ \pm10^\circ\big),\qquad \dot\xi=v_{cmd}-\hat v$$

$$\text{PWM}=\mathrm{clamp}\Big(k_p(\varphi^\circ-\text{target})+k_d\,\dot\varphi^\circ + 255\,k_{ff}\,v_{cmd}\tfrac{k_e/r}{V_b},\ \pm204\Big),\qquad u=\text{PWM}/255$$

with $k_p=55$, $k_d=0.35$, $k_{p,v}=20$, $k_{i,v}=0.9$, $k_{ff}=1$ (angles in degrees, as in the code).
Two details of the real implementation must be in the model, or the answer is wrong:

* **Speed estimate $\hat v$.** The firmware averages 5 samples (about 10 ms of delay) and then low-passes with a factor 0.3 (11.7 ms).
  Modelled as one lag, $\tau_v=21.7$ ms. *Without this lag the closed loop is unstable* (poles at $+3.6\pm71j$); with it, it is stable.
  The lag is what lets the outer speed loop coexist with the fast angle loop.
* **Delay.** The motor command is applied 1 ms after it is computed, and on average half a sample (2.5 ms) after the sensors were read:
  $T_d=3.5$ ms, modelled with a first-order Padé approximation.

## 6. Results

| Quantity | Value | Graph |
|---|---|---|
| Closed-loop poles | −504, −91 (fast, well damped), **−8.2 ± 52.2j** (balance mode), −1.4, −0.07 (speed and position) | `01_poles.png` |
| Balance mode | about 52 rad/s (8.3 Hz), damping ratio about 0.16 | `01_poles.png` |
| Angle loop, crossover | 72 rad/s | `04_angle_loop_bode.png` |
| Angle loop, phase margin | 46° without delay, **32° with the 3.5 ms delay** | `04_angle_loop_bode.png` |
| Stable range of $k_p$ | 16.5 to 121 (firmware uses 55) | `05_gain_sweeps.png` |
| Smallest stable $k_d$ | 0.12 (firmware uses 0.35) | `05_gain_sweeps.png` |
| Battery 8.4 V down to 6.8 V | poles barely move | `06_battery_sensitivity.png` |
| Tilt recovery (nonlinear model) | recovers from every start tilt tried, up to 37°; the motors sit at the 80 % limit for up to about 12 % of the time | `07_nonlinear_recovery.png` |

What to take from this: $k_p=55$ is comfortably inside the stable range (3.3 times the lower limit and 2.2 times below the upper limit),
$k_d=0.35$ is about three times the minimum, and the phase margin is thin enough (32°) that **extra delay hurts**: keep the control loop at 200 Hz
and avoid blocking calls in the control task.

## 7. How well the model matches the simulator

* **Speed command (`03_speed_step.png`):** the rise of the speed matches the nonlinear simulator closely. The simulator ends at about 0.165 m/s
  instead of 0.2, because the simulator has friction and a 1° sensor mounting error that the linear model leaves out.
* **Tilt recovery (`02_tilt_recovery_validation.png`):** same time scale (settles in about 0.5 s), RMS pitch difference 0.8°. The linear model
  rings more at the start. The simulator has gearbox backlash (1.5°), motor friction and stiction, which damp it and slow the recovery.
* **Not in the model:** backlash, friction, stiction, wheel slip, sensor noise, steering (yaw), and battery sag under load.
  Treat the numbers as a good first guess for tuning, not a guarantee. The real robot will differ.

## 8. Reproduce

* Python (graphs in `simulink/results/`): `python simulink/python/bobot_linear_model.py`
* MATLAB: run `bobot_analysis` in `simulink/` (needs the Control System Toolbox, R2018b or newer)
* Simulink: run `build_bobot_model`, then open `bobot_balance.slx` and press Run
