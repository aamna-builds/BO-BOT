# Simulink and MATLAB

The maths behind the balance controller, with graphs. The full derivation is in [`docs/equations.md`](../docs/equations.md).

| File | What it is |
|---|---|
| `bobot_params.m` | All physical and controller parameters (same values as the simulator and the firmware) |
| `bobot_analysis.m` | Linear model, closed loop with the firmware gains, poles, Bode margins, gain sweeps, step and tilt responses, nonlinear check |
| `bobot_closed.m`, `bobot_nonlinear.m` | Helper functions for the analysis script |
| `build_bobot_model.m` | Builds the Simulink model `bobot_balance.slx` from code |
| `python/bobot_linear_model.py` | The same calculation in Python; produced the graphs in `results/` |
| `data/` | Traces recorded from the nonlinear web simulator, used to check the linear model |
| `results/` | Graphs (PNG) and `summary.json` with the numbers |

## Graphs

| | |
|---|---|
| ![poles](results/01_poles.png) | ![recovery](results/02_tilt_recovery_validation.png) |
| Open-loop poles: one is unstable | Linear model against the simulator, 3° tilt |
| ![speed](results/03_speed_step.png) | ![bode](results/04_angle_loop_bode.png) |
| Speed command response | Angle loop margins |
| ![gains](results/05_gain_sweeps.png) | ![nonlinear](results/07_nonlinear_recovery.png) |
| Gain sweeps | Larger tilts, nonlinear model |

## Run it

**MATLAB** (R2018b or newer, Control System Toolbox): open the `simulink` folder, then run `bobot_analysis`. Figures are saved in `results_matlab/`.

**Simulink:** run `build_bobot_model`, open `bobot_balance.slx` and press **Run**. Open the two scope blocks to see speed and pitch.
Change gains in `bobot_params.m` and run again.

**Python** (numpy, scipy, matplotlib): `python simulink/python/bobot_linear_model.py`

## Status
- **Checked:** the Python calculation and all the graphs. The linear model agrees with the nonlinear simulator for speed response and for the time scale of tilt recovery (see section 7 of the equations page for the differences).
- **Not checked:** the MATLAB scripts and the Simulink builder were written to give the same results as the Python version, but they have **not been run in MATLAB**. If one errors, send me the message and I will fix it. After the first successful run in MATLAB, save the generated `bobot_balance.slx` and commit it here, with a note of your MATLAB version.
