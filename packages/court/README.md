# @handball/court · handball-court

Single source of truth for the handball court (BRIEF 4.1).

- `spec/court.json`: hand-edited parameters (metres)
- `scripts/generate.py`: builds `generated/court_geometry.json` (polylines + calibration keypoints)
- `handball_court/` (Python) and `src/` (TypeScript) load the same generated file

Coordinate system: x = 0 at the left goal line to 40, y = 0 at the bottom sideline to 20.
All analytics are normalised so the attacked goal sits at x = 40 (`normalize_to_attack`).

Run `make court` after editing the spec. CI fails if the generated file is stale.
Shot zones (BRIEF 4.3) are added in M4 (`zones.py`, `zones.ts`) from the same spec.
