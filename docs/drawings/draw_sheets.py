"""Engineering drawing sheets for BO-BOT (A3, third angle projection).

All geometry comes from cad/fusion360/python/CatRobot.py (units mm, robot axes:
x width, y up from the ground, z towards the face). Run:  python3 draw_sheets.py
Writes sheet1-general-arrangement.png and sheet2-electronics.png next to this file.
"""
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyBboxPatch

OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]
plt.rcParams["hatch.linewidth"] = 0.6
INK = "#111111"; THIN = 0.45; MED = 0.9; THICK = 1.6
A3W, A3H = 420, 297

# ---------------------------------------------------------------- CAD numbers
WHEEL_D, WHEEL_W, TRACK = 34, 6.5, 70
AX = WHEEL_D / 2                      # axle height
P1Y, P2Y, P3Y = 22.0, 41.6, 63.2      # platform bottom faces
PT = 1.6                              # platform thickness
P1 = (70, 48); P2 = (70, 46); P3 = (56, 27)   # width x depth
S1 = [(25.5, 21), (-25.5, 21), (25.5, -21), (-25.5, -21)]
S2 = [(25.5, 0), (-25.5, 0)]
WALL = 2.5


def egg_s(t):
    if t <= 0.32:
        s = 0.82 + 0.18 * math.sin(math.pi / 2 * t / 0.32)
    else:
        u = (t - 0.32) / 0.68
        s = math.sqrt(max(1 - u ** 2.2, 0.0))
    return max(s, 0.14)


def egg(half, inset=0.0, n=120):
    """outline of the shell: list of (offset, y) for the right half; half = 40 (width) or 27.5 (depth)"""
    pts = []
    for i in range(n + 1):
        t = i / n
        y = 2 + 98 * t
        pts.append((max(half * egg_s(t) - inset, 0.0), y))
    return pts


# ---------------------------------------------------------------- drawing helpers
def new_sheet():
    fig = plt.figure(figsize=(A3W / 25.4, A3H / 25.4), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, A3W); ax.set_ylim(0, A3H); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), A3W, A3H, fc="white", ec="none"))
    ax.add_patch(Rectangle((20, 10), A3W - 30, A3H - 20, fc="none", ec=INK, lw=1.6))   # border (binding margin left)
    ax.add_patch(Rectangle((15, 5), A3W - 20, A3H - 10, fc="none", ec=INK, lw=0.5))
    # zone marks
    for i in range(1, 8):
        x = 20 + i * (A3W - 30) / 8
        ax.plot([x, x], [10, 14], color=INK, lw=0.5); ax.plot([x, x], [A3H - 10, A3H - 14], color=INK, lw=0.5)
    for i in range(8):
        x = 20 + (i + .5) * (A3W - 30) / 8
        ax.text(x, 6.7, str(i + 1), ha="center", va="center", fontsize=6)
        ax.text(x, A3H - 7.3, str(i + 1), ha="center", va="center", fontsize=6)
    for i, c in enumerate("FEDCBA"):
        y = 10 + (i + .5) * (A3H - 20) / 6
        ax.text(17.4, y, c, ha="center", va="center", fontsize=6)
    return fig, ax


def line(ax, pts, lw=MED, ls="-", c=INK, z=3):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=c, lw=lw, ls=ls, solid_capstyle="round", zorder=z)


def rect(ax, x0, y0, x1, y1, lw=MED, ls="-", fc="none", hatch=None, z=3, ec=INK):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, ls=ls, hatch=hatch, zorder=z))


def centre(ax, x0, y0, x1, y1):
    ax.plot([x0, x1], [y0, y1], color=INK, lw=THIN, ls=(0, (8, 2, 1.5, 2)), zorder=2)


def txt(ax, x, y, s, size=7, ha="left", va="center", weight="normal", rot=0, style="normal", color=INK):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, fontweight=weight, rotation=rot, fontstyle=style, color=color, zorder=6)


def arrow(ax, p, q):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="-|>,head_length=0.35,head_width=0.12",
                                                   color=INK, lw=0.5, shrinkA=0, shrinkB=0), zorder=5)


def dim_h(ax, x1, x2, y, label, off=-9, ext_from=None, size=7, label_dx=0):
    """horizontal dimension between x1 and x2 at feature height y; dimension line placed at y+off"""
    yd = y + off
    s = 1 if off > 0 else -1
    for x in (x1, x2):
        ax.plot([x, x], [y + s * 1.2, yd + s * 1.5], color=INK, lw=THIN, zorder=2)
    arrow(ax, ((x1 + x2) / 2, yd), (x1, yd)); arrow(ax, ((x1 + x2) / 2, yd), (x2, yd))
    ax.plot([x1, x2], [yd, yd], color=INK, lw=THIN, zorder=2)
    txt(ax, (x1 + x2) / 2 + label_dx, yd + s * 2.2, label, size, ha="center")


