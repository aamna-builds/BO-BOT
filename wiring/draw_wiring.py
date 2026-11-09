"""Draw the BO-BOT wiring diagram (wiring-diagram.png) from the pin map in wiring/README.md.

Run:  python draw_wiring.py     (needs matplotlib)
If you change a pin, change it here, in config.h and in wiring/README.md.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiring-diagram.png")
COL = {"pwr": "#d9442f", "gnd": "#333333", "3v3": "#e8893c", "sda": "#2b8fd6", "scl": "#2f9e6a",
       "mot": "#7a5bc0", "enc": "#8a8f98", "bat": "#b0305a"}

fig, ax = plt.subplots(figsize=(15, 10), dpi=130)
ax.set_xlim(0, 150); ax.set_ylim(0, 108); ax.axis("off")
fig.patch.set_facecolor("white")


def box(x0, y0, x1, y1, title, fc="#f4f6f8", ec="#445", sub=None, ty=2.2):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.2,rounding_size=1.2", fc=fc, ec=ec, lw=1.6))
    ax.text((x0 + x1) / 2, y1 - ty, title, ha="center", va="top", fontsize=11, weight="bold", color="#111")
    if sub:
        ax.text((x0 + x1) / 2, y1 - ty - 2.8, sub, ha="center", va="top", fontsize=8, color="#555")


def pin(x, y, label, side, color="#111"):
    ax.plot([x], [y], "s", ms=4, color="#222")
    dx = 1.6 if side == "R" else -1.6
    ax.text(x + dx, y, label, ha="left" if side == "R" else "right", va="center", fontsize=8.5, color=color)


def wire(pts, key, lw=2.0, label=None, lx=None, ly=None):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, "-", color=COL[key], lw=lw, solid_capstyle="round", solid_joinstyle="round", zorder=1)
    if label:
        ax.text(lx, ly, label, fontsize=8, color=COL[key], ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=0.6), zorder=3)


# ---------------------------------------------------------------- boxes
box(52, 30, 92, 74, "ESP32 DevKit", "#eef3fb", sub="controller", ty=14)
box(36, 84, 62, 98, "MPU-6050", "#eaf2ff", sub="IMU (I2C 0x68)")
box(82, 84, 112, 98, "OLED 1.3\" SH1106", "#eaf2ff", sub="face (I2C)")
box(116, 40, 146, 74, "DRV8833", "#fdeeee", sub="motor driver")
box(3, 56, 32, 78, "Left motor", "#f3eefb", sub="GA12-N20 + encoder")
box(3, 28, 32, 50, "Right motor", "#f3eefb", sub="GA12-N20 + encoder")
box(116, 4, 146, 24, "2S LiPo 7.4 V", "#fdeaf1", sub="XT30 + switch")
box(62, 4, 96, 20, "Buck converter", "#eef8ee", sub="7.4 V in, 5.0 V out")

# ---------------------------------------------------------------- I2C (top)
sda_x, scl_x = 66, 76
for xx, lab in [(sda_x, "GPIO 21\nSDA"), (scl_x, "GPIO 22\nSCL")]:
    ax.plot([xx], [74], "s", ms=4, color="#222"); ax.text(xx, 72.6, lab, ha="center", va="top", fontsize=8.5)
wire([(sda_x, 74), (sda_x, 80), (47, 80), (47, 84)], "sda"); wire([(sda_x, 80), (92, 80), (92, 84)], "sda")
wire([(scl_x, 74), (scl_x, 78), (55, 78), (55, 84)], "scl"); wire([(scl_x, 78), (102, 78), (102, 84)], "scl")
ax.text(70, 81.2, "SDA", color=COL["sda"], fontsize=8, ha="center", weight="bold")
ax.text(70, 76.6, "SCL", color=COL["scl"], fontsize=8, ha="center", weight="bold")
ax.text(118, 92, "MPU-6050 and OLED share the two I2C wires\nBoth powered from 3V3, common GND", fontsize=8, color="#555", ha="left")

# ---------------------------------------------------------------- encoders (left of ESP32)
left = [(68, "GPIO 32  ENC L-A", 66), (64, "GPIO 33  ENC L-B", 62), (46, "GPIO 34  ENC R-A", 44), (42, "GPIO 35  ENC R-B", 40)]
for y, lab, ym in left:
    ax.plot([52], [y], "s", ms=4, color="#222")
    ax.text(50.4, y + 1.4, lab, ha="right", va="center", fontsize=8.5)
wire([(52, 68), (32, 68)], "enc"); wire([(52, 64), (32, 64)], "enc")
wire([(52, 46), (32, 46)], "enc"); wire([(52, 42), (32, 42)], "enc")
ax.text(5, 54.5, "encoder supply: 3V3 (not 5 V!)", fontsize=8, color=COL["3v3"], weight="bold")
ax.text(5, 26.5, "encoder supply: 3V3 (not 5 V!)", fontsize=8, color=COL["3v3"], weight="bold")

# ---------------------------------------------------------------- motor driver signals (right of ESP32)
right = [(68, "GPIO 25  L IN1 > AIN1"), (64, "GPIO 26  L IN2 > AIN2"), (60, "GPIO 27  R IN1 > BIN1"), (56, "GPIO  4  R IN2 > BIN2")]
for i, (y, lab) in enumerate(right):
    ax.plot([92], [y], "s", ms=4, color="#222")
    ax.text(93.6, y + 1.4, lab, ha="left", va="center", fontsize=8.5)
    wire([(92, y), (116, y)], "mot")
ax.text(105, 71, "PWM 20 kHz", fontsize=8, color=COL["mot"], ha="center")

# DRV outputs to motors: run along the bottom-left
wire([(131, 40), (131, 33), (36, 33), (36, 72), (32, 72)], "mot", label="AOUT1 / AOUT2 to left motor", lx=112, ly=33)
wire([(137, 40), (137, 28), (34, 28), (34, 36), (32, 36)], "mot", label="BOUT1 / BOUT2 to right motor", lx=112, ly=28)

# ---------------------------------------------------------------- battery sense
ax.plot([52], [36], "s", ms=4, color="#222"); ax.text(50.4, 37.4, "GPIO 36  VBAT", ha="right", fontsize=8.5)
wire([(52, 36), (48, 36), (48, 24), (124, 24)], "bat",
     label="10 k / 4.7 k divider to battery +", lx=100, ly=25.8)

# ---------------------------------------------------------------- power
wire([(131, 24), (131, 40)], "pwr", lw=2.4)                 # battery + to DRV8833 VM
ax.text(133, 31, "VM", fontsize=8, color=COL["pwr"], weight="bold")
wire([(116, 17), (96, 17)], "pwr", lw=2.4, label="7.4 V", lx=106, ly=19)    # battery + to buck in
wire([(79, 20), (79, 30)], "pwr", lw=2.4)                   # buck 5 V to ESP32 VIN
ax.plot([79], [30], "s", ms=4, color="#222"); ax.text(80.6, 22, "5 V to VIN", fontsize=8.5, color=COL["pwr"], weight="bold")
# 3V3 and GND notes
ax.text(72, 50, "3V3  >  MPU-6050, OLED, both encoders", fontsize=9, color=COL["3v3"], ha="center", weight="bold")
ax.text(72, 46.5, "GND  >  one common ground for everything", fontsize=9, color=COL["gnd"], ha="center", weight="bold")
ax.text(72, 42.5, "DRV8833 SLP pin to 3V3", fontsize=8.5, color="#555", ha="center")

# ---------------------------------------------------------------- legend and notes
x = 3
for k, lab in [("pwr", "battery power"), ("3v3", "3V3"), ("sda", "I2C SDA"), ("scl", "I2C SCL"), ("mot", "motor"), ("enc", "encoder"), ("bat", "battery sense")]:
    ax.plot([x, x + 4], [103, 103], "-", color=COL[k], lw=3); ax.text(x + 5, 103, lab, fontsize=8.5, va="center"); x += 7 + len(lab) * 1.15
ax.text(3, 2, "Check XT30 polarity before connecting. Do not power from the battery and USB at the same time.",
        fontsize=8.5, color="#a00")
ax.text(75, 105.5, "BO-BOT wiring", fontsize=15, weight="bold", ha="center", va="bottom")
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print("wrote", OUT)
