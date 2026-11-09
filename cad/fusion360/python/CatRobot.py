"""
Self-Balancing Cat Robot v2 - Fusion 360 script (works with Y-up AND Z-up)
Each part = its own component (hide with the lightbulb). Units mm.
Robot axes (internal): X width, Y up, Z front(face). Ground = 0, wheel centre height 17.
Run on a NEW EMPTY parametric design.
"""
import adsk.core, adsk.fusion, traceback, math

app = adsk.core.Application.get()
ui = app.userInterface
design = adsk.fusion.Design.cast(app.activeProduct)
root = design.rootComponent
tbm = adsk.fusion.TemporaryBRepManager.get()

try:
    YUP = (app.preferences.generalPreferences.defaultModelingOrientation ==
           adsk.core.DefaultModelingOrientations.YUpModelingOrientation)
except:
    YUP = True

WHITE = (248, 248, 250); BLUE = (70, 170, 255); BLACK = (35, 35, 38)
GOLD = (212, 175, 55); GREEN = (20, 120, 60); RED = (200, 40, 40)
NAVY = (25, 50, 130); YELLOW = (240, 200, 20); SILVER = (185, 185, 190)
ORANGE = (210, 120, 40); TYRE = (25, 25, 25); PLATE = (235, 235, 215)
errors = []


def mm(v):
    return v / 10.0


def M(x, y, z):
    """robot coords -> Fusion world coords"""
    return (x, y, z) if YUP else (x, -z, y)


def P(x, y, z):
    a, b, c = M(x, y, z)
    return adsk.core.Point3D.create(mm(a), mm(b), mm(c))


def box(cx, cy, cz, sx, sy, sz):
    wd = M(0, 1, 0)
    obb = adsk.core.OrientedBoundingBox3D.create(
        P(cx, cy, cz),
        adsk.core.Vector3D.create(1, 0, 0),
        adsk.core.Vector3D.create(wd[0], wd[1], wd[2]),
        mm(sx), mm(sy), mm(sz))
    return tbm.createBox(obb)


def cyl(p1, p2, r):
    return tbm.createCylinderOrCone(P(*p1), mm(r), P(*p2), mm(r))


def cone(p1, r1, p2, r2):
    return tbm.createCylinderOrCone(P(*p1), mm(r1), P(*p2), mm(r2))


def cut(a, b):
    tbm.booleanOperation(a, b, adsk.fusion.BooleanTypes.DifferenceBooleanType); return a


def join(a, b):
    tbm.booleanOperation(a, b, adsk.fusion.BooleanTypes.UnionBooleanType); return a


def inter(a, b):
    tbm.booleanOperation(a, b, adsk.fusion.BooleanTypes.IntersectBooleanType); return a


_cache = {}


def paint(body, rgb):
    try:
        if rgb not in _cache:
            base = None
            for lib in app.materialLibraries:
                try:
                    base = lib.appearances.itemByName('Paint - Enamel Glossy (White)')
                except:
                    base = None
                if base:
                    break
            if not base:
                return
            cp = design.appearances.addByCopy(base, 'RB_%d_%d_%d' % rgb)
            pr = adsk.core.ColorProperty.cast(cp.appearanceProperties.itemByName('Color'))
            pr.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
            _cache[rgb] = cp
        body.appearance = _cache[rgb]
    except:
        pass


def newocc(name):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ


def add(comp, tmp, name, rgb=None):
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    b = comp.bRepBodies.add(tmp, bf)
    bf.finishEdit()
    b.name = name
    if rgb:
        paint(b, rgb)
    return b


def rrect(sk, hw, hd, r):
    A = sk.sketchCurves.sketchArcs
    L = sk.sketchCurves.sketchLines
    cx, cy = hw - r, hd - r
    p = lambda x, y: adsk.core.Point3D.create(mm(x), mm(y), 0)
    a1 = A.addByCenterStartSweep(p(cx, cy), p(cx + r, cy), math.pi / 2)
    a2 = A.addByCenterStartSweep(p(-cx, cy), p(-cx, cy + r), math.pi / 2)
    a3 = A.addByCenterStartSweep(p(-cx, -cy), p(-cx - r, -cy), math.pi / 2)
    a4 = A.addByCenterStartSweep(p(cx, -cy), p(cx, -cy - r), math.pi / 2)
    L.addByTwoPoints(a1.endSketchPoint, a2.startSketchPoint)
    L.addByTwoPoints(a2.endSketchPoint, a3.startSketchPoint)
    L.addByTwoPoints(a3.endSketchPoint, a4.startSketchPoint)
    L.addByTwoPoints(a4.endSketchPoint, a1.startSketchPoint)


