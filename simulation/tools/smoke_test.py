"""Smoke test for the web simulator (run by CI).

Loads the page in headless Chromium, then checks that
  1. the page loads without JavaScript errors,
  2. the robot balances on its own for 10 s,
  3. it survives a push and keeps balancing,
  4. it follows a drive command without falling.
Usage: python simulation/tools/smoke_test.py simulation/web/index.html
Requires: pip install playwright && python -m playwright install chromium
"""
import os
import sys
from playwright.sync_api import sync_playwright

html = sys.argv[1] if len(sys.argv) > 1 else "simulation/web/index.html"
problems = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        problems.append(msg)


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                "--ignore-gpu-blocklist", "--enable-webgl"])
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    js_errors = []
    pg.on("pageerror", lambda e: js_errors.append(str(e)))
    # Failed network loads (e.g. the optional web fonts) are not code errors, so they are ignored.
    pg.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and js_errors.append(m.text))
    pg.goto("file://" + os.path.abspath(html) + "?manual=1")
    pg.wait_for_function("window.__bb !== undefined", timeout=30000)
    pg.evaluate("__bb.step(1/60)")  # one full frame: physics + 3D render + panel
    check(not js_errors, "page loads and renders without JavaScript errors" + (f" ({js_errors[:2]})" if js_errors else ""))

    def run(seconds, dt=1 / 200):  # physics only, same 200 Hz as the firmware log
        pg.evaluate("([s, dt]) => { const sim = __bb.sim; for (let i = 0; i < s / dt; i++) sim.advance(dt); }", [seconds, dt])

    state = lambda: pg.evaluate("({fallen: __bb.sim.fallen, angle: __bb.sim.ctrl.angle})")

    run(10)
    s = state()
    check(not s["fallen"], "balances unaided for 10 s")
    check(abs(s["angle"]) < 3, f"pitch stays within 3 degrees at rest (now {s['angle']:.2f})")

    pg.evaluate("__bb.doPush(1, false)")
    run(5)
    s = state()
    check(not s["fallen"], "survives a forward push")
    check(abs(s["angle"]) < 3, f"recovers upright after the push (pitch {s['angle']:.2f})")

    pg.evaluate("__bb.sim.v_cmd = 0.2")
    run(3)
    pg.evaluate("__bb.sim.v_cmd = 0")
    run(4)
    check(not pg.evaluate("__bb.sim.fallen"), "drives forward and stops without falling")

    pg.evaluate("__bb.step(1/60)")
    check(not js_errors, "no JavaScript errors after the run")
    b.close()

sys.exit(1 if problems else 0)
