"""Regenerate the reference data the host tests compare against, straight from the web simulator.

    python firmware/test/gen_golden.py            (needs: pip install playwright && python -m playwright install chromium)

Writes firmware/test/golden/controller_trace.txt  (sensor inputs and the simulator controller's outputs, 200 Hz)
       firmware/test/golden/face_frames.txt       (face images drawn by the simulator)
Only needed when the simulator's controller or face changes.
"""
import os
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
HTML = ROOT / "simulation" / "web" / "index.html"
OUT = pathlib.Path(__file__).resolve().parent / "golden"
OUT.mkdir(exist_ok=True)

TRACE_JS = """
() => {
  const c = __bb.sim.ctrl, orig = c.update.bind(c);
  window.__trace = [];
  c.update = (raw, cL, cR, adc, vIn, yIn) => {
    const out = orig(raw, cL, cR, adc * (window.__adcMul ?? 1), vIn, yIn);
    window.__trace.push([...raw, cL, cR, adc * (window.__adcMul ?? 1) * c.adcScale, vIn, yIn, out[0], out[1], out[2] ? 1 : 0,
                         c.angle, c.v, c.target, c.fallen ? 1 : 0, c.low_batt ? 1 : 0]);
    return out;
  };
  return c.goff;
}
"""

SCENARIO = [  # (seconds to run, javascript to run first)
    (2.0, "__bb.sim.v_cmd = 0; __bb.sim.yaw_cmd = 0"),
    (3.0, "__bb.doPush(1, false)"),
    (3.0, "__bb.sim.v_cmd = 0.2"),
    (2.5, "__bb.sim.yaw_cmd = 60"),
    (2.0, "__bb.sim.v_cmd = 0; __bb.sim.yaw_cmd = 0"),
    (3.0, "__bb.doPush(-1, true)"),
    (2.0, "__bb.sim.v_cmd = -0.2"),
    (2.0, "__bb.sim.v_cmd = 0"),
    (8.0, "__bb.sim.plant.soc = 0.0; window.__adcMul = 0.9"),  # battery sags below the cut-off, then the robot falls
]

FACE_JS = """
() => {
  const moods = ["idle", "happy", "careful", "worried", "surprised", "dizzy", "sleepy"];
  const combos = [[0, 0, 1], [0.6, -0.4, 1], [-1, 1, 0.5], [0, 0, 0.1]];
  const rows = [];
  for (const m of moods) for (const [look, lookv, blink] of combos) {
    const f = new BB.Face(); f.look = look; f.lookv = lookv;
    const img = f.draw(m, blink); let hex = "";
    for (let i = 0; i < img.length; i += 4) hex += (img[i] * 8 + img[i + 1] * 4 + img[i + 2] * 2 + img[i + 3]).toString(16);
    rows.push([m, look, lookv, blink, hex].join(" "));
  }
  return rows;
}
"""

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                "--ignore-gpu-blocklist"])
    pg = b.new_page()
    pg.goto("file://" + os.path.abspath(HTML) + "?manual=1")
    pg.wait_for_function("window.__bb !== undefined", timeout=30000)
    goff = pg.evaluate(TRACE_JS)
    for seconds, js in SCENARIO:
        pg.evaluate(js)
        pg.evaluate("s => __bb.sim.advance(s)", seconds)
    trace = pg.evaluate("window.__trace")
    faces = pg.evaluate(FACE_JS)
    b.close()

with open(OUT / "controller_trace.txt", "w") as f:
    f.write("# goff_gx goff_gy goff_gz, then one line per control step:\n")
    f.write("# ax ay az gx gy gz cL cR vbat v_in yaw_in | pwmL pwmR enabled angle v target fallen low_batt\n")
    f.write("GOFF " + " ".join("%.9g" % g for g in goff) + "\n")
    for r in trace:
        f.write("T " + " ".join(("%d" % v) if i < 8 or i in (11, 12, 16, 17) else ("%.9g" % v) for i, v in enumerate(r)) + "\n")
with open(OUT / "face_frames.txt", "w") as f:
    f.write("# mood look lookv blink hex(128x64 bits, row-major)\n")
    f.write("\n".join(faces) + "\n")
print("controller steps:", len(trace), " face frames:", len(faces))
