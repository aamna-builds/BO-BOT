/*
 * Self-Balancing Cat Robot v2  -  Fusion 360 C++ add-in
 * Works with Y-up and Z-up designs. Every part is its own component. Units: mm.
 * Robot axes (internal): X width, Y up, Z front (face). Ground = 0, wheel centre height = 17.
 * Run on a NEW EMPTY parametric design.
 *
 * Matches the reference sheet: 80 x 55 x 110 mm shell, 34 x 6.5 mm wheels, 70 mm track,
 * platform spacing 20/20/18 mm, white shell + blue ears/bow/LED strips, black whiskers & bezel,
 * gold standoffs, 0.96" OLED with blue dot-matrix face (happy eyes + smile).
 */
#include <Core/CoreAll.h>
#include <Fusion/FusionAll.h>

#include <cmath>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

using namespace adsk::core;
using namespace adsk::fusion;

static const double PI_ = 3.14159265358979323846;

struct RGB { int r, g, b; };
static const RGB WHITE{248, 248, 250}, BLUE{70, 170, 255}, BLACK{35, 35, 38};
static const RGB GOLD{212, 175, 55}, GREEN{20, 120, 60}, RED{200, 40, 40};
static const RGB NAVY{25, 50, 130}, YELLOW{240, 200, 20}, SILVER{185, 185, 190};
static const RGB ORANGE{210, 120, 40}, TYRE{25, 25, 25}, PLATE{235, 235, 215};
static const RGB GLASS{20, 20, 25}, ACTIVE{10, 25, 80}, DOT{120, 200, 255};

typedef std::vector<std::pair<double, double> > PtList;

static Ptr<Application> app;
static Ptr<UserInterface> ui;
static Ptr<Design> design;
static Ptr<Component> root;
static Ptr<TemporaryBRepManager> tbm;
static bool YUP = true;
static std::vector<std::string> errors;
static std::map<int, Ptr<Appearance> > appCache;

// ------------------------------------------------------------ helpers
static void need(bool ok, const char* what) { if (!ok) throw std::runtime_error(what); }
static double mm(double v) { return v / 10.0; }

static void M(double x, double y, double z, double& a, double& b, double& c)
{
    if (YUP) { a = x; b = y; c = z; }
    else     { a = x; b = -z; c = y; }
}

static Ptr<Point3D> P(double x, double y, double z)
{
    double a, b, c; M(x, y, z, a, b, c);
    return Point3D::create(mm(a), mm(b), mm(c));
}

typedef Ptr<BRepBody> Body;

static Body box(double cx, double cy, double cz, double sx, double sy, double sz)
{
    double a, b, c; M(0, 1, 0, a, b, c);
    Ptr<OrientedBoundingBox3D> obb = OrientedBoundingBox3D::create(
        P(cx, cy, cz), Vector3D::create(1, 0, 0), Vector3D::create(a, b, c),
        mm(sx), mm(sy), mm(sz));
    Body r = tbm->createBox(obb);
    need(r != nullptr, "createBox");
    return r;
}

static Body cyl(double x1, double y1, double z1, double x2, double y2, double z2, double r)
{
    Body b = tbm->createCylinderOrCone(P(x1, y1, z1), mm(r), P(x2, y2, z2), mm(r));
    need(b != nullptr, "createCylinder");
    return b;
}

static Body cone(double x1, double y1, double z1, double r1,
                 double x2, double y2, double z2, double r2)
{
    Body b = tbm->createCylinderOrCone(P(x1, y1, z1), mm(r1), P(x2, y2, z2), mm(r2));
    need(b != nullptr, "createCone");
    return b;
}

static Body cut(Body a, Body b)   { need(tbm->booleanOperation(a, b, BooleanTypes::DifferenceBooleanType), "cut");  return a; }
static Body join(Body a, Body b)  { need(tbm->booleanOperation(a, b, BooleanTypes::UnionBooleanType), "join");      return a; }
static Body inter(Body a, Body b) { need(tbm->booleanOperation(a, b, BooleanTypes::IntersectBooleanType), "inter"); return a; }