def dim_v(ax, y1, y2, x, label, off=-9, size=7, label_dy=0):
    xd = x + off
    s = 1 if off > 0 else -1
    for y in (y1, y2):
        ax.plot([x + s * 1.2, xd + s * 1.5], [y, y], color=INK, lw=THIN, zorder=2)
    arrow(ax, (xd, (y1 + y2) / 2), (xd, y1)); arrow(ax, (xd, (y1 + y2) / 2), (xd, y2))
    ax.plot([xd, xd], [y1, y2], color=INK, lw=THIN, zorder=2)
    txt(ax, xd - s * 2.4, (y1 + y2) / 2 + label_dy, label, size, ha="center", rot=90)


def leader(ax, tip, text_xy, label, size=6.5, ha="left"):
    arrow(ax, text_xy, tip)
    txt(ax, text_xy[0] + (1.2 if ha == "left" else -1.2), text_xy[1], label, size, ha=ha)


def view_title(ax, x, y, name, scale="SCALE 1 : 1"):
    txt(ax, x, y, name, 9, ha="center", weight="bold")
    txt(ax, x, y - 4.6, scale, 6.5, ha="center")
    ax.plot([x - 22, x + 22], [y - 2.3, y - 2.3], color=INK, lw=0.7)


def balloon(ax, x, y, n, tip):
    ax.add_patch(Circle((x, y), 3.1, fc="white", ec=INK, lw=0.7, zorder=6))
    txt(ax, x, y, str(n), 6.5, ha="center", weight="bold")
    d = math.hypot(tip[0] - x, tip[1] - y)
    p = (x + (tip[0] - x) * 3.1 / d, y + (tip[1] - y) * 3.1 / d)
    arrow(ax, p, tip)


def table(ax, x0, y_top, colw, rows, rowh=6.4, header=True, size=6.3, bold_first_row=True, aligns=None):
    n = len(rows)
    W = sum(colw)
    ax.add_patch(Rectangle((x0, y_top - n * rowh), W, n * rowh, fc="white", ec=INK, lw=1.0, zorder=2))
    for i, r in enumerate(rows):
        y = y_top - (i + .5) * rowh
        if i > 0:
            ax.plot([x0, x0 + W], [y_top - i * rowh] * 2, color=INK, lw=0.5 if i > 1 or not header else 1.0, zorder=3)
        cx = x0
        for j, c in enumerate(r):
            al = (aligns[j] if aligns else "left")
            tx = cx + 1.6 if al == "left" else cx + colw[j] / 2
            txt(ax, tx, y, str(c), size, ha=al, weight="bold" if (i == 0 and header and bold_first_row) else "normal")
            cx += colw[j]
    cx = x0
    for w in colw[:-1]:
        cx += w
        ax.plot([cx, cx], [y_top, y_top - n * rowh], color=INK, lw=0.5, zorder=3)


def title_block(ax, title, sub, sheet, dwg):
    x0, y0, w, h = 230, 10, 180, 46
    ax.add_patch(Rectangle((x0, y0), w, h, fc="white", ec=INK, lw=1.6, zorder=2))
    ax.plot([x0, x0 + w], [y0 + 26, y0 + 26], color=INK, lw=0.8)
    ax.plot([x0, x0 + w], [y0 + 13, y0 + 13], color=INK, lw=0.5)
    for xv in (x0 + 60, x0 + 120): ax.plot([xv, xv], [y0, y0 + 26], color=INK, lw=0.5)
    ax.plot([x0 + 120, x0 + 120], [y0 + 26, y0 + h], color=INK, lw=0.5)
    txt(ax, x0 + 3, y0 + h - 4, "TITLE", 5, color="#444"); txt(ax, x0 + 3, y0 + h - 12, title, 11, weight="bold")
    txt(ax, x0 + 3, y0 + 30.5, sub, 7)
    txt(ax, x0 + 123, y0 + h - 4, "DRAWING NO.", 5, color="#444"); txt(ax, x0 + 123, y0 + h - 12, dwg, 10, weight="bold")
    txt(ax, x0 + 123, y0 + 30.5, "REV  A", 7)
    cells = [("DRAWN BY", "Aamna Khan", 0, 13), ("DATE", "11-11-2026", 60, 13), ("SCALE", "as noted", 120, 13),
             ("CHECKED", "", 0, 0), ("UNITS", "mm", 60, 0), ("SHEET", sheet, 120, 0)]
    for lab, val, dx, dy in cells:
        txt(ax, x0 + dx + 3, y0 + dy + 10.5, lab, 4.8, color="#444"); txt(ax, x0 + dx + 3, y0 + dy + 4.6, val, 7.5)
    # projection symbol (third angle)
    px, py = x0 + 150, y0 + 6.5
    ax.add_patch(Polygon([[px - 7, py - 4.2], [px - 7, py + 4.2], [px + 2, py + 2.4], [px + 2, py - 2.4]], fc="none", ec=INK, lw=0.7, zorder=6))
    ax.add_patch(Circle((px + 13, py), 4.2, fc="none", ec=INK, lw=0.7, zorder=6)); ax.add_patch(Circle((px + 13, py), 2.0, fc="none", ec=INK, lw=0.7, zorder=6))
    ax.plot([px - 9, px + 19], [py, py], color=INK, lw=0.4, ls=(0, (8, 2, 1.5, 2)), zorder=6)
    txt(ax, px + 3, py + 8.4, "THIRD ANGLE", 4.6, ha="center", color="#444")