def egg_loft(comp, secs, inset):
    lofts = comp.features.loftFeatures
    li = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    base = comp.xZConstructionPlane if YUP else comp.xYConstructionPlane
    n = adsk.core.Plane.cast(base.geometry).normal
    sgn = 1 if (n.y if YUP else n.z) > 0 else -1
    for y, s in secs:
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(base, adsk.core.ValueInput.createByReal(sgn * mm(y)))
        pl = comp.constructionPlanes.add(pi)
        sk = comp.sketches.add(pl)
        hw = 40.0 * s - inset
        hd = 27.5 * s - inset
        r = max(15.0 * s - inset, 1.0)
        r = min(r, hw - 0.3, hd - 0.3)
        rrect(sk, hw, hd, r)
        li.loftSections.add(sk.profiles.item(0))
    li.isSolid = True
    return lofts.add(li).bodies.item(0)


def egg_s(t):
    """smooth egg width factor, t = 0..1 from base to top"""
    if t <= 0.32:
        s = 0.82 + 0.18 * math.sin(math.pi / 2 * t / 0.32)
    else:
        u = (t - 0.32) / 0.68
        s = math.sqrt(max(1 - u ** 2.2, 0.0))
    return max(s, 0.14)


def egg_y(t):
    return 2 + 98 * t


def part(fn, *a):
    try:
        return fn(*a)
    except:
        errors.append(fn.__name__ + ': ' + traceback.format_exc().splitlines()[-1])


# ------------------------------------------------------------ shell
def make_shell():
    occ = newocc('_scratch')
    sc = occ.component
    T_OUT = [0, .06, .12, .2, .3, .4, .5, .6, .7, .78, .85, .91, .96, 1.0]
    T_IN = [0, .06, .12, .2, .3, .4, .5, .6, .7, .78, .85, .91]
    outer = egg_loft(sc, [(egg_y(t), egg_s(t)) for t in T_OUT], 0.0)
    inner_secs = [(0.0, egg_s(0))] + [(egg_y(t), egg_s(t)) for t in T_IN]
    inner = egg_loft(sc, inner_secs, 2.5)
    outer_t = tbm.copy(outer)
    inner_t = tbm.copy(inner)
    env_t = tbm.copy(inner)
    occ.deleteMe()                                   # scratch lofts no longer needed

    body = cut(outer_t, inner_t)                     # hollow, open at bottom
    for s in (1, -1):                                # wheel arches
        body = cut(body, cyl((s * 28, 17, 0), (s * 46, 17, 0), 19))
    body = cut(body, box(0, 67, 24, 30.4, 15.2, 20))  # OLED window (1.3in: active area 29.42 x 14.7 + margin)

    SPLIT = 40.0
    low = inter(tbm.copy(body), box(0, SPLIT / 2 - 5, 0, 200, SPLIT + 10, 200))
    up = inter(tbm.copy(body), box(0, SPLIT + 50, 0, 200, 100, 200))
    c1 = newocc('Shell_Lower').component
    add(c1, low, 'Shell_Lower_Body', WHITE)
    c2 = newocc('Shell_Upper_Head').component
    add(c2, up, 'Shell_Upper_Body', WHITE)
    return env_t


def make_bezel():
    c = newocc('Face_Bezel').component
    b = cut(box(0, 67, 23.65, 38, 23, 5.3), box(0, 67, 23.65, 30.4, 15.2, 12))
    add(c, b, 'Bezel', BLACK)


def make_ears():
    c = newocc('Ears').component
    for s, nm in ((1, 'R'), (-1, 'L')):
        o = inter(cone((s * 15, 87, 0), 9, (s * 22, 110, 0), 0.8),
                  box(s * 18, 100, 0, 40, 40, 4.5))
        add(c, o, 'Ear_' + nm, WHITE)
        i = inter(cone((s * 15.5, 88, 0), 5.5, (s * 21.2, 106, 0), 0.6),
                  box(s * 18, 98, 1.4, 40, 40, 1.9))
        add(c, i, 'EarInner_' + nm, BLUE)


def make_bow():
    c = newocc('BowTie').component
    for s, nm in ((1, 'R'), (-1, 'L')):
        add(c, cone((s * 2.5, 46, 28.3), 2, (s * 11, 46, 28.3), 5), 'Bow_' + nm, BLUE)
    add(c, cyl((-2.5, 46, 28.3), (2.5, 46, 28.3), 3), 'Bow_Knot', BLUE)