static void paint(Body body, RGB c)
{
    try {
        int key = (c.r << 16) | (c.g << 8) | c.b;
        if (appCache.find(key) == appCache.end()) {
            Ptr<Appearance> base;
            Ptr<MaterialLibraries> libs = app->materialLibraries();
            for (size_t i = 0; i < libs->count() && !base; ++i)
                base = libs->item(i)->appearances()->itemByName("Paint - Enamel Glossy (White)");
            if (!base) return;
            std::string nm = "RB_" + std::to_string(c.r) + "_" + std::to_string(c.g) + "_" + std::to_string(c.b);
            Ptr<Appearance> cp = design->appearances()->addByCopy(base, nm);
            if (!cp) return;
            Ptr<ColorProperty> pr = cp->appearanceProperties()->itemByName("Color");
            if (!pr) return;
            pr->value(Color::create(c.r, c.g, c.b, 255));
            appCache[key] = cp;
        }
        body->appearance(appCache[key]);
    } catch (...) {}
}

static Ptr<Component> newocc(const std::string& name)
{
    Ptr<Occurrence> occ = root->occurrences()->addNewComponent(Matrix3D::create());
    need(occ != nullptr, "addNewComponent");
    occ->component()->name(name);
    return occ->component();
}

static Ptr<Occurrence> newoccOcc(const std::string& name)
{
    Ptr<Occurrence> occ = root->occurrences()->addNewComponent(Matrix3D::create());
    need(occ != nullptr, "addNewComponent");
    occ->component()->name(name);
    return occ;
}

static Body add(Ptr<Component> comp, Body tmp, const std::string& name, const RGB* rgb = nullptr)
{
    need(tmp != nullptr, "add: null body");
    Ptr<BaseFeature> bf = comp->features()->baseFeatures()->add();
    need(bf != nullptr, "baseFeature");
    bf->startEdit();
    Body b = comp->bRepBodies()->add(tmp, bf);
    bf->finishEdit();
    need(b != nullptr, "bRepBodies.add");
    b->name(name);
    if (rgb) paint(b, *rgb);
    return b;
}

static void rrect(Ptr<Sketch> sk, double hw, double hd, double r)
{
    Ptr<SketchArcs> A = sk->sketchCurves()->sketchArcs();
    Ptr<SketchLines> L = sk->sketchCurves()->sketchLines();
    double cx = hw - r, cy = hd - r;
    auto p = [](double x, double y) { return Point3D::create(mm(x), mm(y), 0); };
    Ptr<SketchArc> a1 = A->addByCenterStartSweep(p(cx, cy),   p(cx + r, cy),   PI_ / 2);
    Ptr<SketchArc> a2 = A->addByCenterStartSweep(p(-cx, cy),  p(-cx, cy + r),  PI_ / 2);
    Ptr<SketchArc> a3 = A->addByCenterStartSweep(p(-cx, -cy), p(-cx - r, -cy), PI_ / 2);
    Ptr<SketchArc> a4 = A->addByCenterStartSweep(p(cx, -cy),  p(cx, -cy - r),  PI_ / 2);
    L->addByTwoPoints(a1->endSketchPoint(), a2->startSketchPoint());
    L->addByTwoPoints(a2->endSketchPoint(), a3->startSketchPoint());
    L->addByTwoPoints(a3->endSketchPoint(), a4->startSketchPoint());
    L->addByTwoPoints(a4->endSketchPoint(), a1->startSketchPoint());
}

static Body egg_loft(Ptr<Component> comp, const PtList& secs, double inset)
{
    Ptr<LoftFeatures> lofts = comp->features()->loftFeatures();
    Ptr<LoftFeatureInput> li = lofts->createInput(FeatureOperations::NewBodyFeatureOperation);
    Ptr<ConstructionPlane> base = YUP ? comp->xZConstructionPlane() : comp->xYConstructionPlane();
    Ptr<Plane> pl = base->geometry();
    Ptr<Vector3D> n = pl->normal();
    double sgn = ((YUP ? n->y() : n->z()) > 0) ? 1.0 : -1.0;

    for (size_t i = 0; i < secs.size(); ++i) {
        double y = secs[i].first, s = secs[i].second;
        Ptr<ConstructionPlaneInput> pi = comp->constructionPlanes()->createInput();
        pi->setByOffset(base, ValueInput::createByReal(sgn * mm(y)));
        Ptr<ConstructionPlane> plane = comp->constructionPlanes()->add(pi);
        Ptr<Sketch> sk = comp->sketches()->add(plane);
        double hw = 40.0 * s - inset;
        double hd = 27.5 * s - inset;
        double r = std::max(15.0 * s - inset, 1.0);
        r = std::min(r, std::min(hw - 0.3, hd - 0.3));
        rrect(sk, hw, hd, r);
        li->loftSections()->add(sk->profiles()->item(0));
    }
    li->isSolid(true);
    Ptr<LoftFeature> lf = lofts->add(li);
    need(lf != nullptr, "loft failed");
    return lf->bodies()->item(0);
}

