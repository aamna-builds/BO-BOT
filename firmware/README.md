# Firmware (ESP32)

Planned contents:
- IMU driver (MPU-6050) and angle estimate (complementary / Kalman filter)
- Balance controller (PID or LQR) and motor + encoder control
- OLED face animations (fixed eyes, animated mouth)
- Pin configuration in one header, matching [`../wiring/`](../wiring/)

Suggested layout: one PlatformIO or Arduino project per folder, for example `balance_bot/`.