def make_whiskers():
    c = newocc('Whiskers').component
    for s, side in ((1, 'R'), (-1, 'L')):
        for i, (y, dy) in enumerate(((64, 3), (60, 0), (56, -3))):
            add(c, cyl((s * 25, y, 23), (s * 35, y + dy, 15.5), 0.6),
                'Whisker_%s%d' % (side, i + 1), BLACK)


def make_leds():
    c = newocc('LED_Strips').component
    for s, nm in ((1, 'R'), (-1, 'L')):
        x0, x1 = (s * 37.0, s * 40.6)
        ring = cut(cyl((x0, 17, 0), (x1, 17, 0), 22.4), cyl((x0 - s, 17, 0), (x1 + s, 17, 0), 20.5))
        ring = inter(ring, box(s * 39, 40, 0, 8, 46, 60))   # upper half only
        add(c, ring, 'LED_' + nm, BLUE)


# ------------------------------------------------------------ chassis
def make_platform(name, y0, W, D, env, pts):
    c = newocc(name).component
    b = inter(box(0, y0 + 0.8, 0, W, 1.6, D), tbm.copy(env))
    for (x, z) in pts:
        b = cut(b, cyl((x, y0 - 1, z), (x, y0 + 3, z), 1.6))
    add(c, b, name, PLATE)


def make_standoffs(name, y0, y1, pts):
    c = newocc(name).component
    for i, (x, z) in enumerate(pts):
        add(c, cyl((x, y0, z), (x, y1, z), 2.75), '%s_%d' % (name, i + 1), GOLD)


def dflat(xc):
    return box(xc, 17, -0.15, 12, 3.2, 2.7)


def make_wheel(name, sx):
    c = newocc(name).component
    x0 = sx * 35.0
    xa, xb = x0 - 3.25, x0 + 3.25
    tyre = cut(cyl((xa, 17, 0), (xb, 17, 0), 17), cyl((xa - 1, 17, 0), (xb + 1, 17, 0), 13))
    add(c, tyre, name + '_Tyre', TYRE)
    rim = cyl((xa + 0.75, 17, 0), (xb - 0.75, 17, 0), 13)
    for k in range(5):
        th = 2 * math.pi * k / 5
        y, z = 17 + 8.2 * math.cos(th), 8.2 * math.sin(th)
        rim = cut(rim, cyl((xa - 1, y, z), (xb + 1, y, z), 2.6))
    rim = cut(rim, inter(cyl((xa - 1, 17, 0), (xb + 1, 17, 0), 1.5), dflat(x0)))
    add(c, rim, name + '_Rim', WHITE)


def make_motor(name, sx):
    c = newocc(name).component
    add(c, box(sx * 21, 17, 0, 10, 10, 12), name + '_Gearbox', SILVER)
    add(c, box(sx * 9.5, 17, 0, 13, 10, 12), name + '_Motor', ORANGE)
    add(c, box(sx * 2.25, 17, 0, 1.5, 10, 12), name + '_Encoder', GREEN)
    add(c, inter(cyl((sx * 26, 17, 0), (sx * 35.5, 17, 0), 1.5), dflat(sx * 30)), name + '_Shaft', SILVER)


# ------------------------------------------------------------ electronics
def make_battery():
    c = newocc('LiPo_Battery_2S_1000mAh').component
    y0 = 23.6
    add(c, box(0, y0 + 6, 0, 68, 12, 37), 'Battery_68x37x12', NAVY)
    add(c, box(0, y0 + 6, 0, 8, 13.6, 38.6), 'Strap', BLACK)
    add(c, box(0, y0 + 6, -22.5, 10, 5, 8), 'XT30', YELLOW)


def make_esp32():
    c = newocc('ESP32_DevBoard').component
    y = 64.8
    add(c, box(0, y + 0.8, 0, 51, 1.6, 26), 'ESP32_PCB_51x26', BLACK)
    add(c, box(-16.5, y + 3.15, 0, 18, 3.1, 25.5), 'ESP32_Module', SILVER)
    add(c, box(25.0, y + 3.1, 0, 7, 3, 8), 'USB_Port', SILVER)
    add(c, box(0, y + 2.85, 11.5, 38, 2.5, 2.5), 'Header_A', BLACK)
    add(c, box(0, y + 2.85, -11.5, 38, 2.5, 2.5), 'Header_B', BLACK)


