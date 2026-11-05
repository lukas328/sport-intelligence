# Goal and shot moments from the picture (research; goal and shot candidates are shipped, see the last sections)

How far can we find goal moments in handball video without the score overlay? The free ground truth
is the official game log: every goal has a table time. This folder holds the first goal-moment
detector that can be scored against it, plus the scripts that measure it.

## Data
- **Goal clips**: 52 official goals (50 field goals, 2 penalties) of Magdeburg II vs Rostock (3. Liga
  broadcast, 1280x720, 50 fps). Each clip covers 6 s before to 3 s after the logged time
  (`ml/eval/cut_event_clips.py`).
- **Non-goal clips**: 47 windows of 9 s from the four 3-minute segments that show play
  (`data/videos/segs/magdeburg_rostock_s{0,1,3,4}.mp4`; s2 is the half-time break). Each window is
  at least 20 s away from every logged event. They are cut with the same ffmpeg settings as the goal
  clips (`cut_negatives.py`), so neither resolution nor compression gives the class away. The
  segment start times in the full video (855, 1709, 3988 and 4843 s) come from reading the overlay
  clock and matching it to the aligned log's clock samples. They put the deleted full video at
  about 5697 s.
- **Reference times**: when the score digits of the overlay change (`overlay_ref.py`, yellow digit
  masks, used only to score the detector). The change is inside 35 of the 52 goal clips. These 35
  are the "overlay-confirmed" subset below.

### Finding: the logged time is 4 to 6 s late
The overlay changes a median of **4.7 s before** the logged time (10th to 90th percentile: 6.0 to
2.4 s before). 7 of the 35 changes come in the first 0.3 s of the clip, so the true lag is larger
still. In 16 clips the overlay does not change at all, mostly because the goal fell before the clip
started. The 9-second clips are therefore centred badly: the shot is often missing and only the
restart is in the picture. **Future clip cuts should cover -12 s to +3 s around the logged time**,
or shift the log by about -5 s first.

## Pipeline
1. `extract.py` (heavy pass, run once, cached as npz per clip). Every frame gets the camera pan
   (phase correlation on a quarter-size grey image), the correlation response and the
   pan-compensated motion energy. Every 4th frame goes through the 3-frame ball net (`ball3d.onnx`,
   t-3/t/t+3 at 50 fps, top 5 peaks), every 25th frame through YOLOX-m for people. A 320x180
   thumbnail and the overlay crop are kept at 10 Hz. Cost on the shared 4-core CPU: about 6 min per
   9-second clip with the ball net, about 10 s without it (`--no-ball --no-det`).
2. `cues.py`: one value per 0.2 s step over clip seconds 0.5 to 7.0. Each value looks 2 s back and
   2 s ahead:
   - `pan_rev`: the camera pans one way before t and the other way after t (geometric mean of the
     two opposite mean pan speeds).
   - `still_swing`: a quiet camera before t, a swing after t.
   - `pan_after`: the size of the swing after t.
   - `cut`: the phase-correlation response collapses (motion blur of a fast swing; this broadcast
     has no replays).
   - `energy_drop`: motion energy before t divided by motion energy after t.
   - `zone_leave`: the share of goal-area paint in view before t minus after t. This hall paints
     the 6 m zone green, so the cue is hall-specific.
   - `ball_fast`, `ball_fast_lost`, `ball_zone`: from the balltrack path. Top path speed before t;
     a fast segment that ends and the ball is not seen for up to 2 s; the last fast point lies in
     the goal-area paint.
   - `people_flow`: the median canvas x of the YOLOX people turns round, or everyone runs one way.
   - `template`: a matched filter. Three channels at 10 Hz (pan speed with its sign set so that the
     swing after t is positive, goal-area share, motion energy) form a profile from -2 to +3 s
     around t. The template is the mean profile of the goal clips around overlay change + 1 s, and
     the cue is the cosine similarity with it. It is leave-one-clip-out: a goal clip is never scored
     with a template it helped build.
3. `evaluate.py`: the clip score is the maximum of the cue over the grid, which is the same for both
   classes. It reports AUC on all 52 goal clips and on the 35 overlay-confirmed ones, recall at a
   10 % false-positive rate (overlay-confirmed), and the peak time against the logged time and
   against the overlay change. The combinations are a sum of z-scores (no fitting) and a logistic
   regression, leave-one-clip-out.
4. `stream_eval.py`: the template score over the four continuous 3-minute segments (11.7 min of
   play, 7 overlay goals). Peaks are taken with 8 s non-maximum suppression. A detection counts
   when it falls 1 s before to 4 s after an overlay change. The template here is built only from
   goal clips outside the segments.

## Results
AUC: all 52 goal clips / 35 overlay-confirmed clips, against 47 non-goal clips. R@10%FP is the
recall on the overlay-confirmed clips at the threshold where 10 % of non-goal clips fire. Timing
columns use the score peak in each goal clip. "peak - overlay" is the median offset from the score
change, |dev| is the median distance from that offset, and the last column is the share of clips
within 1 s of it.

