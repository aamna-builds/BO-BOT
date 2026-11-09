# Wiring

## System block diagram (from the reference sheet)

```mermaid
flowchart TD
    BAT["7.4 V LiPo (2S, 1000 mAh)"] --> BUCK["DC-DC Buck (5 V, 3 A)"]
    BAT --> MSUP["Motor supply (6 V)"]
    BUCK --> ESP["ESP32 (controller)"]
    ESP <-->|I2C| MPU["MPU-6050 (IMU)"]
    ESP <-->|I2C| OLED["OLED 1.3in"]
    ESP <--> DRV["DRV8833 (motor driver)"]
    MSUP --> DRV
    DRV --> M1["M1 (encoder)"]
    DRV --> M2["M2 (encoder)"]
    M1 -. encoder A/B .-> ESP
    M2 -. encoder A/B .-> ESP
```

## Pin map
Fill this in once the firmware pins are final. Do not guess; copy from the firmware config.

| Signal | ESP32 pin | Connects to |
|---|---|---|
| I2C SDA | | MPU-6050, OLED |
| I2C SCL | | MPU-6050, OLED |
| Motor A IN1 / IN2 | | DRV8833 |
| Motor B IN1 / IN2 | | DRV8833 |
| Encoder A (A / B) | | M1 encoder |
| Encoder B (A / B) | | M2 encoder |
| Battery voltage sense | | divider (optional) |

## Notes
- Add photos or Fritzing / KiCad exports of the wiring here.
- Check polarity on the XT30 battery connector before powering on.
