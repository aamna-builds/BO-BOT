# Components / Bill of Materials

## Purchased parts

| # | Item | Qty | Use | Size |
|---|---|---|---|---|
| 1 | GA12-N20 6 V 300 RPM micro DC reducer motor with encoder | 2 | Drive wheels and speed feedback | 10 x 12 mm |
| 2 | White wheel tyre for N20 motor | 2 | Wheels | 34 mm dia |
| 3 | 1.3" I2C 4-pin OLED, blue (SH1106) | 1 | Robot face | 35.4 x 33.5 mm board |
| 4 | Compact balance charger, 2S-3S (IMAX B3 AC Pro) | 1 | Charging the LiPo | |
| 5 | DRV8833 two-way motor driver module | 1 | Drives both motors | 20 x 15 mm |
| 6 | MPU-6050 gyro + accelerometer breakout | 1 | Tilt sensing | 20 x 15 mm |
| 7 | DC-DC buck module, 6-24 V to 5 V, 3 A | 1 | 5 V supply for the ESP32 | 26.4 x 15 mm |
| 8 | XT30 connector, male + female | 1 set | Battery connector / on-off | |
| 9 | 7.4 V 2S 1000 mAh 35C/70C LiPo battery | 1 | Main power | 68 x 37 x 12 mm |
| 10 | Jumper wires | 1 set | Signal wiring | |

**Already available:** ESP32 DevKit (51 x 26 mm), USB cable, other small parts.

**Total cost (all of the above, taxes and shipping included): Rs 4,058.78**

> **Display size:** the CAD model uses the **1.3" SH1106** (board about 35.4 x 33.5 mm, active area 29.42 x 14.7 mm,
> taken from seller listings). The older design sheets in `docs/images/` still show a 0.96" display. Measure the real
> board with calipers when it arrives and update the CAD if it differs.

## Build materials (not in the purchase list above)

| Item | Qty | Notes |
|---|---|---|
| Standoffs (gold) | 4 + 2 | 18 mm and 20 mm, between platforms |
| Platforms | 3 | Spacing 20 / 20 / 18 mm |
| Thermocol sheet | | 5-8 mm, casing walls |

## Datasheets
Put PDFs in [`datasheets/`](datasheets/).
