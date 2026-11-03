# First real videos: findings

Three 5-minute clips from Swiss leagues (NLB men 2017 ×2, SPL2 women 2024), 1280×720 at 30 fps, registered in
`ml/eval/golden_set/manifest.json`. Files are not in git and not yet in the bucket (ADR 002); current results
from `make eval-real` in `docs/perf/eval-real.md`.

## 2026-11-03, first run: nothing worked
Automatic court calibration failed on all three clips (whole clip 0/3, single frames 3 of 72), so the analysis
never started. Reasons:

1. **Panning camera.** All three clips come from an operator who follows play (80 to 86 degrees of pan,
   slight zoom); the full court is never in view at once. The pipeline assumed a fixed camera.
2. **Line mask too simple.** It took every bright, unsaturated pixel: white walls, the light grey floor and
   light reflections.
3. **Multi-sport floors.** Several line sets in several colours; the handball lines are not the white ones in
   every hall.
4. **Broadcast overlays and zoom** (SPL2 clip): score box, sponsor banners, changing focal length.

## 2026-11-03, after ADR 020 (moving cameras)
- **Camera motion: solved on all three clips.** Pan 82 to 86 degrees, zoom ratio 1.05 to 1.12, 100 % of
  frames placed on the panorama, focal length estimated (about 1200 px for the club cameras, 920 px for the
  broadcast). The hall panoramas are clean (players removed by the median); debug images in `data/eval-real/`.
  On synthetic panning footage with ground truth: rotation error about 0.2 degrees, focal length within 1 %,
  tracking on par with fixed cameras (`docs/perf/eval.md`).
- **Calibration: not solved on the real halls.** With a higher-resolution panorama the automatic calibration
  reports success on one or two clips, but the court overlays (`data/eval-real/*-court.jpg`) show the court
  several metres off (Möhlin: a court a third of the real size in the middle of the hall; Stäfa: goal area
  beside the real goal). A physical check with the known focal length (equal, orthogonal court axes, camera
  2 to 30 m above the floor) now rejects the Möhlin result; the Stäfa result passes all checks and is still
  wrong. Automatic calibration of real halls therefore has to be confirmed by the user until it is reliable.
  The underlying reasons: on the panoramas the court is a flat strip far from the camera; the handball
  lines are faint or coloured among badminton, volleyball and basketball lines; the near sideline is hidden
  by the balcony railing and spectators (club clips) or out of the picture (broadcast). The line masks find
  many lines, and a court hypothesis built from the wrong lines can still explain a fair share of them.

## Next steps
1. **Click calibration on the panorama** (product): the user marks 4 or more court points once per video on
   the hall panorama; motion carries them to every frame. The pipeline already supports it
   (`analyse_video(calibration=..., calibration_frame=...)`, manifest field `calibration` for
   `make eval-real`); missing is the UI and storing the frame index with the points.
2. **Top-down search with the known focal length**: all line sets of a hall run parallel to its walls, so the
   two floor vanishing points give the floor orientation; with the focal length from the camera motion the
   panorama floor can be rectified to a top view, where the handball court is a 40 x 20 m template that only
   needs position and scale (no need to see all four boundary lines).
3. **Goal detection as calibration anchors**: the red/white goal frames are the most distinctive objects in a
   multi-sport hall; their posts give four court points (0/8.5, 0/11.5, 40/8.5, 40/11.5).
4. **Learned court keypoint model** (BRIEF 7.2, ADR 012) once annotated real frames exist (Q-DATA-3).
5. **Speed for moving cameras**: about 1.3 × video length on CPU (fixed: 0.34 ×); motion pass on every second
   frame and cheaper per-frame view rendering are the obvious levers.
6. **Ground truth** for at least one real clip (Q-DATA-3) to measure accuracy once calibration works.