static double egg_s(double t)
{
    double s;
    if (t <= 0.32) s = 0.82 + 0.18 * std::sin(PI_ / 2 * t / 0.32);
    else {
        double u = (t - 0.32) / 0.68;
        s = std::sqrt(std::max(1 - std::pow(u, 2.2), 0.0));
    }
    return std::max(s, 0.14);
}
static double egg_y(double t) { return 2 + 98 * t; }

template <class F>
static void part(const char* name, F f)
{
    try { f(); }
    catch (const std::exception& e) { errors.push_back(std::string(name) + ": " + e.what()); }
    catch (...) { errors.push_back(std::string(name) + ": unknown error"); }
}

// ------------------------------------------------------------ shell
static Body make_shell()
{
    Ptr<Occurrence> occ = newoccOcc("_scratch");
    Ptr<Component> sc = occ->component();

    const double T_OUT[] = {0, .06, .12, .2, .3, .4, .5, .6, .7, .78, .85, .91, .96, 1.0};
    const double T_IN[]  = {0, .06, .12, .2, .3, .4, .5, .6, .7, .78, .85, .91};

    PtList outerSecs, innerSecs;
    for (double t : T_OUT) outerSecs.push_back({egg_y(t), egg_s(t)});
    innerSecs.push_back({0.0, egg_s(0)});
    for (double t : T_IN) innerSecs.push_back({egg_y(t), egg_s(t)});

    Body outer = egg_loft(sc, outerSecs, 0.0);
    Body inner = egg_loft(sc, innerSecs, 2.5);
    Body outer_t = tbm->copy(outer);
    Body inner_t = tbm->copy(inner);
    Body env_t   = tbm->copy(inner);
    occ->deleteMe();                                   // scratch lofts no longer needed

    Body body = cut(outer_t, inner_t);                 // hollow, open at bottom
    for (int s = -1; s <= 1; s += 2)                   // wheel arches
        body = cut(body, cyl(s * 28, 17, 0, s * 46, 17, 0, 19));
    body = cut(body, box(0, 67, 24, 22.5, 11.3, 20));  // OLED window

    const double SPLIT = 40.0;
    Body low = inter(tbm->copy(body), box(0, SPLIT / 2 - 5, 0, 200, SPLIT + 10, 200));
    Body up  = inter(tbm->copy(body), box(0, SPLIT + 50, 0, 200, 100, 200));
    add(newocc("Shell_Lower"), low, "Shell_Lower_Body", &WHITE);
    add(newocc("Shell_Upper_Head"), up, "Shell_Upper_Body", &WHITE);
    return env_t;
}

static void make_bezel()
{
    Ptr<Component> c = newocc("Face_Bezel");
    Body b = cut(box(0, 67, 24.0, 30, 18, 4.0), box(0, 67, 24.0, 22.5, 11.3, 12));
    add(c, b, "Bezel", &BLACK);
}

static void make_ears()
{
    Ptr<Component> c = newocc("Ears");
    for (int s = 1; s >= -1; s -= 2) {
        const char* nm = (s == 1) ? "R" : "L";
        Body o = inter(cone(s * 15, 87, 0, 9, s * 22, 110, 0, 0.8), box(s * 18, 100, 0, 40, 40, 4.5));
        add(c, o, std::string("Ear_") + nm, &WHITE);
        Body i = inter(cone(s * 15.5, 88, 0, 5.5, s * 21.2, 106, 0, 0.6), box(s * 18, 98, 1.4, 40, 40, 1.9));
        add(c, i, std::string("EarInner_") + nm, &BLUE);
    }
}

