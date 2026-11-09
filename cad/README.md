# CAD

| Path | Contents |
|---|---|
| `fusion360/python/CatRobot.py` | Fusion 360 script that builds the whole robot (recommended) |
| `fusion360/cpp/` | C++ add-in version (untested; Autodesk has deprecated the C++ API) |
| `exports/` | Exported `.f3d`, `.step`, `.stl` files for submission and printing |

## Run
1. Fusion 360, new parametric design (history on).
2. Shift+S, Scripts, + , Create Script (Python), paste `CatRobot.py`, Run.
3. Hide `Shell_Upper_Head` / `Shell_Lower` with the lightbulb to see inside.
4. File, Export, save into `exports/`.