| Cue | Needs | AUC all / confirmed | R@10%FP | peak - logged | peak - overlay | abs dev | within 1 s |
|---|---|---|---|---|---|---|---|
| `pan_rev` | camera pan | 0.844 / 0.897 | 0.74 | -3.5 s | +1.5 s | 0.5 s | 0.80 |
| `still_swing` | camera pan | 0.824 / 0.900 | 0.71 | -2.9 s | +1.7 s | 0.6 s | 0.60 |
| `pan_after` | camera pan | 0.830 / 0.903 | 0.60 | -1.7 s | +3.0 s | 1.1 s | 0.49 |
| `cut` | camera pan | 0.812 / 0.861 | 0.17 | -4.1 s | +1.7 s | 0.7 s | 0.60 |
| `energy_drop` | frames | 0.650 / 0.647 | 0.14 | +0.1 s | +4.5 s | 1.1 s | 0.46 |
| `zone_leave` | goal-area paint (hall) | **0.876 / 0.945** | **0.94** | -1.9 s | +2.8 s | 0.6 s | 0.66 |
| `people_flow` | YOLOX every 0.5 s | 0.828 / 0.873 | 0.57 | -2.1 s | +2.9 s | 0.8 s | 0.54 |
| `ball_fast` | ball net + path | 0.676 / 0.736 | 0.40 | -3.1 s | +1.3 s | 2.0 s | 0.26 |
| `ball_fast_lost` | ball net + path | 0.677 / 0.735 | 0.37 | -4.6 s | +0.7 s | 1.6 s | 0.31 |
| `ball_zone` | ball + paint | 0.528 / 0.578 | 0.29 | -5.5 s | -0.4 s | 0.9 s | 0.57 |
| sum z(pan_rev, still_swing, cut) | camera pan only | 0.850 / 0.921 | 0.80 | -3.3 s | +1.7 s | 0.6 s | 0.77 |
| sum z(pan_rev, still_swing, zone_leave) | pan + paint | 0.861 / 0.920 | 0.60 | -3.0 s | +2.0 s | 0.6 s | 0.80 |
| logistic regression, LOO, same three | pan + paint | 0.849 / 0.905 | 0.51 | -1.9 s | +2.6 s | 0.7 s | 0.63 |
| sum z(pan_rev, still_swing, zone_leave, ball_fast, people_flow) | all | 0.860 / 0.919 | 0.71 | -2.9 s | +2.0 s | 0.7 s | 0.69 |
| **template** (pan, paint, energy; LOO) | pan + paint | **0.869 / 0.928** | **0.91** | -3.5 s | **+1.3 s** | **0.5 s** | 0.74 |
| template (pan, energy) | camera pan only | 0.817 / 0.894 | 0.66 | -4.0 s | +0.8 s | 0.6 s | 0.71 |
| template (pan only) | camera pan only | 0.573 / 0.563 | 0.17 | -3.5 s | +1.4 s | 0.9 s | 0.54 |

The ball path covers 24 % of the sampled frames (1.7 net peaks per frame above 0.2). Adding the
ball and people cues to the combination does not raise the AUC. Template window variants (-3..+4,
-2..+2, -2..+5, -1..+4 s) give AUC 0.855 to 0.873: the result does not hinge on that choice.

Timing prior: always answering the same clip time (the median overlay change, 1.3 s) gives a median
error of 1.0 s, with 51 % of goals within 1 s. A useful cue has to beat that.

### Continuous footage (11.7 min, 7 goals, template cue)
| threshold | recall | precision | false alarms / min | detection - overlay |
|---|---|---|---|---|
| 0.60 | 0.86 | 0.27 | 1.37 | +1.0 s |
| 0.70 | 0.86 | 0.35 | 0.94 | +1.0 s |
| 0.80 | 0.71 | 0.42 | 0.60 | +1.1 s |

## What the numbers say
- **Without any ball, the camera finds goal moments well, but it does not tell goals apart from
  turnovers.** After a goal the camera leaves the goal area and swings back for the throw-off. Pan
  reversal, leaving the goal area and the template reach AUC 0.84 to 0.87 (0.90 to 0.93 on the
  overlay-confirmed clips). The template peak sits 1.3 s after the overlay change, with a median
  deviation of only 0.5 s. Every top-scoring non-goal clip is a turnover or save followed by a
  counter-attack, and the camera swing looks the same. On continuous play this costs about one false
  alarm per minute at 86 % recall, so precision is about 35 % when goals come about once a minute.
- **The ball cues add almost nothing yet** (AUC around 0.6). The balltrack path covers only about 25 %
  of the sampled frames, and it is rarely the shot itself. The ball net's 33 % top-1 rate on the
  user benchmark falls further on fast, blurred shots and on the small far goal.
- **Goal posts are not found by a heuristic.** At 720p the black/white posts are 2 to 4 px wide.
  The stripe detector (`goalfind.py`, a negative result) fires more on spectators and the mixing
  desk. The goal area's paint works in this hall but is hall-specific.
- **Energy drop does not work** (AUC 0.65): with fast throw-offs nobody stops.

## Most promising direction
1. **Use overlay score changes as labels and shift the logs.** On broadcast games the digit change is
   an exact, free label, accurate to about 1 s. The log needs about -5 s. With some hundred goals
   from several broadcasts, train a small temporal classifier (1D CNN or GRU) on the cheap
   per-frame channels instead of a hand-made template.
2. **Add goal-specific evidence on top of the transition detector, which then only proposes
   candidates.** It cuts the footage to about 2 candidate windows per minute.
   - **Ball into the goal mouth.** Goals are fixed in the hall: locate them once per game, through
     court calibration (`topview.refine_on_goals` projects the post model) or a small learned post
     detector. Then run the ball net at full resolution only on goal-mouth crops in the candidate
     windows. That is cheap, and the ball looks the same near the goal in every hall.
   - **Throw-off restart.** The ball and one player at the centre spot, the teams in their own
     halves. This needs the centre line from calibration and the people detector, and it is the
     cue that separates a goal from a save followed by a counter-attack.
   - **Audio** (not testable here: the clips were cut without sound). The referee's whistle for
     the throw-off, the crowd and the horn are strong and camera-independent goal cues.
3. **Raw amateur footage.** A fixed wide camera has no pan, but the same signal is there as the
   players' centroid: YOLOX people, projected to court coordinates when calibration is available.
   The play's centre of mass leaving one goal and running back to the centre replaces the camera
   swing, and the players' "leave the goal area" replaces the painted zone. `people_flow`, which
   already uses canvas coordinates, reaches AUC 0.83 / 0.87 here. Auto-panning cameras (Veo,
   Pixellot) behave like the broadcast camera, so the pan cues carry over directly.

