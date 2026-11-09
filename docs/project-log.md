# Project log and to-do

## Log
| Date | What was done |
|---|---|
| 2026-11-09 | Repository created. Fusion 360 CAD scripts (Python + C++) added. |
| 2026-11-09 | Cover page redesigned. Concept sketches and design sheets added. Rough web simulator added with offline support, video recording and a demo video. |
| 2026-11-09 | Parts list finalised and added to `components/`. CAD updated for the 1.3" OLED (face window, bezel, display module; buck converter moved 2 mm). |

## To-do
- [ ] Run CAD script in Fusion 360 and export `.f3d` / `.step` to `cad/exports/`
- [ ] Add exported renders to `media/images/`
- [ ] Firmware: IMU reading + complementary filter
- [ ] Firmware: balance controller + motor/encoder drivers
- [ ] Firmware: OLED face animations (happy, talking, surprised, sad)
- [ ] Simulation / Simulink model of the inverted pendulum
- [ ] Fill in wiring pin map
- [ ] Measure the real 1.3" OLED with calipers and confirm the CAD face window and clearances
- [ ] Build thermocol casing and record assembly video
