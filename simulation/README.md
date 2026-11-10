# Simulation

## Web simulator (rough prototype)

A browser-based 3D test bench for the balancing robot: full equations of motion, motor and gearbox model, MPU-6050 and
encoder sensor models, firmware-style controller with live-tunable gains, OLED face, and live charts.

### Run it
No install needed. Everything it needs is included (three.js is bundled in `web/vendor/`), so it also works offline.

- **Simplest:** open `web/index.html` in Chrome or Edge.
- **Or serve it locally:** from this folder run `python -m http.server 8000`, then open
  `http://localhost:8000/web/`.

### Controls
| Input | Action |
|---|---|
| Arrow keys / on-screen pad | Drive and turn (`Shift` = faster) |
| `X` / `Z` | Push forward / backward |
| `R` | Pick up and release |
| `S` / `O` | Toggle shell / X-ray |
| `P` | Pause |
| `C` | Change camera |
| `1`-`4` | Simulation speed |

The right-hand panel shows live traces and lets you change the controller gains (`kp`, `kd`, `kp_v`, ...), battery level,
gear backlash, IMU position and extra weight while it runs.

### Run it online (GitHub Pages)
A workflow (`.github/workflows/pages.yml`) publishes the simulator from `simulation/web/` whenever it changes.
Switch it on once: on GitHub open **Settings, Pages**, and under **Build and deployment** set **Source** to **GitHub Actions**.
The page then appears at `https://aamna-builds.github.io/Bo-Bot/`.

### Record a video
Click **Record** (top right of the 3D view), use the simulator, then click **Stop & save**. The browser downloads a
`.webm` video of the 3D view. Works in Chrome and Edge.

### Demo video
`../media/videos/simulation-demo.mp4` shows a scripted run: balancing, driving, turning, pushes, X-ray view, and a fall.
To regenerate it:

```
pip install playwright
python simulation/tools/render_demo.py simulation/web/index.html media/videos/simulation-demo.mp4 /tmp/frames 30
```

(`ffmpeg` and Chrome are required. The script steps the simulation frame by frame, so the video is smooth and
repeatable on any machine.)

## Other simulations
Put Python or MATLAB scripts, parameter files and result plots here. Simulink models go in [`../simulink/`](../simulink/).