# ================================================================== SHEET 1
def sheet1():
    fig, ax = new_sheet()
    GX, GY = 100, 62          # ground, centre line of the front view
    # -------- FRONT VIEW (section A-A through the centre plane) -------
    outer = egg(40); inner = egg(40, WALL)
    # shell walls hatched, with the inner profile starting at y=2 (open bottom) and closed top shell above y=100
    def mirror(pts, sx): return [(GX + sx * x, GY + y) for x, y in pts]
    for sx in (1, -1):
        wall = mirror(outer, sx) + list(reversed(mirror(inner[:-1] if False else inner, sx)))
        ax.add_patch(Polygon(wall, fc="none", ec="none", hatch="//////", zorder=2))
        line(ax, mirror(outer, sx), THICK); line(ax, mirror(inner, sx), MED)
        line(ax, [mirror(outer, sx)[0], mirror(inner, sx)[0]], MED)
    line(ax, [(GX - outer[-1][0], GY + 102), (GX + outer[-1][0], GY + 102)], THICK)          # top of the egg
    # ears (outside the section plane, shown as outline)
    for sx in (1, -1):
        e = [(GX + sx * 6, GY + 99), (GX + sx * 24, GY + 87), (GX + sx * 22, GY + 110), (GX + sx * 15, GY + 104)]
        line(ax, [(GX + sx * 24, GY + 85.5), (GX + sx * 22, GY + 110.3), (GX + sx * 10, GY + 98.5)], MED)
        line(ax, [(GX + sx * 21.2, GY + 106), (GX + sx * 15.5, GY + 88)], THIN, ls=(0, (4, 2)))
    # wheel arches in the lower shell are cut for the wheels: show wheels
    for sx in (1, -1):
        xc = GX + sx * 35
        rect(ax, xc - WHEEL_W / 2, GY, xc + WHEEL_W / 2, GY + WHEEL_D, MED, fc="white", z=4)
        rect(ax, xc - WHEEL_W / 2 + 0.75, GY + 4, xc + WHEEL_W / 2 - 0.75, GY + WHEEL_D - 4, THIN, z=5)
        line(ax, [(xc - 0.8 * sx, GY + AX - 1.5), (xc - 0.8 * sx, GY + AX + 1.5)], THIN, z=5)
        # motor: gearbox + motor + encoder (cut plane, hatched thin)
        gx0, gx1 = sorted((GX + sx * 16, GX + sx * 26)); rect(ax, gx0, GY + AX - 5, gx1, GY + AX + 5, MED, hatch="||||", z=3, fc="white")
        mx0, mx1 = sorted((GX + sx * 3, GX + sx * 16)); rect(ax, mx0, GY + AX - 5, mx1, GY + AX + 5, MED, fc="white", z=3)
        line(ax, [(GX + sx * 26, GY + AX), (GX + sx * 35.5, GY + AX)], MED)
    # platforms (cut) and standoffs
    def plat(y0, W):
        rect(ax, GX - W / 2, GY + y0, GX + W / 2, GY + y0 + PT, MED, fc="black", z=4)
    plat(P1Y, P1[0]); plat(P2Y, P2[0]); plat(P3Y, P3[0])
    for x in (25.5, -25.5):   # standoffs L1 (behind plane, hidden-ish) and L2 (cut)
        rect(ax, GX + x - 2.75, GY + P1Y + PT, GX + x + 2.75, GY + P2Y, THIN, fc="white", z=3)
        rect(ax, GX + x - 2.75, GY + P2Y + PT, GX + x + 2.75, GY + P3Y, MED, fc="white", hatch="////", z=3)
    # battery (cut) with strap
    rect(ax, GX - 34, GY + 23.6, GX + 34, GY + 35.6, MED, fc="white", hatch="....", z=3)
    rect(ax, GX - 4, GY + 23.6, GX + 4, GY + 35.6, MED, fc="white", z=3)
    # ESP32 on platform 3, OLED + bezel at the front (z+), seen from the side edge in the plane
    rect(ax, GX - 25.5, GY + P3Y + PT, GX + 25.5, GY + P3Y + PT + 1.6, MED, fc="black", z=4)
    rect(ax, GX - 17.7, GY + 47.75, GX + 17.7, GY + 81.25, MED, ls=(0, (5, 2)), z=3)        # OLED board (behind, z=15.8)
    rect(ax, GX - 15.2, GY + 59.6, GX + 15.2, GY + 74.4, MED, z=3)                               # window in the shell, 30.4 x 15.2 at y=67
    # centre lines
    centre(ax, GX, GY - 8, GX, GY + 116); centre(ax, GX - 52, GY + AX, GX + 52, GY + AX)
    line(ax, [(GX - 58, GY), (GX + 58, GY)], THICK)                                          # ground
    for i in range(-11, 12): ax.plot([GX + i * 5, GX + i * 5 - 2.4], [GY, GY - 2.4], color=INK, lw=0.4, zorder=2)
    # dimensions
    dim_v(ax, GY, GY + 110, GX - 58, "110", off=-12)
    dim_v(ax, GY, GY + AX, GX + 58, "17", off=10)
    dim_h(ax, GX - 40, GX + 40, GY + 33, "80", off=85)            # overall width at the widest section
    dim_h(ax, GX - 35, GX + 35, GY, f"{TRACK}  (track, centre to centre)", off=-17, label_dx=0)
    dim_h(ax, GX + 35 - WHEEL_W / 2, GX + 35 + WHEEL_W / 2, GY, "6.5", off=-7, size=6.2)
    dim_v(ax, GY + P1Y, GY + P2Y, GX + 38, "18", off=13, label_dy=0)
    dim_v(ax, GY + P2Y + PT, GY + P3Y, GX + 38, "20", off=13, label_dy=0)
    view_title(ax, GX, 31 + 0, "SECTION A-A  (FRONT)", "SCALE 1 : 1")
    # balloons
    balloon(ax, GX - 55, GY + 98, 1, (GX - 14, GY + 94)); balloon(ax, GX - 59, GY + 52, 2, (GX - 31.5, GY + 50))
    balloon(ax, GX + 70, GY + 80, 5, (GX + 25, GY + P3Y + 0.8)); balloon(ax, GX + 70, GY + 56, 4, (GX + 34.5, GY + 42.4))
    balloon(ax, GX + 70, GY + 30, 3, (GX + 33, GY + 22.8)); balloon(ax, GX - 55, GY + 29, 10, (GX - 32, GY + 29))
    balloon(ax, GX - 55, GY + 12, 8, (GX - 22, GY + 15)); balloon(ax, GX + 62, GY + 8, 9, (GX + 37, GY + 9))
    balloon(ax, GX - 62, GY + 70, 11, (GX - 24, GY + 66))

    # -------- SIDE VIEW (from the right: face is on the right) -------
    SX = 205
    so = egg(27.5); si = egg(27.5, WALL)
    # outer silhouette (external view): full outline
    full = [(SX - x, GY + y) for x, y in so] + [(SX + x, GY + y) for x, y in reversed(so)]
    line(ax, full + [full[0]], THICK)
    line(ax, [(SX - so[0][0], GY + 2), (SX + so[0][0], GY + 2)], THICK)
    line(ax, [(SX - so[-1][0], GY + 100), (SX + so[-1][0], GY + 100)], MED)
    # ears: seen edge-on (thin, 4.5 thick)
    line(ax, [(SX - 2.25, GY + 96), (SX - 2.25, GY + 109), (SX + 2.25, GY + 109), (SX + 2.25, GY + 96)], MED)
    # wheel (right side wheel, in front of the shell)
    ax.add_patch(Circle((SX, GY + AX), 17, fc="white", ec=INK, lw=MED, zorder=5))
    ax.add_patch(Circle((SX, GY + AX), 13, fc="none", ec=INK, lw=THIN, zorder=5))
    ax.add_patch(Circle((SX, GY + AX), 1.5, fc="none", ec=INK, lw=MED, zorder=5))
    for k in range(5):
        th = 2 * math.pi * k / 5 + math.pi / 2
        ax.add_patch(Circle((SX + 8.2 * math.cos(th), GY + AX + 8.2 * math.sin(th)), 2.6, fc="none", ec=INK, lw=THIN, zorder=5))
    # OLED window + bezel on the face (right side), bezel 5.3 thick, window 30.4 x 15.2 wide
    rect(ax, SX + 22.1, GY + 55.5, SX + 27.4, GY + 78.5, MED, z=4)
    # hidden: platforms and battery (dashed)
    for y0, d in ((P1Y, P1[1]), (P2Y, P2[1]), (P3Y, P3[1])):
        rect(ax, SX - d / 2, GY + y0, SX + d / 2, GY + y0 + PT, THIN, ls=(0, (4, 2)), z=1)
    rect(ax, SX - 18.5, GY + 23.6, SX + 18.5, GY + 35.6, THIN, ls=(0, (4, 2)), z=1)
    # bow tie
    rect(ax, SX + 25, GY + 43, SX + 31.5, GY + 49, THIN, z=4)
    centre(ax, SX, GY - 8, SX, GY + 116); centre(ax, SX - 42, GY + AX, SX + 42, GY + AX)
    line(ax, [(SX - 48, GY), (SX + 48, GY)], THICK)
    for i in range(-9, 10): ax.plot([SX + i * 5, SX + i * 5 - 2.4], [GY, GY - 2.4], color=INK, lw=0.4, zorder=2)
    dim_h(ax, SX - 27.5, SX + 27.5, GY + 33, "55", off=85)
    dim_h(ax, SX - 17, SX + 17, GY, f"Ø{WHEEL_D}", off=-11)
    dim_v(ax, GY, GY + 110, SX + 40, "110", off=16)
    dim_v(ax, GY + 59.6, GY + 74.4, SX + 27.4, "15.2", off=7, size=6.2)
    leader(ax, (SX + 24.7, GY + 72), (SX + 33, GY + 96), "OLED window", 6.2)
    txt(ax, SX + 34.2, GY + 92, "30.4 x 15.2", 6.2)
    leader(ax, (SX + 31.5, GY + 46), (SX + 36, GY + 38), "bow tie", 6.2)
    view_title(ax, SX, 31, "SIDE VIEW  (FROM RIGHT)", "SCALE 1 : 1")

    # -------- TOP VIEW -------
    TX, TY = 100, 241
    # shell max section 80 x 55 (the widest layer, y = 33) drawn as rounded rectangle
    ax.add_patch(FancyBboxPatch((TX - 40 + 12, TY - 27.5 + 12), 80 - 24, 55 - 24, boxstyle="round,pad=12,rounding_size=12", fc="none", ec=INK, lw=THICK, zorder=3))
    # inside the top at y=100 the egg is small: show its outline
    ax.add_patch(FancyBboxPatch((TX - 5.6 + 1.5, TY - 3.85 + 1.5), 11.2 - 3, 7.7 - 3, boxstyle="round,pad=1.5,rounding_size=1.5", fc="none", ec=INK, lw=MED, zorder=3))
    for sx in (1, -1):
        rect(ax, TX + sx * 35 - WHEEL_W / 2, TY - 17, TX + sx * 35 + WHEEL_W / 2, TY + 17, MED, ls=(0, (4, 2)), z=2)
        rect(ax, TX + sx * 35 - WHEEL_W / 2, TY - 17, TX + sx * 35 + WHEEL_W / 2, TY + 17, MED, ls="none", z=1)
    # ears
    for sx in (1, -1): rect(ax, TX + sx * 18 - 7, TY - 2.25, TX + sx * 18 + 7, TY + 2.25, MED, z=4, fc="white")
    # OLED window (front = up)
    rect(ax, TX - 19, TY + 21, TX + 19, TY + 26.4, MED, z=4)
    centre(ax, TX, TY - 36, TX, TY + 36); centre(ax, TX - 50, TY, TX + 50, TY)
    dim_h(ax, TX - 40, TX + 40, TY + 27.5, "80", off=10)
    dim_v(ax, TY - 27.5, TY + 27.5, TX + 40, "55", off=19)
    dim_h(ax, TX - 35, TX + 35, TY - 27.5, "70", off=-10)
    txt(ax, TX - 44, TY + 29, "FRONT", 6.5, ha="right", weight="bold"); arrow(ax, (TX - 52, TY + 22), (TX - 52, TY + 34))
    view_title(ax, TX, TY - 47, "TOP VIEW", "SCALE 1 : 1")
    line(ax, [(TX - 52, TY), (TX - 47, TY)], 1.4); line(ax, [(TX + 47, TY), (TX + 52, TY)], 1.4)
    txt(ax, TX - 55, TY + 4, "A", 8, weight="bold"); txt(ax, TX + 56, TY + 4, "A", 8, weight="bold")

    # -------- DETAIL B: OLED window at 2:1 -------
    DX, DY, k = 345, 232, 2.0
    def R(cx, cy, w, h, **kw): rect(ax, DX + (cx - w / 2) * k, DY + (cy - h / 2) * k, DX + (cx + w / 2) * k, DY + (cy + h / 2) * k, **kw)
    R(0, 0, 38, 23, lw=THICK)                       # bezel
    R(0, 0, 30.4, 15.2, lw=MED)                     # window
    R(0, 0, 29.42, 14.7, lw=THIN, ls=(0, (3, 2)))   # active area
    R(0, -1.0, 35.4, 33.5, lw=THIN, ls=(0, (6, 2, 1, 2)))   # board behind (centre 2.5 below the glass centre)
    centre(ax, DX - 42, DY, DX + 42, DY); centre(ax, DX, DY - 36, DX, DY + 40)
    dim_h(ax, DX - 38, DX + 38, DY + 11.5 * k, "38", off=17, size=6.5)
    dim_h(ax, DX - 30.4, DX + 30.4, DY - 7.6 * k, "30.4", off=-(3.9 * k + 9), size=6.5)
    dim_v(ax, DY - 11.5 * k, DY + 11.5 * k, DX + 38, "23", off=14, size=6.5)
    dim_v(ax, DY - 7.6 * k, DY + 7.6 * k, DX - 30.4, "15.2", off=-14, size=6.5)
    txt(ax, DX, DY - 18.6 * k - 2.6, "chain line: display board 35.4 x 33.5 (behind the bezel)", 5.8, ha="center")
    view_title(ax, DX, DY - 55, "DETAIL B  (OLED WINDOW)", "SCALE 2 : 1")

    # -------- notes -------
    nx, ny = 175, 270
    txt(ax, nx, ny, "NOTES", 8, weight="bold")
    notes = ["1.  All dimensions in millimetres. General tolerance +/- 0.5 (3D printed parts).",
             "2.  Dimensions taken from the Fusion 360 script  cad/fusion360/python/CatRobot.py.",
             "3.  Shell: 2.5 wall, printed in two parts, split at 40 above the ground.",
             "4.  Section A-A is cut through the centre plane; the standoffs at the corners",
             "     (4 off, 18 long) lie behind the plane and are shown plain.",
             "5.  Display: 1.3\" SH1106 OLED, board 35.4 x 33.5, active area 29.42 x 14.7",
             "     (seller figures; measure the real board before printing the bezel).",
             "6.  Whiskers, LED rings and bow tie are decoration and are not dimensioned.",
             "7.  Part numbers refer to the parts list."]
    for i, n in enumerate(notes): txt(ax, nx, ny - 7 - i * 5.0, n, 6.2)

    # -------- parts list -------
    rows = [("NO.", "PART", "QTY", "SIZE (mm)"),
            ("1", "Shell, upper (head)", "1", "80 x 55, 2.5 wall"),
            ("2", "Shell, lower", "1", "80 x 55, 2.5 wall"),
            ("3", "Platform 1 (battery)", "1", "70 x 48 x 1.6"),
            ("4", "Platform 2 (drivers)", "1", "70 x 46 x 1.6"),
            ("5", "Platform 3 (ESP32)", "1", "56 x 27 x 1.6"),
            ("6", "Standoff, lower", "4", "dia 5.5 x 18"),
            ("7", "Standoff, upper", "2", "dia 5.5 x 20"),
            ("8", "N20 motor + gearbox + encoder", "2", "26 x 10 x 12 (+ 9.5 shaft)"),
            ("9", "Wheel and tyre", "2", f"dia {WHEEL_D} x {WHEEL_W}"),
            ("10", "LiPo 2S 1000 mAh", "1", "68 x 37 x 12"),
            ("11", "ESP32 dev board", "1", "51 x 26"),
            ("12", "MPU-6050 (GY-521)", "1", "20 x 15"),
            ("13", "DRV8833 motor driver", "1", "20 x 15"),
            ("14", "Buck converter 5 V 3 A", "1", "26.4 x 15"),
            ("15", "OLED 1.3\" SH1106", "1", "35.4 x 33.5"),
            ("16", "Face bezel", "1", "38 x 23 x 5.3")]
    table(ax, 272, 143, [10, 58, 10, 50], rows, rowh=4.7, size=6.1, aligns=["center", "left", "center", "left"])
    title_block(ax, "BO-BOT  Self-Balancing Cat Robot", "General arrangement, 3D printed shell", "1 of 2", "BB-GA-01")
    fig.savefig(os.path.join(OUT, "sheet1-general-arrangement.png"), dpi=200)
    plt.close(fig)