def make_mpu():
    c = newocc('MPU6050').component
    y, cx, cz = 43.2, 15, 10.5
    add(c, box(cx, y + 0.8, cz, 20, 1.6, 15), 'MPU_PCB_20x15', BLUE)
    add(c, box(cx, y + 2.1, cz, 4, 1, 4), 'MPU_Chip', BLACK)
    add(c, box(cx, y + 2.85, cz + 6, 16, 2.5, 2.5), 'MPU_Header', BLACK)


def make_drv():
    c = newocc('DRV8833').component
    y, cx, cz = 43.2, 0, -10.5
    add(c, box(cx, y + 0.8, cz, 20, 1.6, 15), 'DRV_PCB_20x15', RED)
    add(c, box(cx, y + 2.35, cz, 6, 1.5, 4), 'DRV_Chip', BLACK)
    add(c, box(cx, y + 2.85, cz - 6, 16, 2.5, 2.5), 'DRV_Header', BLACK)


def make_buck():
    c = newocc('DCDC_Buck').component
    y, cx, cz = 43.2, -20, 10.5   # cx moved 2 mm to clear the 1.3in OLED board
    add(c, box(cx, y + 0.8, cz, 26.4, 1.6, 15), 'Buck_PCB_26.4x15', RED)
    add(c, box(cx - 4, y + 4.5, cz, 10, 5.8, 10), 'Buck_Inductor', SILVER)
    add(c, box(cx + 8, y + 3.6, cz, 6, 4, 8), 'Buck_Capacitor', BLACK)


def make_oled():
    # 1.3in SH1106 I2C module: board ~35.4 x 33.5 mm, active area 29.42 x 14.7 mm (seller listings; verify with calipers)
    c = newocc('OLED_1.3in').component
    add(c, box(0, 64.5, 15.8, 35.4, 33.5, 1.6), 'OLED_PCB_35.4x33.5', BLACK)
    add(c, box(0, 67, 16.9, 34.5, 19, 0.6), 'OLED_Glass', (20, 20, 25))
    add(c, box(0, 67, 17.275, 29.42, 14.7, 0.15), 'OLED_ActiveArea_29.42x14.7', (10, 25, 80))
    add(c, box(0, 49.35, 13.75, 10, 2.5, 2.5), 'OLED_Header', BLACK)
    m = newocc('OLED_Mount').component
    for s in (1, -1):
        add(m, box(s * 14.5, 64.5, 14.25, 4, 4, 1.5), 'OLED_Mount_' + ('R' if s > 0 else 'L'), WHITE)


# ------------------------------------------------------------ run
def run(context):
    try:
        if design is None or design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
            ui.messageBox('Open a NEW design with history (parametric) on, then re-run.')
            return
        try:
            design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        except:
            pass
        for n, v in (('wheel_d', 34), ('wheel_w', 6.5), ('track', 70), ('gap_top', 20), ('gap_mid', 20),
                     ('gap_bat', 18), ('shell_t', 2.5), ('body_W', 80), ('body_D', 55), ('body_H', 110)):
            try:
                design.userParameters.add(n, adsk.core.ValueInput.createByString('%s mm' % v), 'mm', '')
            except:
                pass

        env = part(make_shell)
        part(make_bezel); part(make_ears); part(make_bow); part(make_whiskers); part(make_leds)

        s1 = [(25.5, 21), (-25.5, 21), (25.5, -21), (-25.5, -21)]
        s2 = [(25.5, 0), (-25.5, 0)]
        if env is not None:
            part(make_platform, 'Platform_1_Battery', 22.0, 70, 48, env, s1)
            part(make_platform, 'Platform_2_Drivers', 41.6, 70, 46, env, s1 + s2)
            part(make_platform, 'Platform_3_ESP32', 63.2, 56, 27, env, s2)
        part(make_standoffs, 'Standoffs_L1_18mm', 23.6, 41.6, s1)
        part(make_standoffs, 'Standoffs_L2_20mm', 43.2, 63.2, s2)
        part(make_wheel, 'Wheel_L', -1); part(make_wheel, 'Wheel_R', 1)
        part(make_motor, 'Motor_N20_L', -1); part(make_motor, 'Motor_N20_R', 1)
        part(make_battery); part(make_buck); part(make_drv); part(make_mpu)
        part(make_esp32); part(make_oled)

        try:
            app.activeViewport.fit()
        except:
            pass
        msg = 'Robot built (%s).\nHide "Shell_Upper_Head" / "Shell_Lower" with the lightbulb to see inside.' % \
              ('Y-up' if YUP else 'Z-up')
        if errors:
            msg += '\n\nSome parts failed - send me this:\n' + '\n'.join(errors)
        ui.messageBox(msg)
    except:
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
