# Firmware (ESP32)

`balance_bot/` is a PlatformIO project (Arduino framework) for the ESP32. The balance controller and the OLED face are
**ports of the web simulator**, using the same gains and units, so values tuned in the simulator are a good starting point on the robot.

| File | What it does |
|---|---|
| `balance_bot/include/controller.h` | Balance controller: complementary filter, speed estimate, lean-angle loop, steering, battery cut-off. No Arduino code, so it also runs on a PC |
| `balance_bot/include/face.h` | OLED face (idle, happy, careful, worried, surprised, dizzy, sleepy), drawn into a 128 x 64 image |
| `balance_bot/include/config.h` | Pins, motor and wheel constants, direction switches, IMU axis mapping |
| `balance_bot/src/main.cpp` | Hardware layer: MPU-6050, encoders, DRV8833 PWM, OLED, 200 Hz control task, serial commands |
| `test/` | PC tests that check the controller and face against the simulator (see below) |

## Build and upload
1. Install [PlatformIO](https://platformio.org/install) (VS Code extension).
2. Open the `firmware/balance_bot` folder, connect the ESP32 over USB, and press **Upload** (`pio run -t upload`).
3. Open the Serial Monitor at 115200 baud. Type `help` for the commands.

## Bring-up (do these in order, with the wheels OFF the ground)
1. **Power the ESP32 from USB only** (motor battery disconnected). The monitor should print the MPU `WHO_AM_I`, then the gyro offsets.
   If you see "MPU-6050 not found", check SDA (GPIO 21), SCL (GPIO 22) and 3V3.
2. **Angle sign:** type `tele on`. Tilt the robot forward: the `angle` column must go **positive**. If not, remap the axes in `mapImu()` in `config.h`.
3. **Encoders:** type `show`, roll the left wheel forward by hand: the left count must go **up**. Same for the right wheel. If not, flip `ENC_L_INVERT` / `ENC_R_INVERT`.
4. **Motors:** connect the battery, hold the robot upright, and let it start (angle within 3 degrees for one second). Tilt it forward
   by hand: both wheels must spin **forward** (the direction that catches a forward fall). If one spins backwards, flip `MOTOR_L_INVERT` / `MOTOR_R_INVERT`.
   If the wheel direction is right but it falls over harder, the encoder or angle sign from steps 2 and 3 is wrong.
5. **First balance:** put it on the floor with a soft landing around it. Start with the default gains, then tune.

If something spins up violently: unplug the battery. The controller stops by itself beyond 40 degrees of tilt and does not restart
until the robot is held upright for one second.

## Tuning from the Serial Monitor
`set kp 50`, `set kd 0.4`, `v 0.2`, `yaw 60`, `tele on` (CSV for plotting), `show`. The same advice as the simulator applies:

- Creeps away while standing: adjust `trim`.
- Motors buzz: lower `kd`.
- Slow sway back and forth: lower `kp_v` or `ki_v`.
- Falls when pushed: raise `kp` a little.

Gains typed here are not saved. Put the final values into `Gains` in `controller.h`.

## Tests (run on a PC, no hardware needed)
```
cd firmware/test
g++ -std=c++17 -O2 -o test_controller test_controller.cpp && ./test_controller
g++ -std=c++17 -O2 -o test_face test_face.cpp && ./test_face
```
- `test_controller` replays 27 s of sensor data recorded from the simulator (pushes, driving, turning, a flat battery, a fall) through
  `controller.h` and checks that the PWM outputs match the simulator's controller (within 2 counts).
- `test_face` checks that every face pixel matches the simulator's drawing.
- If you change the simulator's controller or face, regenerate the reference data with `python firmware/test/gen_golden.py`.
- GitHub runs these tests, plus a syntax check of `main.cpp` against stand-in Arduino headers, on every push.

## Status
- **Verified on a PC:** the controller and face match the simulator.
- **Not yet verified:** `main.cpp` has not been compiled with the ESP32 toolchain or run on the robot. It passes a syntax check
  against stand-in headers only. Expect small fixes at the first real build, and expect to re-tune the gains: the simulator is an approximation.
