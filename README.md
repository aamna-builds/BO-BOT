<div align="center">

<img src="docs/images/banner.svg" alt="BO-BOT: Self-Balancing Cat Robot" width="100%">

<br>

**A two-wheeled, self-balancing robot with a cat-shaped casing and an animated OLED face.**<br>
Mechanical design, electronics, firmware, simulation and documentation, all in one place.

<br>

[![CI](https://github.com/aamna-builds/BO-BOT/actions/workflows/ci.yml/badge.svg)](https://github.com/aamna-builds/BO-BOT/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-in%20development-orange)
![Controller](https://img.shields.io/badge/controller-ESP32-blue)
![CAD](https://img.shields.io/badge/CAD-Fusion%20360-0696D7)
![Languages](https://img.shields.io/badge/code-C%2B%2B%20%7C%20Python%20%7C%20MATLAB-informational)

[About](#about) ·
[Design](#design) ·
[Specifications](#specifications) ·
[Simulation](#simulation) ·
[Architecture](#system-architecture) ·
[Repository](#repository-structure) ·
[Roadmap](#roadmap)

</div>

---

## About

BO-BOT is an **inverted-pendulum robot**: it stands upright on two wheels and keeps its balance by continuously
measuring its tilt and driving the wheels to correct it. The body is a compact cat-shaped casing, first built as a
low-cost **thermocol prototype**, with a small OLED screen that shows a fixed pair of eyes and an animated mouth
(happy, talking, surprised, sad).

The project covers the full engineering workflow:

- **Mechanical:** parametric CAD, layered chassis, casing design and build
- **Electronics:** power distribution, motor driving, sensing and wiring
- **Control:** balance controller, tuned with simulation before running on hardware
- **Software:** ESP32 firmware, OLED face animation
- **Documentation:** bill of materials, wiring, build photos and videos

## Design

The design is a three-platform chassis inside an egg-shaped cat shell. The battery sits low to keep the centre of mass
close to the axle, drivers and sensors sit on the middle platform, and the ESP32 and OLED face sit at the top.

**Concept sketches:** early ideas for the outer layer, internal structure, LED face expressions and alternative looks.

<p align="center">
  <img src="docs/images/concept-sketch.png" alt="BO-BOT concept sketches" width="95%">
</p>

**Design sheet (3D-printed shell version):** dimensions, internal layout, components and system block diagram.

<p align="center">
  <img src="docs/images/design-sheet-3d-print.png" alt="BO-BOT design sheet, 3D-printed shell" width="95%">
</p>

The earlier [thermocol casing version](docs/images/design-sheet-thermocol.png) is kept for reference.

> The sheets above were drawn for a 0.96" display. The build uses a **1.3" SH1106 OLED**, and the CAD model
> (`cad/`) has been updated for it.

## Simulation

A browser-based 3D simulator lets you drive the robot, push it, tune the controller gains live and record video.
Open [`simulation/web/index.html`](simulation/web/index.html) in Chrome or Edge, no install needed.
Details are in [`simulation/README.md`](simulation/README.md).

<p align="center">
  <img src="media/videos/simulation-demo.gif" alt="Simulation demo" width="60%"><br>
  <sub>Scripted demo: balancing, driving, turning and recovering from pushes.
  <a href="media/videos/simulation-demo.mp4">Full video (MP4)</a></sub>
</p>

## Specifications

| | |
|---|---|
| **Size (H x W x D)** | about 110 x 80 x 55 mm |
| **Wheels** | 34 mm diameter, 6.5 mm wide, 70 mm track |
| **Platform spacing** | 20 / 20 / 18 mm |
| **Controller** | ESP32 development board |
| **Motion sensing** | MPU-6050 (accelerometer + gyroscope, I2C) |
| **Actuation** | 2 x N20 geared motors with encoders, driven by a DRV8833 |
| **Display** | 1.3" OLED, SH1106 (I2C), fixed eyes with an animated mouth |
| **Power** | 2S 1000 mAh LiPo (7.4 V) with a 5 V / 3 A buck converter |
| **Casing** | Thermocol (5-8 mm) prototype |

## System architecture

```mermaid
flowchart TD
    BAT["7.4 V LiPo (2S, 1000 mAh)"] --> BUCK["DC-DC Buck (5 V, 3 A)"]
    BAT --> MSUP["Motor supply (6 V)"]
    BUCK --> ESP["ESP32 (controller)"]
    ESP <-->|I2C| MPU["MPU-6050 (IMU)"]
    ESP <-->|I2C| OLED["OLED 1.3in"]
    ESP <--> DRV["DRV8833 (motor driver)"]
    MSUP --> DRV
    DRV --> M1["Motor 1 + encoder"]
    DRV --> M2["Motor 2 + encoder"]
```

**Control idea:** the MPU-6050 gives the tilt angle, a filter combines the accelerometer and gyroscope, and the
controller turns the angle error into motor commands many times per second. Encoders on both motors provide speed
feedback.

## Repository structure

```
BO-BOT/
├── cad/            Fusion 360 scripts and exported CAD files
├── firmware/       ESP32 code
├── simulation/     Simulations and tuning results
├── simulink/       MATLAB / Simulink model, equations, graphs
├── hardware/       Mechanical build notes (casing, assembly)
├── electronics/    Power design, schematics, layouts
├── wiring/         Wiring diagrams and pin map
├── components/     Bill of materials and datasheets
├── media/          Photos and videos
└── docs/           Reports, project log, images
```

Each folder has its own README describing what belongs there.

## Roadmap

| Area | Task | Status |
|---|---|---|
| CAD | Parametric Fusion 360 model of the robot | Done |
| CAD | Export `.f3d` / `.step` and renders | In progress |
| CAD | Alternative body and layout designs | Planned |
| Simulation | Rough web simulator with live gain tuning and video recording | Prototype done |
| Maths | Linear model, stability analysis and graphs ([equations](docs/equations.md), [`simulink/`](simulink/)) | Done in Python; MATLAB and Simulink files written, not yet run |
| Simulation | Controller tuning and validation against hardware | Planned |
| Electronics | Final component selection and wiring pin map | Pin map done |
| Firmware | IMU filter, balance controller, motor and encoder drivers | Written, not yet run on hardware |
| Firmware | OLED face animations | Written, not yet run on hardware |
| Hardware | Thermocol casing build | Planned |
| Media | Build photos and demo video | Planned |

Detailed progress is tracked in [`docs/project-log.md`](docs/project-log.md).

## Components

The full parts list with sizes and sources is in [`components/`](components/).

## Gallery

Build photos, renders and demo videos will appear here as the project progresses. See [`media/`](media/).
