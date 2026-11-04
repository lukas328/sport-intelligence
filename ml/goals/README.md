# Goal moments from the picture (research, not shipped)

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
RESULTS_TABLE

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
   already uses canvas coordinates, reaches AUC PEOPLE_AUC here. Auto-panning cameras (Veo,
   Pixellot) behave like the broadcast camera, so the pan cues carry over directly.

## Reproduce
```bash
S=<scratchpad>; V=data/videos/segs
python ml/goals/cut_negatives.py $S/match/magdeburg_aligned.json $S/goals/neg_clips \
  --segs $V/magdeburg_rostock_s0.mp4,$V/magdeburg_rostock_s1.mp4,$V/magdeburg_rostock_s3.mp4,$V/magdeburg_rostock_s4.mp4 \
  --starts 855,1709,3988,4843
uv run --project packages/vision python ml/goals/extract.py $S/goals/cache $S/match/magdeburg_goals/*.mp4 $S/goals/neg_clips/*.mp4
python ml/goals/overlay_ref.py $S/goals/cache
uv run --project packages/vision python ml/goals/evaluate.py $S/goals/cache $S/match/magdeburg_goals/index.json \
  --cues pan_rev,still_swing,zone_leave --template
uv run --project packages/vision python ml/goals/extract.py $S/goals/cache_seg $V/magdeburg_rostock_s{0,1,3,4}.mp4 --no-ball --no-det
uv run --project packages/vision python ml/goals/stream_eval.py $S/goals/cache_seg $S/goals/cache \
  $S/match/magdeburg_goals/index.json --starts 855,1709,3988,4843
```
