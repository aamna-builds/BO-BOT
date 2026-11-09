"""Draw the block diagram of the Simulink model bobot_balance.slx (model-diagram.png).

A picture of what build_bobot_model.m builds, for the README. Feedback signals are drawn as tags (pink). Run: python draw_model_diagram.py (needs matplotlib).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(figsize=(17, 8.2), dpi=130)
ax.set_xlim(0, 170); ax.set_ylim(10, 80); ax.axis("off")

W, H = 15.0, 8.4
kinds = {"src": "#eef3fb", "gain": "#f4f6f8", "lim": "#fff4e5", "plant": "#f3eefb", "fb": "#fdeaf1", "ff": "#eef8ee", "scope": "#e8f6ee", "del": "#fdeeee"}


def block(x, y, text, kind="gain", w=W, h=H, lw=1.4):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.1,rounding_size=0.8", fc=kinds[kind], ec="#445566", lw=lw, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.3, zorder=4, linespacing=1.15)
    return x, y


def total(x, y, signs):
    ax.add_patch(Circle((x, y), 2.6, fc="white", ec="#445566", lw=1.4, zorder=3))
    ax.text(x, y, signs, ha="center", va="center", fontsize=8, zorder=4, linespacing=0.95)
    return x, y


def arrow(pts, color="#222", label=None, lpos=None, lw=1.4):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1], ys[:-1], color=color, lw=lw, zorder=2, solid_capstyle="butt")
    ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0), zorder=2)
    if label:
        ax.text(lpos[0], lpos[1], label, fontsize=7.8, color=color, ha="center", va="bottom", zorder=4)


R1, R2, FB = 62, 28, 46          # main row, return row, feedback band
hw = W / 2

# ---- row 1: command, speed loop, angle loop
block(9, R1, "Step\n0 to 0.2 m/s\nat 0.5 s", "src")
block(28, R1, "Rate limiter\n0.6 m/s per s", "src")
total(46, R1, "+\n-")
block(65, R1, "Speed PI\nkp_v = 20\nki_v = 0.9 (with 1/s)", "gain", w=17.5)
block(86, R1, "Lean limit\n+/-10 deg", "lim")
total(103, R1, "+\n-")
block(122, R1, "Angle PD\nkp = 55, kd = 0.35", "gain", w=18)
total(142, R1, "+\n+")
arrow([(9 + hw, R1), (28 - hw, R1)]); arrow([(28 + hw, R1), (46 - 2.6, R1)], label="vcmd", lpos=(37, R1 + 1.4))
arrow([(46 + 2.6, R1), (65 - 8.75, R1)], label="speed error", lpos=(55.5, R1 + 1.4))
arrow([(65 + 8.75, R1), (86 - hw, R1)]); arrow([(86 + hw, R1), (103 - 2.6, R1)], label="lean target", lpos=(95, R1 + 1.4))
arrow([(103 + 2.6, R1), (122 - 9, R1)], label="angle error", lpos=(112.5, R1 + 1.4)); arrow([(122 + 9, R1), (142 - 2.6, R1)])

# ---- feedback band (From blocks)
block(46, FB, "From v:\nspeed estimate\n1/(0.0217 s + 1)", "fb", w=17, h=9.4)
block(103, FB, "From phi:\nx 57.3 (deg)", "fb")
block(122, FB + 0.0, "From phid:\nx 57.3 (deg/s)", "fb", w=16.5)
block(142, FB, "Feed-forward\nkff*emf/Vb*255\n(from vcmd)", "ff", w=17, h=9.4)
arrow([(46, FB + 4.7), (46, R1 - 2.6)], color="#b0305a")
arrow([(103, FB + 4.2), (103, R1 - 2.6)], color="#b0305a")
arrow([(122, FB + 4.2), (122, R1 - 4.2)], color="#b0305a", label="", lpos=(0, 0))
arrow([(142, FB + 4.7), (142, R1 - 2.6)], color="#2f7d4f")

# ---- row 2: output chain, flowing right to left
block(152, R2, "PWM limit\n+/-204", "lim")
block(133, R2, "x 1/255\n(PWM to duty)", "gain")
block(114, R2, "Transport delay\n3.5 ms", "del")
block(93, R2, "Plant (State-Space)\nx = [v, phi, phid]\nA, B from the equations", "plant", w=21, h=10.4, lw=2.2)
block(70, R2, "Demux", "plant", w=10)
block(46, R2 + 6, "Scope: speed", "scope", w=15)
block(46, R2 - 6, "Scope: pitch", "scope", w=15)
arrow([(142 + 2.6, R1), (152, R1), (152, R2 + H / 2)], label="PWM request", lpos=(158.5, R1 - 5.5))
arrow([(152 - hw, R2), (133 + hw, R2)]); arrow([(133 - hw, R2), (114 + hw, R2)], label="duty u", lpos=(123.5, R2 + 0.6))
arrow([(114 - hw, R2), (93 + 10.5, R2)]); arrow([(93 - 10.5, R2), (70 + 5, R2)])
arrow([(70 - 5, R2), (62, R2), (62, R2 + 6), (46 + 7.5, R2 + 6)]); arrow([(62, R2), (62, R2 - 6), (46 + 7.5, R2 - 6)])
ax.text(66.5, R2 + 9.5, "v, phi, phid", fontsize=8, color="#555", ha="center")

# ---- notes
ax.text(100, 16, "Pink blocks: v, phi and phid are returned from the Demux to the loop.\nHere they are drawn as tags; in the generated model they are plain feedback wires.", fontsize=8, color="#b0305a", ha="left", va="top")
ax.text(5, 78, "bobot_balance.slx: linear plant with the firmware control law", fontsize=14, weight="bold", ha="left", va="top")
ax.text(5, 74.2, "Gains and limits are the firmware values. Speed estimate lag and control delay are included because the loop is unstable without them.",
        fontsize=9, color="#555", ha="left", va="top")
fig.savefig(os.path.join(HERE, "model-diagram.png"), bbox_inches="tight", facecolor="white")
print("wrote model-diagram.png")
