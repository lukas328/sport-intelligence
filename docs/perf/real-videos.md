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

## 2026-11-03, marking the court on the panorama (built)
Every analysis now stores a hall image (panorama or median frame) and, if the court is not found, ends with
"mark the court" instead of an error. The web dialog lets the user pick court landmarks and click them on the
hall image; the worker re-runs with the points on the panorama and reuses the stored camera motion.

Checked by hand on the Stäfa clip: the four goal-post feet clicked once on the panorama land exactly on the
goal posts in frames 4 minutes and 80 degrees of pan apart, so camera motion and panorama coordinates are
accurate on real footage. The goal posts alone, however, do not fix the court's width (two 3 m segments
40 m apart): a few pixels of clicking error stretch the court. The dialog therefore warns until the points
span at least 20 m of length and 10 m of width (corners, centre line ends). A fully checked analysis of a real
clip still needs those points from someone who knows which lines in the hall are the handball court.

## 2026-11-04, learned detector and top-view calibration (ADR 025)
Pretrained Apache-2.0 weights are reachable now (GitHub releases). With YOLOX-S (COCO) and the new
automatic calibration all three clips run end to end without any click:

| Clip | Camera | Calibration (automatic) | People on court / frame | Teams (tracks > 30 s) | Possession phases |
|---|---|---|---|---|---|
| Horgen - Stäfa (NLB 2017) | balcony, 6.0 m high, 5.6 m behind the near sideline | goal fit 0.76, both goal frames on the real goals | 14 | 35 / 28, referees 12, keepers by position | 11 in 5 min |
| Horgen - Möhlin (NLB 2017) | 4.2 m high, 5.9 m behind the sideline, low and flat | goal fit 0.56, one goal about 1 m off | 14 | 27 / 30, referees 12 | 8 |
| Leimental - Arbon (SPL2 2024, broadcast) | 5.5 m high above the near sideline | goal fit 0.63 | 13 | 30 / 24 | 10 |

How it works (details in ADR 025): floor orientation from the hall's markings over many frames, scale
from person heights, a top view drawn from the aligned markings only, court template search with
the players (on the court, nobody behind the goal lines, goalkeepers in the goal mouths), refined on
the striped goal frames. Check images: the court and both 3D goal frames drawn on the panorama
(`data/views/*-court.jpg`, local only).

What was fixed on the way:
- **Floor from a single panorama is wrong** (walls, banners and the railing give many segments):
  segments from 100 frames with the top 30 % and the people masked give a clean fit (tilt 17.8
  instead of 8 degrees on Stäfa).
- **Pixel masks in the top view** are dominated by white walls and reflections smeared along rays;
  drawing only segments along the two hall directions gives a clean map.
- **Goal search on red paint** locked onto red wall frames and window mullions; the score now asks
  for alternation along posts and crossbar (stripes), and a small move penalty keeps the court near
  the top-view result.
- **Team colours**: video washes colours out (yellow looks beige, white grey); kits are compared by
  hue, and the final labels come from clustering this match's colours and matching the two team
  clusters by order (lighter to lighter, hue to hue).
- **Goalkeepers by position** (most of the time within 6.5 m of a goal) and by which team defends
  that goal in set attacks; kit colours for goalkeepers are often missing or wrong.
- **Panning camera**: tracks of players outside the view wait instead of ageing.

Still open:
- **Goals** are not found automatically on these clips: after a goal the panning camera rarely shows
  the whole throw-off formation. Goals come from courtside marks, the paper report or tagging.
- **Ball and shots** need a handball-trained detector (COCO finds no handball).
- **Track identities** fragment (110 to 200 tracks per 5 minutes for about 16 people on court);
  team-level analysis (formations, possession, heatmaps) works, per-player numbers need shirt numbers
  or the manual assignment.
- **Speed on CPU** (4 cores): about 2x real time (detection on every 3rd frame dominates); a GPU
  worker brings this well under real time.

## Next steps
1. ~~Use the dialog on the real clips~~ (automatic now; the dialog stays as fallback).
2. ~~Top-down search with the known focal length~~ (done, ADR 025):: all line sets of a hall run parallel to its walls, so the
   two floor vanishing points give the floor orientation; with the focal length from the camera motion the
   panorama floor can be rectified to a top view, where the handball court is a 40 x 20 m template that only
   needs position and scale (no need to see all four boundary lines).
3. **Goal detection as calibration anchors**: the red/white goal frames are the most distinctive objects in a
   multi-sport hall; their posts give four court points (0/8.5, 0/11.5, 40/8.5, 40/11.5).
4. **Learned court keypoint model** (BRIEF 7.2, ADR 012) once annotated real frames exist (Q-DATA-3).
5. **Speed for moving cameras**: about 1.3 × video length on CPU (fixed: 0.34 ×); motion pass on every second
   frame and cheaper per-frame view rendering are the obvious levers.
6. **Ground truth** for at least one real clip (Q-DATA-3) to measure accuracy once calibration works.