# ================================================================== SHEET 2
def box_(ax, x, y, w, h, lab, sub="", lw=1.0, size=7):
    rect(ax, x, y, x + w, y + h, lw, fc="white")
    txt(ax, x + w / 2, y + h / 2 + (1.6 if sub else 0), lab, size, ha="center", weight="bold")
    if sub: txt(ax, x + w / 2, y + h / 2 - 2.4, sub, 5.6, ha="center")


def wire(ax, pts, lab=None, lpos=None, ls="-", lw=0.9, size=5.8, ha="center", arrows="end"):
    line(ax, pts, lw, ls)
    if arrows in ("end", "both"): arrow(ax, pts[-2], pts[-1])
    if arrows == "both": arrow(ax, pts[1], pts[0])
    if lab: txt(ax, lpos[0], lpos[1], lab, size, ha=ha)


def plan(ax, cx, cy, W, D, holes, name, scale="SCALE 1 : 1"):
    ax.add_patch(FancyBboxPatch((cx - W / 2 + 3, cy - D / 2 + 3), W - 6, D - 6, boxstyle="round,pad=3,rounding_size=3", fc="none", ec=INK, lw=THICK, zorder=3))
    for (x, z) in holes:
        ax.add_patch(Circle((cx + x, cy + z), 1.6, fc="white", ec=INK, lw=MED, zorder=4))
        ax.add_patch(Circle((cx + x, cy + z), 2.75, fc="none", ec=INK, lw=THIN, ls=(0, (2, 1.5)), zorder=4))
    centre(ax, cx - W / 2 - 5, cy, cx + W / 2 + 5, cy); centre(ax, cx, cy - D / 2 - 5, cx, cy + D / 2 + 5)
    view_title(ax, cx, cy - D / 2 - 16, name, scale)


