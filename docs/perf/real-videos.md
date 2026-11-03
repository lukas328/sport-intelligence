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
- **Calibration: still fails on the real halls**, now for the right reason. On the panoramas the court is a
  flat strip far from the camera; the handball lines are faint or coloured among badminton, volleyball and
  basketball lines; the near sideline is hidden by the balcony railing and spectators (club clips) or out of
  the picture (broadcast). The classic and per-colour line masks find many lines, but no court hypothesis
  explains enough of the handball model. A wrong court is rejected (match below 25 %, or less than 85 % of
  the court seen) instead of producing wrong positions.

## Next steps
1. **Click calibration on the panorama** (product): the user marks 4 or more court points once per video on
   the hall panorama; motion carries them to every frame. The pipeline already supports it
   (`analyse_video(calibration=..., calibration_frame=...)`, manifest field `calibration` for
   `make eval-real`); missing is the UI and storing the frame index with the points.
2. **Goal detection as calibration anchors**: the red/white goal frames are the most distinctive objects in a
   multi-sport hall; their posts give four court points (0/8.5, 0/11.5, 40/8.5, 40/11.5).
3. **Learned court keypoint model** (BRIEF 7.2, ADR 012) once annotated real frames exist (Q-DATA-3).
4. **Speed for moving cameras**: about 1.3 × video length on CPU (fixed: 0.34 ×); motion pass on every second
   frame and cheaper per-frame view rendering are the obvious levers.
5. **Ground truth** for at least one real clip (Q-DATA-3) to measure accuracy once calibration works.