## Reproduce
```bash
S=<scratchpad>; V=data/videos/segs
python ml/goals/cut_negatives.py $S/match/magdeburg_aligned.json $S/goals/neg_clips \
  --segs $V/magdeburg_rostock_s0.mp4,$V/magdeburg_rostock_s1.mp4,$V/magdeburg_rostock_s3.mp4,$V/magdeburg_rostock_s4.mp4 \
  --starts 855,1709,3988,4843
uv run --project packages/vision python ml/goals/extract.py $S/goals/cache $S/match/magdeburg_goals/*.mp4 $S/goals/neg_clips/*.mp4
python ml/goals/overlay_ref.py $S/goals/cache
uv run --project packages/vision python ml/goals/compact.py $S/goals/cache   # optional: 15 MB -> 2.7 MB per clip
uv run --project packages/vision python ml/goals/evaluate.py $S/goals/cache $S/match/magdeburg_goals/index.json \
  --cues pan_rev,still_swing,zone_leave --template
uv run --project packages/vision python ml/goals/extract.py $S/goals/cache_seg $V/magdeburg_rostock_s{0,1,3,4}.mp4 --no-ball --no-det
uv run --project packages/vision python ml/goals/stream_eval.py $S/goals/cache_seg $S/goals/cache \
  $S/match/magdeburg_goals/index.json --starts 855,1709,3988,4843
```

## Club footage: goal candidates on the ingest's 3-minute segments
The broadcast study above worked on one TV game. This part runs on the raw club recordings of the
ingest (`ml/data/ingest_drive.py`, 3-minute segments at 1280x720, 60 fps) and turns the cues into a
**candidate list**: the top N moments per minute, each to be confirmed by a coach with one click.
Recall counts, precision does not.

### Data and labels
- **Footage**: 45 segments of 13 SG Wädenswil/Horgen NLB games (batches b01, b02 and the local
  batch_03). They all come from the same stream producer: an operated camera high on the side that
  pans with play and zooms a little, and a score overlay at the top. **There is no fixed-camera or
  overlay-free game with labels yet**, so the "fixed vs panning" and "overlay vs none" splits asked
  for cannot be measured: every labelled segment is panning with an overlay. The overlay is masked
  out of every motion signal and is used only as the label.
- **Labels from the overlay score**: PP-OCR (the `hallboard` models) reads the overlay's score field
  every 0.5 s (`seg_extract.py`; the field is the score-like token on the key frames that keeps its
  value and has no leading zero, unlike the clock), cleaned by `scoreboard.goals_from_scores`.
  This needs neither a clock nor a log and labels every segment with a running overlay. Jumps by
  several goals (overlay hidden) are left out. 35 segments have a usable reading: **79 goals in
  105 min**, 73 of them more than 6 s from a segment end.
- **Labels from the official log** (`segment_clock.game_labels`, the code behind `--labels`): 4
  games have both a log and a clock (Emmen 2023-09-03, Fortitudo Gossau, HC Arbon 2023-12-10, HSG
  Baden-Endingen; 18 log goals). They add one segment without an overlay reading (Baden-Endingen s0,
  1 goal) and measure the log delay.
- **The log is not late here.** Log time minus overlay change, same score, same segment: median
  **-0.5 s** (21 goals, range -3.0 to +0.5 s). The overlay changes about 1 s after the ball is in
  the net (checked on a counter-attack goal frame by frame). The 5 s delay of the Magdeburg log
  belongs to that TV production; on these club streams log, overlay and goal agree within ~1 s.
- **Hall-board clock mapping is unreliable when the anchor is far**: log entries counted from a
  clock reading more than 5 s away (`anchor_gap_s`) were 24 to 47 s off, one a first-half 1:0
  goal placed into a second-half segment at 23:20. They are left out (`MAX_ANCHOR_GAP_S`).

### Signals and cues (`seg_extract.py`, `seg_cues.py`)
One heavy pass per segment, cached as a compressed npz (1.6 MB, 70 MB for all 45): about 4.5 min of
wall time per 3-minute segment on 2 threads of the shared CPU, most of it YOLOX-m at 2 Hz.
- **Camera**: pan per decoded frame (about 30 Hz, phase correlation on 320x180 grey with a Hanning
  window and the overlay boxes masked; note that `cv2.phaseCorrelate` applies the window to its
  inputs in place), compensated motion energy.
- **Flow towards a half**: Farneback flow at 10 Hz minus the camera's median flow, so the residual
  is the players' canvas velocity; the moving pixels' mean x-flow, their share (activity) and a
  16-bin histogram over x.
