"""Combine the four most useful graphs into results/00_overview.png (run bobot_linear_model.py first)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
panels = [("01_poles.png", "Poles: one open-loop pole is unstable"), ("03_speed_step.png", "Speed command response"),
          ("04_angle_loop_bode.png", "Angle loop margins"), ("05_gain_sweeps.png", "Stable gain ranges")]
fig, axs = plt.subplots(2, 2, figsize=(16, 11.5), dpi=120)
for a, (f, t) in zip(axs.flat, panels):
    a.imshow(mpimg.imread(os.path.join(R, f))); a.set_title(t, fontsize=13, weight="bold", pad=8); a.axis("off")
fig.suptitle("BO-BOT balance control: key results", fontsize=18, weight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(R, "00_overview.png"), facecolor="white")
print("wrote 00_overview.png")
