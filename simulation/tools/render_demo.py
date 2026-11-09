"""Render a deterministic demo video of the simulation (headless Chrome, frame by frame).

Usage: python render_demo.py <path/to/index.html> <out.mp4> <scratch_frames_dir> [seconds]
Requires: playwright (pip install playwright), Google Chrome, ffmpeg.
Edit EVENTS below to change the scripted run.
"""
import os, sys, subprocess, shutil
from playwright.sync_api import sync_playwright

HTML = sys.argv[1]            # path to simulation/web/index.html
OUT = sys.argv[2]             # output mp4
FRAMES_DIR = sys.argv[3]      # scratch dir for frames
SECONDS = float(sys.argv[4]) if len(sys.argv) > 4 else 26.0
FPS = 30

# (start_s, js to run)
EVENTS = [
    (0.0,  "document.getElementById('shellBtn').click()"),
    (3.0,  "__bb.hold.up = true"),
    (7.0,  "__bb.hold.up = false; __bb.hold.left = true"),
    (10.0, "__bb.hold.left = false"),
    (12.0, "__bb.doPush(1, false)"),
    (15.0, "__bb.doPush(-1, true)"),
    (17.0, "document.getElementById('xrayBtn').click()"),
    (18.0, "__bb.hold.down = true"),
    (21.0, "__bb.hold.down = false"),
    (23.0, "document.getElementById('xrayBtn').click()"),
]

shutil.rmtree(FRAMES_DIR, ignore_errors=True)
os.makedirs(FRAMES_DIR)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
                          args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                "--ignore-gpu-blocklist", "--enable-webgl"])
    pg = b.new_page(viewport={"width": 1280, "height": 720}, color_scheme="light")
    msgs = []
    pg.on("console", lambda m: msgs.append(m.text))
    pg.on("pageerror", lambda e: msgs.append("PAGEERROR " + str(e)))
    pg.goto("file://" + os.path.abspath(HTML) + "?manual=1")
    pg.wait_for_function("window.__bb !== undefined", timeout=20000)
    pg.wait_for_timeout(500)
    n = int(SECONDS * FPS)
    ev = list(EVENTS)
    for i in range(n):
        t = i / FPS
        while ev and ev[0][0] <= t:
            pg.evaluate(ev.pop(0)[1])
        pg.evaluate("__bb.step(1/30)")
        pg.screenshot(path=os.path.join(FRAMES_DIR, "f%05d.jpg" % i), type="jpeg", quality=88)
        if i % 60 == 0:
            print("frame", i, "/", n, flush=True)
    print("console:", msgs[:5])
    b.close()

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i",
                os.path.join(FRAMES_DIR, "f%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "24", "-preset", "medium", "-movflags", "+faststart", OUT], check=True)
print("wrote", OUT, os.path.getsize(OUT))