- **People**: YOLOX-m at 2 Hz; feet in canvas coordinates (image + accumulated pan). Benches,
  spectators and the table are dropped as "static" (a canvas spot occupied in 60 % of the
  detection frames of the surrounding 30 s). Median x (centroid), 10-90 % spread, play position
  `p` (-1..1 between the segment's 3rd and 97th percentile), balance left/right of the centre.
- **Cues** on a 10 Hz grid: `pan_rev`, `still_swing`, `pan_after` (as before); `cen_rev`,
  `flow_rev`, `play_rev` (the same reversal on the people centroid, the residual flow, and their
  mean with the pan); `energy_drop`; the matched filter `tmpl_*` on per-segment standardised
  channels (leave-one-game-out, centred 2 s after the goal); `lull_after` (busy around t, quiet
  8-24 s later); the **restart detector** `restart` (a lull of 8 s with little activity and a still
  camera, then activity or the camera picks up; softly weighted by the play near the centre and
  people on both sides of the centre line) and `restart_back` (moved back by the median lag of
  27 s); `logreg` (all cues, leave-one-game-out).

### Results
Candidates: the top 1, 2 or 4 peaks per minute and segment (8 s non-maximum suppression, none in
the first and last 2 s). A goal is found when a candidate lies 3 s before to 8 s after the overlay
change. "Random" is the recall of the same number of random candidates: with an 11 s window, 4 per
minute cover most of the minute, so **r@1 and r@2 are the numbers that tell cues apart**. Window
AUC: best score in each goal's window against equally long windows 15 s away from every goal.
Dev = the 3 games looked at while designing `lull_after`, the restart detector and its lag; test =
the other 10 games (56 goals in 72 min), untouched while designing. Goals within 6 s of a segment
end are left out (`--edge-margin 6`; with them: `tmpl_people_flow` 0.51 / 0.80 / 0.91,
`tmpl_all+lull` 0.57 / 0.81 / 0.92 on all 79 goals).

| Score | recall @1 / 2 / 4 per min, all (73 goals) | test (56 goals) | AUC all | AUC test | candidate - goal, median (IQR) |
|---|---|---|---|---|---|
| random candidates | 0.19 / 0.37 / 0.69 | 0.18 / 0.35 / 0.70 | | | |
| `pan_rev` | 0.37 / 0.63 / 0.73 | 0.38 / 0.61 / 0.73 | 0.747 | 0.713 | -0.3 s (5.6) |
| `still_swing` | 0.42 / 0.67 / 0.89 | 0.39 / 0.66 / 0.88 | 0.825 | 0.795 | -0.5 s (3.7) |
| `pan_after` | 0.45 / 0.74 / 0.92 | 0.39 / 0.70 / 0.89 | 0.838 | 0.806 | -0.6 s (3.4) |
| `cen_rev` (people centroid) | 0.34 / 0.69 / 0.85 | 0.29 / 0.61 / 0.82 | 0.746 | 0.693 | +0.2 s (4.7) |
| `flow_rev` (residual flow) | 0.18 / 0.32 / 0.60 | 0.20 / 0.34 / 0.57 | 0.582 | 0.596 | +4.2 s (2.7) |
| `play_rev` (pan + people + flow) | 0.49 / 0.64 / 0.80 | 0.46 / 0.61 / 0.77 | 0.774 | 0.765 | -0.7 s (3.6) |
| `energy_drop` | 0.26 / 0.51 / 0.78 | 0.25 / 0.52 / 0.77 | 0.599 | 0.569 | +3.1 s (2.9) |
| `lull_after` | 0.59 / 0.78 / 0.97 | 0.52 / 0.73 / 0.96 | 0.810 | 0.790 | +1.2 s (3.2) |
| `restart_back` (throw-off) | 0.33 / 0.56 / 0.82 | 0.27 / 0.52 / 0.80 | 0.617 | 0.614 | +3.1 s (5.1) |
| sum z(pan_rev, still_swing, cen_rev, flow_rev) | 0.41 / 0.57 / 0.81 | 0.43 / 0.55 / 0.79 | 0.772 | 0.760 | -1.1 s (5.2) |
| `tmpl_camera` (pan, energy) | 0.42 / 0.66 / 0.88 | 0.41 / 0.64 / 0.86 | 0.743 | 0.732 | +2.8 s (3.7) |
| **`tmpl_people_flow`** (centroid velocity, flow x, activity) | 0.53 / **0.84** / 0.94 | 0.45 / **0.79** / 0.93 | **0.862** | **0.837** | +1.4 s (**2.5**) |
| `tmpl_all` (pan, centroid, flow x, activity, energy) | 0.53 / 0.81 / 0.93 | 0.48 / 0.75 / 0.91 | 0.854 | 0.829 | +1.8 s (3.7) |
| `tmpl_camera` + `lull_after` | 0.62 / 0.84 / 0.90 | 0.57 / 0.80 / 0.88 | 0.840 | 0.802 | +2.3 s (3.0) |
| `tmpl_people_flow` + `lull_after` | 0.56 / 0.84 / 0.96 | 0.48 / 0.79 / 0.95 | 0.844 | 0.831 | +1.5 s (2.2) |
| **`tmpl_all` + `lull_after`** | **0.62** / **0.84** / **0.97** | **0.54** / 0.79 / **0.96** | 0.840 | 0.825 | +1.5 s (3.3) |
| `logreg` (all cues, LOGO) | 0.59 / 0.84 / 0.92 | 0.54 / 0.79 / 0.89 | 0.836 | 0.816 | +1.2 s (3.8) |
| broadcast template, broadcast normalisation | 0.34 / 0.52 / 0.71 | 0.36 / 0.55 / 0.70 | 0.711 | 0.690 | -1.6 s (5.2) |
| broadcast template, per-segment normalisation | 0.40 / 0.59 / 0.77 | 0.41 / 0.61 / 0.79 | 0.764 | 0.746 | -1.6 s (3.4) |

At about 0.7 goals per minute, 2 candidates per minute with 84 % recall means a precision of about
30 %: a coach confirms roughly 3 candidates per goal. Template centre 0 s instead of 2 s after the
goal gives `tmpl_people_flow` 0.58 / 0.82 / 0.89 (AUC 0.872), 4 s gives 0.51 / 0.72 / 0.90: the
choice matters little between 0 and 2 s.

Per game (`tmpl_all` + `lull_after` / `tmpl_people_flow` / `pan_after`, recall @1 / 2 / 4):

| Game | goals / min | tmpl_all + lull | tmpl_people_flow | pan_after | random |
|---|---|---|---|---|---|
| Emmen 2023-09-03 (dev) | 5 / 12 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.40 / 0.80 / 1.00 | 0.21 / 0.36 / 0.72 |
| Fortitudo Gossau 2023-09-23 (dev) | 6 / 12 | 0.83 / 1.00 / 1.00 | 0.67 / 1.00 / 1.00 | 0.83 / 0.83 / 1.00 | 0.20 / 0.40 / 0.72 |
| HC Arbon 2023-12-10 (dev) | 6 / 9 | 0.83 / 1.00 / 1.00 | 0.83 / 1.00 / 1.00 | 0.67 / 1.00 / 1.00 | 0.18 / 0.39 / 0.75 |
| HSG Baden-Endingen 2023-11-19 | 5 / 12 | 0.40 / 0.60 / 0.80 | 0.20 / 0.60 / 0.60 | 0.40 / 0.60 / 0.80 | 0.20 / 0.38 / 0.74 |
| BSV Stans 2022-11-05 | 5 / 9 | 0.80 / 1.00 / 1.00 | 0.60 / 0.80 / 1.00 | 0.40 / 0.80 / 1.00 | 0.17 / 0.40 / 0.73 |
| Chênois 2023-05-13 | 9 / 9 | 0.67 / 1.00 / 1.00 | 0.56 / 1.00 / 1.00 | 0.56 / 0.89 / 1.00 | 0.16 / 0.35 / 0.71 |
| Emmen 2022-11-17 | 11 / 12 | 0.46 / 0.64 / 1.00 | 0.36 / 0.55 / 0.91 | 0.18 / 0.36 / 0.64 | 0.18 / 0.34 / 0.66 |
| GC Amicitia 2023-03-15 | 6 / 6 | 0.50 / 1.00 / 1.00 | 0.50 / 1.00 / 1.00 | 0.33 / 0.50 / 0.83 | 0.21 / 0.38 / 0.73 |
| Kreuzlingen 2022-05-29 (playoff) | 6 / 6 | 0.67 / 0.67 / 0.83 | 0.33 / 0.67 / 0.83 | 0.50 / 0.67 / 1.00 | 0.14 / 0.34 / 0.66 |
| STV Baden 2023-04-05 | 4 / 6 | 0.00 / 0.50 / 1.00 | 0.25 / 0.50 / 1.00 | 0.25 / 0.75 / 1.00 | 0.17 / 0.29 / 0.62 |
| TV Birsfelden 2023-03-25 | 4 / 6 | 0.50 / 0.75 / 1.00 | 0.50 / 1.00 / 1.00 | 0.50 / 1.00 / 1.00 | 0.21 / 0.40 / 0.68 |
| TV Möhlin 2023-02-18 | 6 / 6 | 0.67 / 0.83 / 1.00 | 0.67 / 1.00 / 1.00 | 0.50 / 1.00 / 1.00 | 0.15 / 0.38 / 0.62 |

### What works, what does not
- **The people and flow template is the best single score** and needs no camera pan: 0.84 recall at
  2 candidates per minute (0.79 on the held-out games), AUC 0.86, timing +1.4 s (IQR 2.5 s). It is the closest stand-in for a fixed camera, where the canvas velocity of the players is what
  the image shows directly (it could not be tested on one: see Data). The camera-only template is
  much weaker here (AUC 0.74) than on TV (0.82 with pan + energy): the club operator follows the
  ball less consistently than a TV camera.
- **The post-goal lull is real goal-specific evidence.** Goal-aligned averages (15 dev goals):
  activity drops to about 0.3-0.45 of the segment median from 8 to 26 s after the goal and the
  camera stands still from 18 to 28 s; turnovers and saves go straight on. `lull_after` alone
  reaches 0.59 / 0.78 / 0.97 (test 0.52 / 0.73 / 0.96); added to the template it lifts recall at 1
  per minute from 0.53 to 0.62 (test 0.48 to 0.54). It was designed on the 3 dev games and is
  clearly weaker on the test games (AUC 0.79 against 0.88 on dev, recall @1 0.52 against 0.82), but
  it holds there.
- **The throw-off detector does not work as specified.** The play does not dwell at the court
  centre: with the fast throw-off the conceding team restarts straight into its attack, and from a
  panning camera's canvas the centre is only a rough estimate (`p` stays around 0.5 after goals,
  `bal` does not rise). What remains is "a lull ends", which fires 20 to 34 s after the goal (median
  27 s): moved back by the median lag it reaches AUC 0.62 and 0.56 recall at 2 per minute (random
  0.37), far below the template. Its useful part is already in `lull_after`.
