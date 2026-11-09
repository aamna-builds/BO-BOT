# Assembly and first-test guide

Build order for the robot, with a test after each stage. The layout follows the CAD model in [`../cad/`](../cad/)
(three decks joined by standoffs). Dimensions below come from the CAD and the simulator and should be checked against the real parts.

## Layers (bottom to top)

| Layer | Height in CAD | What goes on it |
|---|---|---|
| Wheels and motors | axle level | Two N20 motors held by the motor clamps, 34 mm wheels |
| Deck 1 | 6.5 mm | Battery (68 x 37 x 12 mm) and the XT30 leads |
| Deck 2 | 24.5 mm | ESP32, MPU-6050, DRV8833, buck converter |
| Deck 3 | 52.5 mm | Breadboard and the OLED mount at the front |
| Shell | optional | Thermocol cat shell with ears and bow tie |

Standoffs: 18 mm and 20 mm between decks (spacing 20 / 20 / 18 mm), M3 screws.

## Before you start: measure and write down

| Measure | Why | Value |
|---|---|---|
| Distance between the wheel centres (track) | The simulator uses 78 mm, the CAD uses 70 mm. Set the right value in `firmware/balance_bot/include/config.h` (`WHEEL_TRACK_M`) and in the CAD | |
| OLED board size and active area | The CAD assumes 35.4 x 33.5 mm and 29.42 x 14.7 mm | |
| Total mass of the finished robot | The simulator expects about 190 g without the shell | |
| Height of the centre of mass above the axle | The simulator says about 24 mm; hang or balance the robot on a pencil to check | |

## Stage 1: mechanical frame
1. Fix the two motors in the motor clamps, wheels off. The motor shafts must be on the same axis.
2. Attach deck 1 to the clamps and fit the battery with the XT30 leads at the back.
3. Fit the 20 mm standoffs and deck 2, then the 18 mm standoffs and deck 3.
4. Press the wheels onto the shafts.

**Test:** roll the robot along a table. Both wheels turn freely and the robot tracks straight.

## Stage 2: electronics, battery disconnected
Wire to the pin map in [`../wiring/README.md`](../wiring/README.md).
1. Mount the MPU-6050 flat, on deck 2, near the middle. Its X axis points forward and its Z axis up (see `mapImu()` in `config.h` if you mount it differently).
2. Mount the DRV8833, buck converter and ESP32 on deck 2.
3. Wire I2C: SDA to GPIO 21, SCL to GPIO 22, with 3V3 and GND, to the MPU-6050 and the OLED.
4. Wire the motor driver (GPIO 25, 26, 27, 4), the encoders (GPIO 32, 33, 34, 35) and the battery divider (GPIO 36).
5. **Power the encoders from 3V3, not 5 V.**
6. Connect all grounds together.

**Test (USB only, battery unplugged):** upload the firmware, open the Serial Monitor at 115200 baud and follow the bring-up steps in
[`../firmware/README.md`](../firmware/README.md): MPU found, angle sign, encoder directions.

## Stage 3: power
1. Check the XT30 polarity with a multimeter before connecting.
2. Set the buck converter to 5.0 V **before** connecting the ESP32.
3. Do not connect the battery and USB at the same time.

**Test:** with the wheels off the ground, the display should show the face and the motors should stay still until the robot is held upright for one second.

## Stage 4: first balance
1. Put the robot on a smooth, flat floor with soft landing material around it.
2. Hold it upright until it starts, then let go.
3. Follow the tuning advice in the firmware README. Change one gain at a time and note the result in [`../docs/project-log.md`](../docs/project-log.md).

If it spins up violently, unplug the battery. The controller stops by itself beyond 40 degrees of tilt.

## Stage 5: shell
Fit the shell last. It adds mass high up and moves the centre of mass, so expect to adjust `trim` and the gains.
Weigh the robot again and update the measurements above.

## Record
Add photos of each stage to [`../media/images/`](../media/images/) and link them here.
