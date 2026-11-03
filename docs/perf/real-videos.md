# First real videos: findings (2026-11-03)

Three 5-minute clips from Swiss leagues (NLB men 2017 ×2, SPL2 women 2024), 1280×720 at 30 fps, registered in
`ml/eval/golden_set/manifest.json`. Files are not in git and not yet in the bucket (ADR 002); results from
`make eval-real`, table in `docs/perf/eval-real.md`.

## Result
**The analysis does not start on any of the three clips: automatic court calibration fails** (whole clip: 0/3;
single frames: 3 of 72). Everything after calibration (detection, tracking, teams, physical load, formations) is
therefore untested on real footage. With synthetic video the same code reaches the targets in `docs/perf/eval.md`.

## Why
1. **Panning camera.** All three clips come from an operator who follows play; the full court is never in view
   at once. `calibrate_frames` assumes a fixed camera (one homography from a median background over the whole
   clip) and needs the whole court boundary.
2. **Line mask too simple.** `line_mask` takes every bright, unsaturated pixel (HSV S < 60, V > 185). In these
   halls that is white walls, the light grey floor and light reflections; the court lines are a small part of
   the mask (debug images: `data/eval-real/*-lines.jpg`).
3. **Multi-sport floors.** Blue, red, green and yellow lines of other sports cross the handball lines; the
   handball lines are not always the white ones (court in the SPL2 hall has white lines on blue, others are
   coloured).
4. **Broadcast overlays and zoom** (SPL2 clip): score box, sponsor banners, changing focal length.

## Next steps (proposal)
1. **Per-frame calibration for moving cameras**: calibrate keyframes from visible line segments (partial
   court is enough, e.g. 9 m line, 6 m line, centre line), then track the homography between keyframes
   (feature matching on the floor). The fixed-camera path stays for Veo-style setups.
2. **Better line detection**: restrict to the floor region, local contrast (top-hat) instead of a global
   brightness threshold, and line colour per hall (manifest field or user click).
3. **Manual fallback that already exists**: `calibrate_points` (4 clicked points) works only for a fixed camera;
   for panning video it would be needed per keyframe.
4. **Filming guidance** (GO_LIVE, Q-DATA-1): for the first pilot clubs, ask for a fixed camera that sees the
   whole court; panning video is a later quality step.
5. **Ground truth** for at least one clip (Q-DATA-3): a few minutes of annotated positions to measure accuracy
   once calibration works.