- **Residual flow alone (`flow_rev`) and energy drop fail** (AUC 0.58, 0.60): the residual flow is
  dominated by parallax and blur during fast pans; the template uses the flow only together with the
  centroid and the activity.
- **The broadcast template transfers only partly**: AUC 0.71 with the broadcast's normalisation,
  0.76 per-segment normalised, against 0.84 to 0.86 for templates learned on club footage, and it
  peaks 1.6 s before the overlay change instead of after it. Learning the template from the free
  overlay labels of a few club games is clearly better than reusing the TV one.

### Failure cases
- **Goals in quick succession** (two goals within 8 s, or a goal within 8 s of a turnover peak):
  the non-maximum suppression keeps one candidate. Seen in Emmen 2022 (58/64 s), Kreuzlingen
  (134/140 s).
- **A very busy camera** (Emmen 2022-11-17: pan 90th percentile 270-300 px/s against 40-190 in the
  other games, tighter zoom): every attack looks like a swing; recall @2 0.64.
- **Segment ends**: windows look 2 s back and 3 s ahead (24 s for the lull), so goals in the first
  or last few seconds are missed; on continuous footage this does not arise.
- **False alarms** (65 at 2 per minute in the 4 games with a log): 23 are next to a logged shot
  (saved 7, missed 7) or turnover (8), the rest have no log entry at all (the log only lists
  shots, turnovers and penalties, not every possession change). As on TV, the false alarms are
  transitions that look like goals.

### Recommendation for the product
- **Candidates**: `tmpl_all` + `lull_after` (or `tmpl_people_flow` + `lull_after` when no pan is
  measured), peaks with 8 s suppression. **2 candidates per minute of play** (about 80 % recall,
  about 3 clicks per goal); **4 per minute** when the coach wants nearly everything (96 %).
  Show each candidate as a clip from 10 s before to 4 s after the peak: the median peak is 1.5 s
  after the goal (interquartile range 3.3 s), and a goal counts as found up to 8 s before the peak.
- **Threshold**: rank, do not threshold. Score scales vary per game (camera operator), so a fixed
  per-minute rate is more stable than a score threshold.
- **Cost**: one YOLOX-m pass at 2 Hz plus 10 Hz flow is about 1.5x real time on 2 CPU threads; the
  people detections are needed anyway for the rest of the pipeline. Without people the
  camera-only score is much weaker (AUC 0.74).
- **Labels to collect next**: (1) **fixed-camera and overlay-free games with official logs** and a
  readable hall board: nothing in the ingest so far, so the fixed-camera claim is untested;
  (2) more overlay games from other producers: the overlay score is a free, exact (about 1 s) label
  and makes the template learnable per camera style (79 goals already beat the TV template
  clearly); (3) the coach's one-click confirmations themselves, with the rejected candidates as
  hard negatives (turnovers, saves), to train a small temporal classifier on the cached 10 Hz
  channels instead of the hand-made template; (4) audio (whistle and crowd): untested, but
  camera-independent.