static void make_bow()
{
    Ptr<Component> c = newocc("BowTie");
    for (int s = 1; s >= -1; s -= 2)
        add(c, cone(s * 2.5, 46, 28.3, 2, s * 11, 46, 28.3, 5), (s == 1) ? "Bow_R" : "Bow_L", &BLUE);
    add(c, cyl(-2.5, 46, 28.3, 2.5, 46, 28.3, 3), "Bow_Knot", &BLUE);
}

static void make_whiskers()
{
    Ptr<Component> c = newocc("Whiskers");
    const double ys[3][2] = {{64, 3}, {60, 0}, {56, -3}};
    for (int s = 1; s >= -1; s -= 2)
        for (int i = 0; i < 3; ++i) {
            double y = ys[i][0], dy = ys[i][1];
            add(c, cyl(s * 25, y, 23, s * 35, y + dy, 15.5, 0.6),
                std::string("Whisker_") + (s == 1 ? "R" : "L") + std::to_string(i + 1), &BLACK);
        }
}

static void make_leds()
{
    Ptr<Component> c = newocc("LED_Strips");
    for (int s = 1; s >= -1; s -= 2) {
        double x0 = s * 37.0, x1 = s * 40.6;
        Body ring = cut(cyl(x0, 17, 0, x1, 17, 0, 22.4), cyl(x0 - s, 17, 0, x1 + s, 17, 0, 20.5));
        ring = inter(ring, box(s * 39, 40, 0, 8, 46, 60));          // upper half only
        add(c, ring, (s == 1) ? "LED_R" : "LED_L", &BLUE);
    }
}

// ------------------------------------------------------------ chassis
static void make_platform(const std::string& name, double y0, double W, double D, Body env, const PtList& pts)
{
    Ptr<Component> c = newocc(name);
    Body b = inter(box(0, y0 + 0.8, 0, W, 1.6, D), tbm->copy(env));
    for (auto& p : pts) b = cut(b, cyl(p.first, y0 - 1, p.second, p.first, y0 + 3, p.second, 1.6));
    add(c, b, name, &PLATE);
}

static void make_standoffs(const std::string& name, double y0, double y1, const PtList& pts)
{
    Ptr<Component> c = newocc(name);
    for (size_t i = 0; i < pts.size(); ++i)
        add(c, cyl(pts[i].first, y0, pts[i].second, pts[i].first, y1, pts[i].second, 2.75),
            name + "_" + std::to_string(i + 1), &GOLD);
}

static Body dflat(double xc) { return box(xc, 17, -0.15, 12, 3.2, 2.7); }

static void make_wheel(const std::string& name, int sx)
{
    Ptr<Component> c = newocc(name);
    double x0 = sx * 35.0, xa = x0 - 3.25, xb = x0 + 3.25;
    Body tyre = cut(cyl(xa, 17, 0, xb, 17, 0, 17), cyl(xa - 1, 17, 0, xb + 1, 17, 0, 13));
    add(c, tyre, name + "_Tyre", &TYRE);
    Body rim = cyl(xa + 0.75, 17, 0, xb - 0.75, 17, 0, 13);
    for (int k = 0; k < 3; ++k) {                       // 3 spokes, as in the reference picture
        double th = 2 * PI_ * k / 3 + PI_ / 3;
        double y = 17 + 8.4 * std::cos(th), z = 8.4 * std::sin(th);
        rim = cut(rim, cyl(xa - 1, y, z, xb + 1, y, z, 4.4));
    }
    rim = cut(rim, inter(cyl(xa - 1, 17, 0, xb + 1, 17, 0, 1.5), dflat(x0)));
    add(c, rim, name + "_Rim", &WHITE);
}

static void make_motor(const std::string& name, int sx)
{
    Ptr<Component> c = newocc(name);
    add(c, box(sx * 21, 17, 0, 10, 10, 12),     name + "_Gearbox", &SILVER);
    add(c, box(sx * 9.5, 17, 0, 13, 10, 12),    name + "_Motor",   &ORANGE);
    add(c, box(sx * 2.25, 17, 0, 1.5, 10, 12),  name + "_Encoder", &GREEN);
    add(c, inter(cyl(sx * 26, 17, 0, sx * 35.5, 17, 0, 1.5), dflat(sx * 30)), name + "_Shaft", &SILVER);
}

