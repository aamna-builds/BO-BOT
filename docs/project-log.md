# Project log and to-do

## Log
| Date | What was done |
|---|---|
| 2026-11-09 | Repository created. Fusion 360 CAD scripts (Python + C++) added. |
| 2026-11-09 | Cover page redesigned. Concept sketches and design sheets added. Rough web simulator added with offline support, video recording and a demo video. |
| 2026-11-09 | Parts list finalised and added to `components/`. CAD updated for the 1.3" OLED (face window, bezel, display module; buck converter moved 2 mm). |
| 2026-11-09 | ESP32 firmware written (balance controller and OLED face ported from the simulator, hardware layer, serial tuning), pin map filled in, tests and CI added. Not yet run on hardware. |
| 2026-11-09 | Simulator animation improved: rounded cat shell, pointed ears and bow tie that swing with the motion, tyre tread, contact shadow, paw for pushes, dizzy stars after a fall, smoother camera. Demo video and GIF re-rendered. Physics and controller unchanged. |

## To-do
- [ ] Run CAD script in Fusion 360 and export `.f3d` / `.step` to `cad/exports/`
- [ ] Add exported renders to `media/images/`
- [x] Firmware: IMU reading + complementary filter (written)
- [x] Firmware: balance controller + motor/encoder drivers (written)
- [x] Firmware: OLED face animations (written)
- [ ] Firmware: first build with the ESP32 toolchain, then bring-up and tuning on the robot (see `firmware/README.md`)
- [ ] Simulation / Simulink model of the inverted pendulum
- [x] Fill in wiring pin map
- [ ] Wire the robot to match `wiring/README.md` (encoders on 3V3)
- [ ] Measure the real 1.3" OLED with calipers and confirm the CAD face window and clearances
- [ ] Build thermocol casing and record assembly video