### Reproduce
```bash
S=<scratchpad>; G=$S/goals_raw
# segments in $G/vid: kaggle datasets download -f, or links to the ingest's batch folder
uv run --project packages/vision python ml/data/segment_clock.py --labels
nice -n 10 uv run --project packages/vision python ml/goals/seg_extract.py $G/cache $G/vid/*.mp4
uv run --project packages/vision python ml/goals/seg_labels.py $G/cache $G/labels.json
uv run --project packages/vision python ml/goals/seg_eval.py $G/cache $G/labels.json --edge-margin 6 \
  --broadcast $S/goals/cache --out $G/results.json [--inspect tmpl_people_flow]
```

## In the product: `handball_vision.goalcandidates`
The analysis proposes goal candidates from what the observation pass (`observe.observe`) already
has, the camera motion and the people detections: no optical flow, no motion energy, no second
decoding pass and no court calibration. `goal_template.py` learns the template from the cached
heavy pass above and exports it as `packages/vision/handball_vision/data/goal_template.json`
(versioned: mean profile, channels, normalisation, lull windows, selection, evaluation). It runs
the cached signals through the product code itself, so its numbers are those of the shipped code.

- **Channels** (10 Hz, reference px = a 1280 px frame at the median zoom): camera pan (canvas x of
  the frame centre per second, from `CameraMotion`), the people's median x velocity in the image
  (canvas velocity minus the pan), the mean x velocity in the image and the mean speed (body
  heights per second) of people matched mutual-nearest between detection frames 0.5 s apart.
  People are sampled at 2 Hz as in the training data; static people (bench, table) are dropped.
- **Score**: rz(template cosine) + rz(lull), where the lull uses the people speed instead of the
  flow share. Channels and scores are normalised over a rolling 3-minute window that keeps its
  full length at the video ends (a 3-minute video gets exactly the per-segment statistics).
- **Candidates**: per 3-minute block the best peaks at 4 per minute, 8 s suppression; each carries
  the lowest rate (1, 2 or 4 per minute) that proposes it. Clip -10 s to +4 s around the peak, goal
  estimated 1.5 s before the peak.

| Score (leave-one-game-out, 73 goals / 56 test goals) | recall @1 / 2 / 4 per min, all | test | window AUC all / test | peak - goal |
|---|---|---|---|---|
| research `tmpl_all` + `lull_after` (needs flow and energy) | 0.62 / 0.84 / 0.97 | 0.54 / 0.79 / 0.96 | 0.840 / 0.825 | +1.5 s (IQR 3.3) |
| **product** (pan + people, people lull) | **0.59 / 0.88 / 0.95** | **0.54 / 0.84 / 0.93** | 0.864 / 0.861 | +1.6 s (IQR 2.9) |
| product channels, people velocities on the canvas (pan not taken out) | 0.55 / 0.82 / 0.93 | 0.48 / 0.79 / 0.91 | 0.840 / 0.819 | +2.1 s |

- **Canvas sign in `seg_cues.signals`**: `cv2.phaseCorrelate(prev, cur)` returns the content shift
  (checked: +5 for content moved 5 px right; the cached pan correlates +0.93 with the median
  Farneback flow), so the hall position is `image - cumsum(pan)`, not `image + cumsum(pan)`. The
  research `cx`, `cx_v` and the static-people mask therefore used "image + content shift"
  coordinates. The product uses the correct canvas, and takes the camera speed out of the people
  velocities instead (image velocities plus a pan channel), which scores best of the variants
  tried (people canvas velocities: 0.82 at 2 per minute; image velocities: 0.88).
- **Cost**: 0.22 s for a 5-minute club clip on top of a 602 s observation pass (shared CPU,
  YOLOX-s every 3rd frame), 1.8 s for a synthetic 60-minute game: well under 0.1 % of the pass.
- **Not measured on the product path end to end**: the labelled segment videos were no longer on
  disk, so the product pass (YOLOX-s at 8 Hz, pan from the rotation model) was only run on an
  unlabelled 5-minute club clip. The template was learned with YOLOX-m at 2 Hz and phase
  correlation; the per-window standardisation should absorb the scale differences, but a check on
  labelled games through `observe` is the first thing to do with new footage.

```bash
uv run --project packages/vision python ml/goals/goal_template.py $G/cache $G/labels.json --version 2026-11-05.1
uv run --project packages/vision python ml/goals/goal_template.py $G/cache $G/labels.json --check
```

## Shots: candidates for every shot (goal, save, miss)
After goals, coaches want the shots with saves and misses, and who shot. Shots without a goal so
far only came from tagging, courtside marks or an imported official report. Question: do the
goal-candidate signals also find the other shots, and can the report's shots be put on the video?

### Data
- **Labels**: the official game logs per segment (`ml/data/segment_labels/*.json`,
  `segment_clock.py --labels`; times from the match clock read in each segment, accurate to a few
  seconds, entries counted from a clock reading more than 5 s away left out). 7 games now have a
  log and a clock: the 4 NLB games of before plus 3 cup games of the owner's first local batch
  (`handball-segs-l01`: RTV Basel - Kadetten 2024-04-27, Red Dragons Uster - Seen Tigers / Pfadi,
  SG Waedenswil/Horgen - RTV Basel 2024-10-19). **28 segments, 84 min, 93 shots** more than 6 s
  from a segment end: 53 goals (2 penalties), 23 saves, 17 misses; 15 turnovers. The logs of the
  older SG games (BSV Stans, Chenois, ...) are empty, so they have no shot labels.
- **Signals**: the product channels (`goalcandidates.signals`: pan, people image velocity,
  matched people x velocity and speed) from the product observation pass (`product_path.py
  observe`: worker proxy, rotation-model camera, YOLOX-s) for 22 segments, the research pass
  (YOLOX-m at 2 Hz, phase correlation) for the other 6. All cameras are operated and panning. No
  ball-net output is cached for these segments, so ball cues near the goal could not be tested.