// ------------------------------------------------------------ electronics
static void make_battery()
{
    Ptr<Component> c = newocc("LiPo_Battery_2S_1000mAh");
    double y0 = 23.6;
    add(c, box(0, y0 + 6, 0, 68, 12, 37),        "Battery_68x37x12", &NAVY);
    add(c, box(0, y0 + 6, 0, 8, 13.6, 38.6),     "Strap", &BLACK);
    add(c, box(0, y0 + 6, -22.5, 10, 5, 8),      "XT30", &YELLOW);
}

static void make_esp32()
{
    Ptr<Component> c = newocc("ESP32_DevBoard");
    double y = 64.8;
    add(c, box(0, y + 0.8, 0, 51, 1.6, 26),        "ESP32_PCB_51x26", &BLACK);
    add(c, box(-16.5, y + 3.15, 0, 18, 3.1, 25.5), "ESP32_Module", &SILVER);
    add(c, box(25.0, y + 3.1, 0, 7, 3, 8),         "USB_Port", &SILVER);
    add(c, box(0, y + 2.85, 11.5, 38, 2.5, 2.5),   "Header_A", &BLACK);
    add(c, box(0, y + 2.85, -11.5, 38, 2.5, 2.5),  "Header_B", &BLACK);
}

static void make_mpu()
{
    Ptr<Component> c = newocc("MPU6050");
    double y = 43.2, cx = 15, cz = 10.5;
    add(c, box(cx, y + 0.8, cz, 20, 1.6, 15),        "MPU_PCB_20x15", &BLUE);
    add(c, box(cx, y + 2.1, cz, 4, 1, 4),            "MPU_Chip", &BLACK);
    add(c, box(cx, y + 2.85, cz + 6, 16, 2.5, 2.5),  "MPU_Header", &BLACK);
}

static void make_drv()
{
    Ptr<Component> c = newocc("DRV8833");
    double y = 43.2, cx = 0, cz = -10.5;
    add(c, box(cx, y + 0.8, cz, 20, 1.6, 15),        "DRV_PCB_20x15", &RED);
    add(c, box(cx, y + 2.35, cz, 6, 1.5, 4),         "DRV_Chip", &BLACK);
    add(c, box(cx, y + 2.85, cz - 6, 16, 2.5, 2.5),  "DRV_Header", &BLACK);
}

static void make_buck()
{
    Ptr<Component> c = newocc("DCDC_Buck");
    double y = 43.2, cx = -18, cz = 10.5;
    add(c, box(cx, y + 0.8, cz, 26.4, 1.6, 15),       "Buck_PCB_26.4x15", &RED);
    add(c, box(cx - 4, y + 4.5, cz, 10, 5.8, 10),     "Buck_Inductor", &SILVER);
    add(c, box(cx + 8, y + 3.6, cz, 6, 4, 8),         "Buck_Capacitor", &BLACK);
}

static void make_oled()
{
    Ptr<Component> c = newocc("OLED_0.96in");
    add(c, box(0, 64, 15.8, 27, 28, 1.6),              "OLED_PCB_27x28", &BLACK);
    add(c, box(0, 67, 16.9, 24, 13, 0.6),              "OLED_Glass", &GLASS);
    add(c, box(0, 67, 17.275, 21.74, 10.86, 0.15),     "OLED_ActiveArea_21.74x10.86", &ACTIVE);
    add(c, box(0, 51.6, 13.75, 10, 2.5, 2.5),          "OLED_Header", &BLACK);

    // Blue dot-matrix face (happy eyes + smile), as in the reference picture
    Ptr<Component> f = newocc("OLED_Face_Dots");
    int n = 0;
    const double ZB = 17.35, ZT = 17.6, R = 0.55;
    for (int s = -1; s <= 1; s += 2) {                // eyes: arcs, opening downward
        double ex = s * 5.6, ey = 68.0, er = 2.7;
        for (int k = 0; k < 7; ++k) {
            double a = (20.0 + 140.0 * k / 6.0) * PI_ / 180.0;
            double x = ex + er * std::cos(a), y = ey + er * std::sin(a);
            add(f, cyl(x, y, ZB, x, y, ZT, R), "Dot_" + std::to_string(++n), &DOT);
        }
    }
    for (int k = 0; k < 9; ++k) {                     // smile
        double a = (230.0 + 80.0 * k / 8.0) * PI_ / 180.0;
        double x = 4.6 * std::cos(a), y = 69.8 + 4.6 * std::sin(a);
        add(f, cyl(x, y, ZB, x, y, ZT, R), "Dot_" + std::to_string(++n), &DOT);
    }

    Ptr<Component> m = newocc("OLED_Mount");
    for (int s = 1; s >= -1; s -= 2)
        add(m, box(s * 11, 64, 14.25, 4, 4, 1.5), (s > 0) ? "OLED_Mount_R" : "OLED_Mount_L", &WHITE);
}