def sheet2():
    fig, ax = new_sheet()
    # ------------------------------------------------ block diagram
    txt(ax, 30, 279, "SYSTEM BLOCK DIAGRAM", 8.5, weight="bold")
    box_(ax, 30, 222, 42, 24, "LiPo 2S", "7.4 V, 1000 mAh")
    box_(ax, 98, 252, 40, 14, "Buck 5 V", "3 A")
    box_(ax, 98, 196, 40, 16, "DRV8833", "dual H-bridge")
    box_(ax, 98, 170, 40, 12, "N20 motors", "L + R, with encoders", size=6.5)
    box_(ax, 170, 218, 46, 48, "ESP32", "dev board, 200 Hz loop")
    box_(ax, 250, 254, 34, 12, "MPU-6050", "I2C 0x68", size=6.5)
    box_(ax, 250, 236, 34, 12, "OLED 1.3\"", "SH1106, I2C", size=6.5)
    box_(ax, 250, 212, 34, 14, "Divider", "10 k / 4.7 k", size=6.5)
    wire(ax, [(72, 240), (86, 240), (86, 259), (98, 259)], "7.4 V", (79, 262), arrows="end")
    wire(ax, [(86, 240), (86, 204), (98, 204)], arrows="end")
    txt(ax, 79, 206.5, "VM", 5.8)
    wire(ax, [(138, 259), (170, 259)], "5 V", (154, 262))
    wire(ax, [(138, 206), (152, 206), (152, 238), (170, 238)], "IN1-IN4 (PWM)", (154, 226), ha="left", arrows="end")
    wire(ax, [(118, 196), (118, 182)], "OUT", (121, 189), ha="left")
    wire(ax, [(138, 176), (196, 176), (196, 218)], "encoders A/B (3V3)", (167, 172.5), ls=(0, (4, 2)), arrows="end")
    wire(ax, [(216, 260), (250, 260)], "I2C", (233, 263), arrows="both")
    wire(ax, [(216, 242), (250, 242)], arrows="both")
    txt(ax, 233, 238.8, "SDA 21 / SCL 22", 5.4)
    wire(ax, [(250, 219), (216, 224)], "GPIO 36", (233, 215.5), arrows="end")
    txt(ax, 30, 208, "Solid: power and signal.  Dashed: encoder lines.", 5.8)
    txt(ax, 30, 203, "All grounds joined at one point.", 5.8)

    # ------------------------------------------------ pin table
    rows = [("SIGNAL", "ESP32 PIN", "GOES TO"),
            ("I2C SDA", "GPIO 21", "MPU-6050, OLED"),
            ("I2C SCL", "GPIO 22", "MPU-6050, OLED"),
            ("Left motor IN1 / IN2", "25 / 26", "DRV8833 AIN1 / AIN2"),
            ("Right motor IN1 / IN2", "27 / 4", "DRV8833 BIN1 / BIN2"),
            ("Left encoder A / B", "32 / 33", "left motor"),
            ("Right encoder A / B", "34 / 35", "right motor"),
            ("Battery sense", "36", "divider mid-point")]
    txt(ax, 292, 279, "PIN MAP", 8.5, weight="bold")
    table(ax, 292, 275, [38, 24, 54], rows, rowh=5.6, size=5.9, aligns=["left", "center", "left"])
    rows2 = [("SUPPLY", "FROM", "TO"),
             ("7.4 V", "LiPo (XT30)", "DRV8833 VM, buck in, divider"),
             ("5 V", "buck out", "ESP32 VIN"),
             ("3.3 V", "ESP32 3V3", "MPU, OLED, encoders")]
    table(ax, 292, 224, [20, 30, 66], rows2, rowh=5.6, size=5.9)

    # ------------------------------------------------ platform plans (top views, front = up)
    PY = 108
    c1, c2, c3 = 62, 152, 244
    # platform 1
    plan(ax, c1, PY, 70, 48, S1, "PLATFORM 1  (BATTERY)")
    rect(ax, c1 - 34, PY - 18.5, c1 + 34, PY + 18.5, MED, fc="white", hatch="....", z=3)
    rect(ax, c1 - 4, PY - 18.5, c1 + 4, PY + 18.5, MED, fc="white", z=3)
    rect(ax, c1 - 5, PY - 26.5, c1 + 5, PY - 18.5, MED, fc="white", z=3)
    leader(ax, (c1 + 20, PY + 8), (c1 + 40, PY + 33), "LiPo 68 x 37 x 12", 6)
    leader(ax, (c1, PY - 23), (c1 + 14, PY - 33), "XT30 lead", 6)
    dim_h(ax, c1 - 25.5, c1 + 25.5, PY + 21, "51", off=18, size=6.3)
    dim_v(ax, PY - 21, PY + 21, c1 - 25.5, "42", off=-14, size=6.3)
    dim_h(ax, c1 - 35, c1 + 35, PY - 24, "70", off=-4, size=6.3)
    # platform 2
    plan(ax, c2, PY, 70, 46, S1 + S2, "PLATFORM 2  (SENSOR + DRIVERS)")
    rect(ax, c2 + 5, PY + 3, c2 + 25, PY + 18, MED, fc="white", z=3)                # mpu
    rect(ax, c2 - 10, PY - 18, c2 + 10, PY - 3, MED, fc="white", z=3)               # drv
    rect(ax, c2 - 33.2, PY + 3, c2 - 6.8, PY + 18, MED, fc="white", z=3)            # buck
    txt(ax, c2 + 15, PY + 10.5, "MPU", 6, ha="center"); txt(ax, c2, PY - 10.5, "DRV8833", 6, ha="center"); txt(ax, c2 - 20, PY + 10.5, "BUCK", 6, ha="center")
    dim_h(ax, c2 + 5, c2 + 25, PY + 18, "20", off=9, size=6.3)
    dim_h(ax, c2 - 33.2, c2 - 6.8, PY + 18, "26.4", off=9, size=6.3)
    dim_v(ax, PY + 3, PY + 18, c2 + 25, "15", off=8, size=6.3)
    dim_h(ax, c2 - 35, c2 + 35, PY - 23, "70", off=-4, size=6.3)
    txt(ax, c2, PY + 26, "", 5)
    # platform 3
    plan(ax, c3, PY, 56, 27, S2, "PLATFORM 3  (ESP32 + OLED)")
    rect(ax, c3 - 25.5, PY - 13, c3 + 25.5, PY + 13, MED, fc="white", z=3)           # esp32 pcb
    rect(ax, c3 - 25.5, PY - 12.75, c3 - 7.5, PY + 12.75, THIN, z=4)                 # module
    rect(ax, c3 + 21.5, PY - 4, c3 + 28.5, PY + 4, THIN, z=4)                        # usb
    txt(ax, c3 + 2, PY, "ESP32", 6.5, ha="center")
    rect(ax, c3 - 17.7, PY + 15, c3 + 17.7, PY + 16.6, MED, ls=(0, (5, 2)), z=3)     # oled board edge (z = 15.8)
    for sx in (1, -1): rect(ax, c3 + sx * 14.5 - 2, PY + 12.3, c3 + sx * 14.5 + 2, PY + 16.2, THIN, z=3)
    leader(ax, (c3, PY + 15.8), (c3 + 12, PY + 28), "OLED board (vertical, front)", 6)
    dim_h(ax, c3 - 25.5, c3 + 25.5, PY - 13, "51", off=-9, size=6.3)
    dim_v(ax, PY - 13, PY + 13, c3 + 28.5, "26", off=7, size=6.3)
    txt(ax, 106, PY + 29, "FRONT", 6.5, ha="center", weight="bold"); arrow(ax, (106, PY + 8), (106, PY + 24))

    # ------------------------------------------------ notes
    nx = 292; ny = 160
    txt(ax, nx, ny, "NOTES", 8, weight="bold")
    for i, n in enumerate(["1.  Dimensions in mm. Layout from CatRobot.py (x = across, z = to the face).",
                           "2.  Platform holes dia 3.2 at (+/-25.5, +/-21); the upper pair at (+/-25.5, 0).",
                           "3.  Power the encoders from 3V3, not 5 V (ESP32 inputs are 3.3 V only).",
                           "4.  DRV8833 SLP pin to 3V3, or the motors stay off.",
                           "5.  Check XT30 polarity before the first power-up.",
                           "6.  Do not run from USB and the battery together.",
                           "7.  Pins match firmware/balance_bot/include/config.h."]):
        txt(ax, nx, ny - 7 - i * 5.2, n, 5.9)
    title_block(ax, "BO-BOT  Self-Balancing Cat Robot", "Electronics layout and wiring", "2 of 2", "BB-EL-01")
    fig.savefig(os.path.join(OUT, "sheet2-electronics.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    sheet1()
    sheet2()