### Cues tried (`shot_eval.py`)
`goal`: the shipped goal score (goal template + lull; its template leave-one-game-out here, from
the overlay goals of the other games); `goal_tmpl`, `lull` its parts; `shot_tmpl`: the same matched
filter with its profile learned from the logged shots (centre 1 s after the log time),
leave-one-game-out; `shot_tmpl_sm` the same from saves and misses only; `end`: the people's canvas
centroid at one end of the covered court and then turning round (the play position proxy for "the
attack ends at the goal"; without court calibration there is no goal-area share of people);
`pan_after`; research cues on the research segments; `logreg`: logistic regression on goal
template, lull, shot template, end and pan_after, leave-one-game-out. Candidates: the top peaks per
segment at 1, 2, 4, 6 per minute, 8 s suppression; a shot is found by a candidate 3 s before to
8 s after its log time (the goal rule). Random candidates as the baseline: at 6 per minute and an
11 s window they cover almost everything, so **1, 2 and 4 per minute tell the cues apart**.

### Results (recall @ 1 / 2 / 4 / 6 per minute, candidate - shot at 2 per minute, median (IQR))
| Score | all shots (93) | goals (53) | saves (23) | misses (17) | timing |
|---|---|---|---|---|---|
| random | 0.18 / 0.36 / 0.68 / 0.87 | 0.19 / 0.36 / 0.70 / 0.90 | 0.20 / 0.38 / 0.69 / 0.93 | 0.16 / 0.36 / 0.71 / 0.90 | |
| `goal` (shipped goal score) | 0.52 / 0.83 / 0.92 / 0.94 | 0.60 / 0.94 / 0.96 / 0.98 | 0.52 / 0.74 / 0.91 / 0.91 | 0.41 / 0.76 / 0.94 / 0.94 | +2.1 s (2.8) |
| `shot_tmpl` | 0.54 / 0.81 / 0.94 / 0.95 | 0.60 / 0.91 / 0.96 / 0.98 | 0.57 / 0.74 / 1.00 / 1.00 | 0.47 / 0.82 / 0.88 / 0.88 | +1.4 s (2.8) |
| `shot_tmpl_sm` | 0.48 / 0.76 / 0.88 / 0.91 | 0.53 / 0.83 / 0.94 / 0.98 | 0.52 / 0.78 / 0.91 / 0.91 | 0.53 / 0.82 / 0.88 / 0.94 | +0.4 s (2.7) |
| `end` | 0.46 / 0.72 / 0.87 / 0.90 | 0.45 / 0.72 / 0.89 / 0.92 | 0.61 / 0.91 / 1.00 / 1.00 | 0.47 / 0.76 / 0.94 / 1.00 | -0.8 s (3.6) |
| `pan_after` | 0.49 / 0.80 / 0.92 / 0.96 | 0.51 / 0.87 / 0.96 / 0.98 | 0.57 / 0.83 / 1.00 / 1.00 | 0.53 / 0.76 / 0.94 / 1.00 | +0.2 s (3.5) |
| `shot_tmpl` + `end` | 0.48 / 0.77 / 0.90 / 0.91 | 0.49 / 0.75 / 0.92 / 0.94 | 0.61 / 1.00 / 1.00 / 1.00 | 0.47 / 0.71 / 0.88 / 0.88 | -0.5 s (2.9) |
| **`shot_tmpl` + `goal`** (shipped) | 0.53 / **0.84 / 0.94** / 0.95 | 0.62 / 0.94 / 0.96 / 0.98 | 0.48 / 0.78 / 0.96 / 0.96 | 0.41 / 0.76 / 0.94 / 0.94 | +1.6 s (3.2) |
| `logreg` | 0.57 / 0.83 / 0.90 / 0.91 | 0.57 / 0.89 / 0.94 / 0.96 | 0.74 / 0.91 / 0.96 / 0.96 | 0.53 / 0.76 / 0.88 / 0.88 | +0.7 s (3.0) |
| `logreg` + `goal` | 0.56 / 0.86 / 0.92 / 0.95 | 0.66 / 0.94 / 0.96 / 0.98 | 0.61 / 0.83 / 0.91 / 0.96 | 0.35 / 0.82 / 0.94 / 0.94 | +1.6 s (3.1) |

On the 16 research-pass segments the research cues do not beat the product ones (all shots @ 2 / 4:
`pan_rev` 0.76 / 0.78, `cen_rev` 0.78 / 0.83, `lull_after` 0.78 / 0.93, product `goal` 0.80 /
0.93).

Per game (all shots, `goal` / `shot_tmpl`, recall @ 1 / 2 / 4 / 6):

| Game | shots (goals / saves / misses) / min | `goal` | `shot_tmpl` | random |
|---|---|---|---|---|
| Cup RTV Basel - Kadetten 2024-04-27 | 17 (12 / 2 / 3) / 9 | 0.47 / 0.82 / 0.94 / 0.94 | 0.41 / 0.76 / 0.94 / 1.00 | 0.18 / 0.34 / 0.71 / 0.90 |
| Cup Red Dragons Uster - Seen Tigers / Pfadi | 16 (8 / 5 / 3) / 15 | 0.69 / 0.88 / 0.94 / 0.94 | 0.56 / 0.88 / 0.94 / 0.94 | 0.18 / 0.33 / 0.67 / 0.86 |
| Cup SG W/H - RTV Basel 2024-10-19 | 19 (13 / 3 / 3) / 12 | 0.37 / 0.84 / 0.89 / 0.89 | 0.47 / 0.89 / 1.00 / 1.00 | 0.17 / 0.34 / 0.68 / 0.88 |
| NLB Emmen 2023-09-03 | 9 (5 / 1 / 3) / 12 | 0.56 / 0.67 / 0.78 / 0.78 | 0.67 / 0.67 / 0.78 / 0.78 | 0.15 / 0.33 / 0.59 / 0.77 |
| NLB Fortitudo Gossau 2023-09-23 | 13 (5 / 5 / 3) / 12 | 0.54 / 0.92 / 1.00 / 1.00 | 0.62 / 0.85 / 1.00 / 1.00 | 0.18 / 0.37 / 0.72 / 0.90 |
| NLB HC Arbon 2023-12-10 | 9 (6 / 3 / 0) / 12 | 0.78 / 1.00 / 1.00 / 1.00 | 0.67 / 1.00 / 1.00 / 1.00 | 0.18 / 0.32 / 0.69 / 0.88 |
| NLB HSG Baden-Endingen 2023-11-19 | 10 (4 / 4 / 2) / 12 | 0.30 / 0.60 / 0.90 / 1.00 | 0.50 / 0.50 / 0.80 / 0.80 | 0.16 / 0.39 / 0.72 / 0.90 |

At the labelled moments (best score 3 s before to 8 s after the entry, AUC): shots against
turnovers 0.36 to 0.56 for every cue (`goal` 0.42, `shot_tmpl` 0.37, `end` 0.56, `pan_after`
0.52), goals against saves and misses 0.55 to 0.62 (`goal` 0.62, `lull` 0.57).

### What the numbers say
- **The transition the goal candidates look for is a shot transition.** Saves and misses end the
  attack with the same camera swing and the same people running back; only the lull after it is
  goal-specific, and it does little harm for saves. So the goal score already finds 83 % of all
  shots at 2 per minute and 92 % at 4 (random 36 % and 68 %), saves and misses 74 to 76 % at 2
  and 91 to 94 % at 4. The shot template adds a little at 4 per minute (0.94) and moves the peak
  closer to the shot (+1.4 s against +2.1 s); goal + shot template is the shipped mix (0.84 / 0.94).
  **The bar of 70 % at 4 per minute is met for every outcome**, and the gap to random is large at
  2 per minute. The logistic regression and the `end` cue win on saves (`shot_tmpl` + `end` finds
  all 23 at 2 per minute) but lose on goals and misses; with 23 saves that is not a basis to ship.
- **Shots do not separate from turnovers on these signals** (AUC below 0.5: a turnover followed
  by a counter-attack is the bigger swing). Candidates near a logged turnover are only 4 to 8 %
  of the list, though: most candidates that are no shot are transitions the log does not list
  (lost balls without a technical error, fouls, restarts). The outcome cannot be read from them
  either (goals against saves and misses 0.62). Ball cues near the goal and the people in the
  goal area would be the next step; they need the ball net output and the court calibration on
  these segments.
- **With an official log the candidates become one key per shot.** Each logged shot suggested to
  the candidate nearest its estimated shot time (peak - 1.5 s, at most 8 s away, each shot once):

| Score | rate | candidates | near a logged shot | near a turnover only | logged shots suggested | suggested on the right candidate | wrong suggestions | right / wrong with the log 10 s off |
|---|---|---|---|---|---|---|---|---|
| `goal` | 2 | 168 | 0.46 | 0.08 | 0.87 | 0.83 | 0.05 | 0.11 / 0.79 |
| `goal` | 4 | 336 | 0.27 | 0.05 | 0.97 | 0.91 | 0.06 | 0.10 / 0.88 |
| shipped (`shot_tmpl` + `goal`) | 2 | 168 | 0.48 | 0.07 | 0.88 | 0.84 | 0.05 | 0.10 / 0.80 |
| shipped (`shot_tmpl` + `goal`) | 4 | 336 | 0.28 | 0.04 | 0.98 | 0.94 | 0.04 | 0.15 / 0.81 |

  At 4 per minute 94 % of the logged shots land on the candidate that shows them, with the
  shooter and the outcome; the coach confirms with one key and skips the candidates without a
  suggestion. **This needs the report times on the video to within a few seconds**: with the log
  10 s off almost every suggestion is wrong. Counting from the throw-off of the half (what the
  import did) is off by every clock stop before the entry (a time-out is a minute). Hence the
  clock map in the API (`services/match_clock.py`): the overlay clock read by the analysis where
  there is one (exact), else the nearest anchor (throw-off, an entry already confirmed on the
  video, an overlay goal), with the clock stop between the anchors as the uncertainty that widens
  the suggestion window (8 s exact, at most 20 s).

### In the product
- `handball_vision.goalcandidates`: `shot_score` = rz(shot template cosine) + rz(goal template
  cosine) + rz(lull), weights in `data/shot_template.json` (versioned; `shot_template.py` learns
  the profile from the logged shots and stores the leave-one-game-out evaluation of the shipped
  selection: 0.84 / 0.94 / 0.95 at 2 / 4 / 6 per minute, peak - shot +1.5 s, IQR 3.2; saves 0.78 /
  0.96, misses 0.76 / 0.94; the goal template in it is the shipped one, which saw the goals of
  the 4 NLB games). Candidates at 2, 4, 6 per minute, default 4, same blocks, suppression and
  no-play mask as the goals; clip -8 s to +4 s; shot estimated 1.5 s before the peak. They travel
  in the worker payload as `goal_candidates.shots`; no change in the workers.
- API: one candidate table with a `kind` (goal, shot) and the confirmed `outcome` (migration
  0031). Shot candidates come with the report's suggestion and the report's shots on the video
  (confirmed, suggested, missing, outside); a confirmation pins the report entry to the video (no
  second event; it survives a re-import) or creates a shot event of the given side, outcome and
  shooter; rejections stay as hard negatives. Details for the UI: docs/plans/ui-match-workspace.md,
  "API additions from the analysis session".
- Next: the coach's confirmations and rejections (with the outcome) are labels for a small
  temporal classifier on the cached 10 Hz channels; ball-net peaks near the goal mouth for the
  outcome; games filmed by a fixed camera to check the people channels alone.

```bash
S=<scratchpad>
uv run --project packages/vision python ml/data/segment_clock.py --labels
uv run --project packages/vision python ml/goals/shot_eval.py ml/data/segment_labels \
  --obs $S/gc_bench/obs $S/gc_bench/obs_l --cache $S/goals_raw/cache --store $S/shots/sig.pkl \
  --goal-labels $S/goals_raw/labels.json --goal-cache $S/goals_raw/cache
uv run --project packages/vision python ml/goals/shot_template.py ml/data/segment_labels \
  --obs $S/gc_bench/obs $S/gc_bench/obs_l --cache $S/goals_raw/cache --store $S/shots/sig.pkl \
  --version 2026-11-05.s1 [--check]
```