// ------------------------------------------------------------ run
extern "C" XI_EXPORT bool run(const char* context)
{
    app = Application::get();
    if (!app) return false;
    ui = app->userInterface();

    try {
        Ptr<Product> prod = app->activeProduct();
        design = prod;
        if (!design || design->designType() != DesignTypes::ParametricDesignType) {
            ui->messageBox("Open a NEW design with history (parametric) on, then re-run.");
            return false;
        }
        root = design->rootComponent();
        tbm = TemporaryBRepManager::get();
        YUP = (app->preferences()->generalPreferences()->defaultModelingOrientation()
               == DefaultModelingOrientations::YUpModelingOrientation);
        errors.clear(); appCache.clear();

        design->fusionUnitsManager()->distanceDisplayUnits(DistanceUnits::MillimeterDistanceUnits);

        const std::pair<const char*, const char*> params[] = {
            {"wheel_d", "34"}, {"wheel_w", "6.5"}, {"track", "70"}, {"gap_top", "20"}, {"gap_mid", "20"},
            {"gap_bat", "18"}, {"shell_t", "2.5"}, {"body_W", "80"}, {"body_D", "55"}, {"body_H", "110"}};
        for (auto& p : params)
            design->userParameters()->add(p.first, ValueInput::createByString(std::string(p.second) + " mm"), "mm", "");

        Body env;
        part("make_shell", [&] { env = make_shell(); });
        part("make_bezel", make_bezel);
        part("make_ears", make_ears);
        part("make_bow", make_bow);
        part("make_whiskers", make_whiskers);
        part("make_leds", make_leds);

        PtList s1 = {{25.5, 21}, {-25.5, 21}, {25.5, -21}, {-25.5, -21}};
        PtList s2 = {{25.5, 0}, {-25.5, 0}};
        PtList s12 = s1; s12.insert(s12.end(), s2.begin(), s2.end());

        if (env) {
            part("Platform_1", [&] { make_platform("Platform_1_Battery", 22.0, 70, 48, env, s1); });
            part("Platform_2", [&] { make_platform("Platform_2_Drivers", 41.6, 70, 46, env, s12); });
            part("Platform_3", [&] { make_platform("Platform_3_ESP32", 63.2, 56, 27, env, s2); });
        }
        part("Standoffs_L1", [&] { make_standoffs("Standoffs_L1_18mm", 23.6, 41.6, s1); });
        part("Standoffs_L2", [&] { make_standoffs("Standoffs_L2_20mm", 43.2, 63.2, s2); });
        part("Wheel_L", [&] { make_wheel("Wheel_L", -1); });
        part("Wheel_R", [&] { make_wheel("Wheel_R", 1); });
        part("Motor_L", [&] { make_motor("Motor_N20_L", -1); });
        part("Motor_R", [&] { make_motor("Motor_N20_R", 1); });
        part("battery", make_battery);
        part("buck", make_buck);
        part("drv", make_drv);
        part("mpu", make_mpu);
        part("esp32", make_esp32);
        part("oled", make_oled);

        Ptr<Viewport> vp = app->activeViewport();
        if (vp) vp->fit();

        std::string msg = std::string("Robot built (") + (YUP ? "Y-up" : "Z-up") +
            ").\nHide \"Shell_Upper_Head\" / \"Shell_Lower\" with the lightbulb to see inside.";
        if (!errors.empty()) {
            msg += "\n\nSome parts failed - send me this:";
            for (auto& e : errors) msg += "\n" + e;
        }
        ui->messageBox(msg);
    }
    catch (const std::exception& e) {
        if (ui) ui->messageBox(std::string("Failed:\n") + e.what());
        return false;
    }
    return true;
}

extern "C" XI_EXPORT bool stop(const char* context)
{
    return true;
}
