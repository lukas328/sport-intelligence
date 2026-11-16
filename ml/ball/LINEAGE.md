# Ball detection and tracking: lineage

Status 2026-11-16. Research only: no ball net and no research tracker from `ml/` is in the product yet.
This file traces where every result comes from: models, data, test sets, trackers, labelling,
failures and decisions. The detailed experiment log stays in `ml/ball/README.md`; this file is the
index over it, with commit hashes and file paths, and the basis for a possible workshop paper.

## 1. Purpose and how to keep it updated

This file is the single source of truth for the ball work: reviews of the approach work from it
alone, and anything a review had to infer because it was missing here is added (section 11).

Every new ball model, dataset, test set, labelling pass or tracker change gets a row here **in the
same commit** that adds the code or the result (model table in section 4, tracker table in section
5, data in section 2, test sets in section 3, timeline in section 9). Give the commit hash of the
result commit (or "this commit"), the Kaggle kernel id, the data it used, the test set and its
numbers exactly as in the README. Failures go into section 7 with their numbers. Where a fact is not
backed by a file or a commit, mark it "unverified" instead of guessing. Kaggle names below are
given without the account prefix (all kernels and datasets live in the owner's private Kaggle
account unless stated otherwise).

Conventions: "top 1" = the detector's strongest peak lies within 12 px of the label (1280 px wide
frame); "top 5" = one of the 5 strongest peaks does; "tracker" = the tracker's one point per frame
lies within 12 px. Commit hashes are on branch `claude/ecstatic-darwin-p0ss4x` unless marked
"PR #3", which refers to commits of the squash-merged pull request #3 (visible on GitHub, not in
the local history; the squash commit is `7581b26`).

## 2. Data inventory

Library context: 226 games with video, 1 130 segments, about 393 h, all transcoded to 1280 px wide
(crf 25), mostly panning broadcast cameras (overview page of 2026-11-15; 226 games also in
`docs/plans/tracking-strategie.md` section 1). Segments live as Kaggle datasets `handball-segs-bNN`
(cloud) and `handball-segs-lNN` (owner uploads), see `docs/plans/HANDOVER.md`.

**Global exclusions (apply to every training set from round 7 on):**
- Test set 2 games (`ml/ball/test_games.json`, 42 games) **and every game of the same home hall**
  (`kaggle/train_r7_push.py` item 2, `ml/gpu/JOBS.md` "Regel für alle Ball-Trainings").
- First test (test half) frames: anything within 2 s of a test-half or unsplit labelled frame is
  dropped from rounds 5b/6 on (`kaggle/train_r6.py` docstring). Halls of the first test: Uznach,
  Eisenach, Leimental, Horgen, Cottbus per `ml/ball/testset_pick.py` (the README says 7 halls; the
  two lists are not reconciled in the sources).
- Non-handball games: `ml/data/not_handball.json` (1 game,
  `DE_Bezirksoberliga_ATSKulmbach_DonBoscoBamberg_2015`, basketball, found in training clips t114,
  t115 on 2026-11-14, commit `aae1fb8`). Skipped by `ml/gold/train_labels_r9.py` from round 10 on.
  Note: the owner's round-8 peak labels (`ml/ball/data/r8_human_labels.json`) contain 19 points of
  that game (6 ball, 13 none), so **rounds 8 and 9 trained on them**; round 10 and later do not.
- Gold v1 clips are one per test set 2 game, so they inherit the test set 2 exclusion. Shot gold
  clips keep at least 10 s away from any training clip of round 9/10 (`ml/gold/pick_shots.py`).

| ID | Source | What, how produced | Size | Where stored | Used by | Licence / caveats |
|---|---|---|---|---|---|---|
| D1 | TeamTrack handball_side | one hall, fisheye panorama, ball in every frame; triplets cut by `extract_teamtrack_triplets.py` | 1 hall | Kaggle public `atomscott/teamtrack`; tiles in `handball-ball-triplets` (unverified which dataset holds them) | single-frame net, round 1 on (in the round 6 mix as `tt_pos`/`tt_neg`, so in all later rounds and hr nets) | MIT. The state-of-the-art review (`docs/plans/ball-stand-der-technik.md` 3.1) says TeamTrack's README mentions only person boxes; our README says the ball is in every frame. Not reconciled. |
| D2 | Own labelled frames ("Ball-Labeling Halle", `labelling/frames.html`) | 130 frames from 7 halls, 80 with ball, split per hall into train and test half; train half used for training (`tiles_from_frames.py`) | 130 frames (40 test balls held out) | `handball-ball-triplets` / `handball-ball-extra` (exact split between the two unverified) | round 2 on (train half) | own |
| D3 | Own labelled ball paths ("Ball-Pfade Halle", `labelling/paths.html`) | 3 s scenes, a click every ~0.1 s, frames between interpolated (`tiles_from_paths.py`), plus random and net-peak negatives | "some scenes" (no count in the sources) | as D2 | round 3 on | own |
| D4 | Own full games, random tiles | 3-minute segments per game, random tiles as negatives (`collect_game.py`) | not recorded | as D2 | early rounds (exact rounds unverified) | own |
| D5 | DeepSport basketball instants | 16 arenas, frame pairs 40 ms apart, 3D ball centre projected and scaled to 8 to 24 px (`deepsport_tiles.py`) | 16 arenas | Kaggle public `deepsportradar/basketball-instants-dataset` | round 3 on (in the round 6 mix as `ds_pos`/`ds_neg`, hence also r7 to r10, hr1, hrp1, hr2, hrp2) | **CC BY-NC-SA 4.0: research only.** Every net from round 3 on, including the current HRNet nets, is a research model and must not ship as trained (`ml/ball/README.md` top). |
| D6 | Roboflow handball sets | still frames with ball boxes: handball-ballon v13, handball-xutbx v16, handball-detection-fj8rc v2, custom_handball_dataset v5, handball5 v1 (`roboflow_tiles.py`); handball-detection-2 left out (mostly football) | about 2 900 balls | `handball-roboflow-ball-tiles` | round 4; down-weighted in round 5 (never trained); **excluded from the round 6 mix** ("no Roboflow", `train_r6.py` line 773; not in the r6 kernel sources) | CC BY 4.0 per project (not individually verified, see state-of-the-art review). `kaggle/train_hr_push.py` docstring lists "Roboflow" among the hr data; the code it builds on (round 6 mix) excludes it. Treat the docstring as inaccurate (unverified by a run log). |
| D7 | OWLv2 pseudo-labels, Kaggle kernel `handball-ball-owl` | OWLv2 base (Apache-2.0) on 480 px tiles upscaled to 960, bursts of 5 frames every 6 s; kept when 3 of 5 burst frames link (score >= 0.35, best box >= 0.45), the chain moves and is not a fixed spot; persistent still spots become hard negatives (`kaggle/owl_gpu.py`, confirm logic in `train_r5.py`/`train_r6.py`) | segments b01 to b03 ("Horgen segments" in `train_r5b.py`); segment count not recorded | kernel output `handball-ball-owl`; cut tiles in `owl_tiles_r6.zip` (kernel output) | round 5 (never trained), round 6 on | Apache-2.0 teacher. Labels not checked by hand. |
| D8 | OWLv2 pseudo-labels, Modal job 2 | as D7, on l01 and l02 | 189 of 300 segments (l01 100/100, l02 89/100, l03 0/100); 11.0 h on a T4, 7.23 USD | `handball-gpu-owl-20261105-1449` (`ml/gpu/JOBS.md` "Erledigt" 2) | round 6 on | The README's round 6 row says "189 segments"; `train_r6.py` uses D7 and D8 together, so the true segment count of round 6 is 189 plus the b01 to b03 segments (number unverified). Job 3 (remaining 111 segments of l02/l03) is still listed as open in `ml/gpu/JOBS.md`; whether it ran is unverified. |
| D9 | OWLv2 pseudo-labels for round 7 | Kaggle kernels `handball-owl-r7-1`, `handball-owl-r7-2`, 144 segments of l04 to l13 (two per game, 72 games), test set 2 games and halls held out (commit `8563763`) | 144 segments | kernel outputs; segment datasets l04, l06 to l13 | round 7 on | as D7 |
| D10 | Mined tracklets (self-training) | the net over every frame of segments, peaks linked with balltrack, fixed spots dropped, long moving tracklets saved as tiles (`kaggle/mine_gpu.py`, `mine_tracklets.py`); about 65 to 70 % real balls by eye; from round 5b on confirmed by OWLv2 (box >= 0.3 within 12 px on half the tiles); failed tracklets give hard negatives | Magdeburg, Muelheim, Leimental-Frauenfeld, U20, Uznach, Eisenach (`train_r5b.py`); tile count not recorded | kernel output `handball-ball-mine` (sources `handball-game-segments`, `handball-ball-models`) | round 5b (never trained), round 6 on (`mine_pos`/`mine_neg`) | own; validation segment `magdeburg_rostock_s4` |
| D11 | Owner's "Ball oder nicht?" peaks (hard negatives and balls) | round 7's confident peaks (score >= 0.4, top 3 per frame) in segments round 7 never saw, at running clock (`hardneg_pick.py`, kernel `handball-ball-hardneg`, page `labelling/crops.html`, commits `a9e95f0`, `b5761ad`); two rounds of 500 labelled by the owner | 1 000 points: 273 ball, 720 none, 7 unsure, 34 games; as tiles 986 (298 with a ball, 688 hard negatives) | `ml/ball/data/r8_human_labels.json` (added in `bcad5f7`) | verifier v2 (498 peaks of one round of 500, apparently the first: 135 ball / 363 no ball / 2 unsure), round 8 on (round 10 on without the basketball game) | own. New segments, not new halls (all 34 games also feed OWL tiles). |
| D12 | Claude's training-clip labels, round 9 snapshot | 46 of the 171 training clips (`ml/gold/train_clips_v1.json`), labelled by Claude (the LLM coding assistant) without the owner's rough track: overview pass, keyframe pass, dense pass; exported tiers sure / track (`ml/gold/export_train.py`) | 834 ball points | `ml/gold/data/train1_llm/`, `ml/gold/data/train_ball_v1.json` at commit `5ecbabe` | round 9 | pilot on 8 gold clips: 98 % of sure points within 12 px of gold |
| D13 | Claude's training-clip labels with the owner's review, v1 | all 171 clips through overview, keyframe and dense passes (`61b97bf`); the owner confirmed 2 832 of 2 902 unconfirmed fast points (tier check) and rejected 55 (review parts `ml/gold/data/train1_review/p1` to `p4`) | 5 767 ball points in 150 clips (2 804 sure + 131 track = 2 935 where two looks agree, 2 832 confirmed); 3 147 free, 2 620 held | `ml/gold/data/train_ball_v1.json` (commits `a7cf93d`, `39351d8`) | round 10, hr1, hrp1, hr2, hrp2; tracker rescoring training (with round-8 candidates) | 171 clips = 3 per game from 57 games outside test set 2 and its halls, 8 s each, 114 with running clock (`b47dc04`). Only 146 of the 150 clip entries hold a positioned point (checked from the file). 2 902 - 2 832 - 55 = 15 points are unaccounted for in the sources (perhaps unsure or skipped; unverified). |
| D14 | Net hard negatives in labelled training frames | per labelled frame the net's strongest peak (score >= 0.3, at least 40 px from the labelled ball) as "none" (`ml/gold/train_labels_r9.py`) | 741 (round 9), 4 875 (round 10) | built into the kernel's embedded label JSON (zlib + base64 from round 10, `train_r10_push.py`) | round 9 on | which net's peaks were used for round 10's negatives is not stated (round 9's PRE_JSON is the likely input; unverified) |
| D15 | Verifier crops (v1) | 72 px three-frame crops from the round 7 OWL tiles: 9 311 confirmed balls, 9 299 r7 peaks within 12 px; negatives 13 948 r7 peaks, 9 013 wrists, 6 446 noses, 5 564 torso centres (RTMPose), 1 405 fixed spots, 10 716 random | about 65 000 crops; 14 of 111 games held out | outside the repo (weights and crops not committed) | verifier v1, v2 | RTMPose via rtmlib (Apache-2.0) |

Single-frame start: "TeamTrack + 37 own" frames (README benchmark table). Early "ball" labels from
Möhlin were mostly a fixed ball-like spot on the wall (README "Findings"); they were the reason for
moving to three frames.

Model weights: rounds 3 (`ball_best.pt`), 6, 7, 8 in Kaggle dataset `handball-ball-models`
(`ball_r6.pt`, `ball_r7.pt`, `ball_r8.pt`); round 9 as kernel output of `handball-ball-r9`; round 10
presumably as kernel output of `handball-ball-r10` (unverified); hr1, hrp1, hr2, hrp2 in Kaggle
dataset `handball-ball-hrmodels` (`ml/gpu/JOBS.md` job 12, `ml/gpu/prelabel_clips.py`). Weights
are never in the repo.

## 3. Test sets

| Test set | How chosen | Size | Used for | Caveats |
|---|---|---|---|---|
| T1 test half | per hall half of the owner's labelled frames (D2), never trained on | 40 balls in the same 7 halls as training (80 ball frames incl. train half) | single-frame net to round 6 (README "Benchmark: labelled test half"); OWLv2 on 24 of its balls | Same halls as training, so it measured known halls. One ball = 2.5 points. Round 3's 33 % is inflated by about 90 training tiles near test frames (round 6's is not). Retired after 2026-11-09 as too small. Script `bench_labelled.py` (12 px). |
| T2 test set 2 | `ml/ball/testset_pick.py`: games of batches l05 to l13 not in any ball training, minus the first test's halls, at most one game per home team, frames at running clock where known; OWLv2 suggestions as pre-selection (kernel `handball-ball-testset2`), labelled by the owner on `labelling/testset.html` (commits `be3b2ec`, `206ec85`, `c91e955`, `db692b4`) | 252 frames from 42 games in 42 new halls: 177 balls, 72 frames without a ball, 3 unsure; about half at running clock (103 balls clock running, 74 stopped) | rounds 3 and 6 to 8, verifier v1 and v2 (`bench_testset2.py`, 12 px, CPU ~10 min) | Single frames (triplets), not clips. One ball = 0.6 points (SE about 3.5 points). The labeller saw OWLv2 suggestions (85 balls clicked on a suggestion), so OWLv2's numbers are optimistic. Games listed in `ml/ball/test_games.json`; never in training with their halls. Not used since round 9 (replaced by gold v1). Native-resolution variant (job 11) still open. |
| T3 gold v1 | `ml/gold/pick_clips.py` (seed 2026): one 8 s clip per test set 2 game, at running clock where clock data exist (`ml/gold/gold_clips.json`, commit `a0e3b6d`); labelled with the owner's rough tracks plus Claude's precise points and the owner's review (section 6) | 42 clips, 42 halls; 25 clips with running clock; fps 30 (17), 25 (13), 50 (5), 60 (4), 59.94 (2), 23.976 (1). 1 555 usable positioned points at `9a5ac20` (905 free, 650 held); **1 553 after `75bd04d`** (2 points rejected: g08 frame 126, g34 frame 108); 14 "out" labels; 738 fast points by `eval_ball.gold_points` (ball moves more than 12 px per frame to a labelled neighbour; the 561 on the overview page came from another count, its definition is unverified); 17 unconfirmed "check" points not used | rounds 8 to 10, hr1/hrp1, ensemble, all tracker work (`ml/gold/eval_ball.py`) | (a) Points cluster in 42 clips: paired p values are optimistic. (b) Only 14 no-ball frames: false positives are barely measurable. (c) **Heavy development use on 2026-11-16**: the repeated-frame step came from error analysis on gold (g08, 50 fps clips), the rescoring scale 3 was chosen on gold (checked with 2-fold CV by clip), tracker parameters were tuned with 2-fold CV on gold, the hit radius was examined on gold, and the owner inspected the three clips with most misses (g34, g08, g03). Gold v1 is therefore a development set for the tracker from 2026-11-16 on, not a clean final test. (d) The README tables after `75bd04d` still say "1555"; the tracker numbers from `46331ba` on use 1 553 points (rechecked 2026-11-16, n printed by the evaluation). |
| T3p pilot without rough track | 8 gold clips (g00, g05, g10, g15, g20, g25, g30, g33) labelled by Claude without the owner's rough track and compared with gold (`ml/gold/data/pilot_nolead/`) | 173 points (overview page) | validating the training-label method: 98 % of "sure" points within 12 px | uses gold clips, so the method was tuned in view of gold labels (small leak of method choice, not of training data) |
| T4 shot gold | `ml/gold/pick_shots.py`: shots from the official game logs (goals, saves, misses; `ml/data/segment_labels/*.json`), independent of any detector, at most 5 per game, clips 7 s before to 3 s after the logged time, at least 10 s from any round 9/10 training clip (`ml/gold/shot_clips.json`, commit `82889c6`) | 61 shots, 13 games: 22 goals, 24 saves, 15 misses; fps 60 (36), 30 (15), 50 (10). Frozen final-test split by home hall (`1a40b6a`): test 20 shots from 4 halls (6 goals, 8 saves, 6 misses), dev 41 shots from 9 games | to become the main measure for shots (`tracking-strategie.md` section 9, step 0); pre-labels via Modal job 12 (`ml/gpu/JOBS.md`) | Not labelled yet (status 2026-11-16). None of the 13 games is a test set 2 game; 3 of them also give training clips, so shot halls can be training halls: results will be somewhat easier than gold v1 and must say so. Split "test" must not be used for development, tuning or looking at results before the end. |
| V-in validation inside training | round 6 on: one game per OWL source held out (`val_games`, `train_r6.py` line 584), mined segment `magdeburg_rostock_s4`, up to 2 000 tiles; round 8 on: every third game of the owner's peaks (and from round 9 the training-clip labels) as group "human" | varies | hourly checkpoint selection and "human validation" numbers (e.g. hr1 0.61 -> 0.63, hrp1 0.67 -> 0.71 at threshold 0.5) | Same sources as training: overstates transfer (verifier v1: 0.91 validation AUC vs 0.81 on test peaks). |
| V-ver verifier tuning set | v2: games of the owner's first 500 peaks split by game: train 23 games (90 ball, 242 no ball), tuning 11 games (45 ball, 121 no ball) | 166 confident peaks | choosing the verifier v2 rule | 45 tuning balls: differences of 0.02 AUC are noise |

## 4. Model lineage

BallNet3 = ResNet-18 layers 1 to 2 plus decoder, stride-4 heatmap, CenterNet focal loss, input three
frames (t-G, t, t+G; G = 3 above 40 fps, else 2) stacked to 9 channels, first conv widened (centre
channels from the single-frame weights, neighbours zero). Results are copied from
`ml/ball/README.md`; "-" = not measured on that set.

| Version | Date, commit | Architecture | Init | Data added | Steps / budget | Kernel / script | Results | Status, why |
|---|---|---|---|---|---|---|---|---|
| single-frame | before 2026-11-04 (PR #3 `03cc835`, squash `7581b26`) | ResNet-18 heatmap, 1 frame | unverified | TeamTrack + 37 own frames | not recorded | `train_ballnet.py` (CPU) | T1 (all 80): top 1 6 %, top 5 14 % | dropped: learned the fixed wall spot (Möhlin labels) |
| round 1 | 2026-11-04 (PR #3) | BallNet3 | single-frame net | TeamTrack (D1) | not recorded | `train_ballnet3.py` (CPU); whether round 1 ran on CPU or Kaggle is unverified | T1: 12 % / 23 %. TeamTrack own validation: 64 % at 2 % false alarms | superseded |
| round 2 | 2026-11-04 (PR #3 `0489eab`) | BallNet3 | round 1 (unverified) | + owner frames, train half (D2) | not recorded (`train_gpu.py` default 10 000 iterations) | first Kaggle GPU run, `kaggle/train_gpu.py` | T1: 20 % / 28 % | superseded |
| round 3 | 2026-11-04 (PR #3 `0489eab`) | BallNet3 | round 2 (unverified) | + ball paths (D3), DeepSport (D5) | not recorded (`train_gpu_fast.py` default 20 000) | `kaggle/train_gpu_fast.py`, kernel `handball-ball-train-fast` (which round used which trainer is unverified) | T1: 33 % / 47 % (inflated, see T1); T1 OWLv2 subset (24 balls): 29 % top 1, 46 % top 5; T2: 15 % / 29 %, score >= 0.3 at the ball 11 %, no-ball >= 0.5 8 % | superseded; weights `ball_best.pt` (`handball-ball-models`), base of rounds 5 and 6 |
| round 4 | between 2026-11-04 and 2026-11-05 (in `7581b26`; own commit not found) | BallNet3 | unverified | + Roboflow still frames (D6) | not recorded | `train_gpu_fast.py` (unverified) | T1: 23 % / 45 % | dropped: still frames without motion hurt; Roboflow removed from the mix from round 6 |
| round 5 | 2026-11-05 (PR #3 `2713226`, `8e2fd96`) | BallNet3 | round 3 | + OWLv2 pseudo-labels (D7), Roboflow down-weighted | never trained | `kaggle/train_r5.py`, kernel `handball-ball-r5` | none | failed: multi-process DataLoader deadlock, log stops after "val at start" (23 min); no training step ever logged (`train_r6.py` docstring) |
| round 5b | 2026-11-05 | BallNet3 | round 3 | round 5 + mined tracklets confirmed by OWLv2 (D10) | never trained | `kaggle/train_r5b.py`, kernel `handball-ball-r5b` | none | failed: same deadlock, log stops at 2.9 h |
| round 6 | 2026-11-09 (`7c943d0` kernel, result `00ca931`, T2 in `db692b4`) | BallNet3 | round 3 (`ball_best.pt`, per the r5 design reused in r6; the r6 docstring does not restate it, unverified) | round 3 data without Roboflow + OWLv2 D7 + D8 + mined D10; persistent still spots as hard negatives; threads instead of worker processes, hourly checkpoints also as base64 in the log | ITERS cap 30 000 fitted to a 9 h kernel budget; steps done not recorded in the README | `kaggle/train_r6.py`, kernel `handball-ball-r6` | T1: 33 % / 42 % (ties round 3; more confident: score >= 0.3 at 45 % of balls vs 23 %); T2: 29 % / 51 %, >= 0.3 44 %, no-ball >= 0.5 43 % | superseded; first proof that OWLv2 labels help in new halls (29 % vs 15 % on T2). `ball_r6.pt` in `handball-ball-models`. "Not promoted" on T1 at the time. |
| round 7 | 2026-11-09 recipe `2c22c4d`, result 2026-11-10 `89e6e9c` | BallNet3 | round 6 | + OWLv2 D9 (144 segments, 72 games); test set 2 games and halls held out; twice the negatives; motion blur on 30 % of the batch | 30 000 steps | `kaggle/train_r7_push.py`, kernel `handball-ball-r7` | T2: 35 % / 53 %, >= 0.3 50 %, no-ball >= 0.5 54 %; paired vs r6 top 1: 15 gained / 5 lost (p = 0.04); found at 10 % FA 15.8 %, at 25 % FA 25.4 % | superseded; more false alarms (54 % vs 43 %). Base of the verifier work. `ball_r7.pt` in `handball-ball-models`. |
| verifier v1 | 2026-11-10 `f1ba15d` (PR #37) | 4-stage conv crop classifier, 145 k parameters, 64 px input, 9 channels | scratch | D15 | 6 459 steps of 128, 43 min on 4 CPU cores | `ml/ball/verifier/` `data.py`, `train.py`, `eval.py` | held-out games AUC 0.91 vs net peaks, 0.98 vs hands; T2 top 1: verifier alone 31.6 %, net x verifier 36.2 % (+8 / -6, p = 0.79), found at FA 10 % 18.1 % vs 15.8 % | dropped: no measurable gain on T2 |
| verifier v2 | 2026-11-12 `4db309e` (PR #38) | same | fine-tune of v1 (lr 5e-4) | + 332 human crops (owner's first 500 peaks, train games) in a unified crop format | 1 211 steps of 128, 6 min | `verifier/v2.py`, `train_v2.py`, `tune_v2.py`, `eval_v2.py` | tuning AUC 0.812 [0.73, 0.87] vs net 0.670 (rule s^0.25 v^0.75); T2 one run: top 1 35.6 % vs 35.0 % (+11 / -10, p = 1.00), found at FA 10 % 18.6 % vs 15.8 % | dropped: no measurable gain on T2 |
| round 8 | 2026-11-12 recipe `4ee62d3`, result `2706af2` | BallNet3 | round 7 | + owner's 1 000 peaks as 224 px native triplet tiles (D11; 298 ball tiles, 688 hard negatives); every third game held out as "human" | 30 000 steps, 3.7 h training | `kaggle/train_r8_push.py`, kernel `handball-ball-r8` | T2: 33 % / 50 %, no-ball >= 0.5 44 %, found at FA 10 % 17 %, at 25 % 25 %; paired vs r7 top 1 8 / 12 (p = 0.50). Gold v1: top 1 49.7 %, top 5 77.2 %, tracker v2 69.0 % (fast 70.3 %), product balltrack 32.1 % | superseded: no measurable gain on T2; held-out human tiles show the mistakes were learned (false peaks at 0.5: 38 % -> 28 %). `ball_r8.pt` in `handball-ball-models`. Its candidates train the tracker rescoring. Trained on 19 basketball-game peaks. |
| round 9 | 2026-11-14 recipe `bcad5f7` (labels `5ecbabe`), result `0d6734a` | BallNet3 | round 8 | + Claude's labels from 46 training clips (D12, 834 points) + 741 net hard negatives (D14) | not recorded (recipe = round 8, cap 30 000) | `kaggle/train_r9_push.py`, kernel `handball-ball-r9` | Gold v1 (OWLv2 boxes from the round-8 gold run): top 1 51.5 % (124 / 96 vs r8, p 0.07), top 5 78.5 % (p 0.10), tracker v2 71.3 % (70 / 35, p 0.001; fast 73.6 %), product balltrack 35.8 % | superseded; first gain since round 7. Also trained on 19 basketball-game peaks. |
| round 10 | 2026-11-15 recipe `a7cf93d`/`39351d8`, result `58337e5` | BallNet3 | round 9 | training labels with the owner's review (D13: 5 767 points, 150 clips) + 4 875 hard negatives + owner's peaks without the basketball game | 30 000 steps | `kaggle/train_r10_push.py`, kernel `handball-ball-r10` | Gold v1: top 1 56.5 % (157 / 79 vs r9, p < 1e-6), top 5 81.0 % (95 / 57, p 0.003), tracker v2 73.4 % (64 / 31, p 0.001; fast 76.7 %). With repeated-frame step 75.5 % (fast 80.4 %); with rescoring 75.8 % (fast 80.4 %) | superseded by the HRNet nets as candidate source; still the last BallNet3. Clearest data gain of any round (7x the labels of round 9). |
| hr1 | 2026-11-15 code `c8b247f`, result 2026-11-16 `f98b29f` | BallHR (`ml/ball/ballhr.py`): own HRNet-style net after the WASB idea, branches at strides 4 / 8 / 16 (48 / 96 / 192 channels), 7.7 M parameters, output stride 4; no WASB code or weights | scratch | exactly the round-10 data | 21 183 steps (1.23 s per step), kernel budget 9.5 h, ITERS cap 90 000, lr 1e-3 | `kaggle/train_hr_push.py`, kernel `handball-ball-hr1` | Gold v1: top 1 63.2 % (261 / 157 vs r10, p 4e-7), top 5 83.9 %, tracker v2 74.5 % (fast 76.6 %); + repeated frames 75.8 % (fast 78.7 %); + gaps and rescoring 79.1 % (fast 83.1 %). Human validation 0.61 -> 0.63 over the last checkpoints | current (part of the ensemble). In `handball-ball-hrmodels`. |
| hrp1 | 2026-11-15 code `0eb79f0`, result 2026-11-16 `f98b29f` | BallHRP (`ml/ball/ballhrp.py`): timm `hrnet_w18` with ImageNet weights, first conv widened to 9 channels (centre pretrained, neighbours zero), head over 4 branches at stride 4, 9.7 M parameters | ImageNet (timm) | exactly the round-10 data | 13 094 steps (1.65 s per step); README says "8 h budget", the kernel budget is 9.5 h (difference probably setup and tile cutting; unverified); backbone lr 3e-4, head 1e-3 | `kaggle/train_hr_push.py ... hrp`, kernel `handball-ball-hrp1` | Gold v1: top 1 65.7 % (313 / 171 vs r10, p 1e-10; vs hr1 238 / 200, p 0.08), top 5 86.2 %, tracker v2 74.0 % (fast 72.1 %); + repeated frames 75.2 % (fast 74.0 %); + gaps and rescoring 80.1 % (fast 80.6 %). Human validation 0.67 -> 0.71 (vs 0.63 for hr1) | current (part of the ensemble). In `handball-ball-hrmodels`. timm `hrnet_w18` weight licence not separately checked (review checked `hrnet_w18_small`: MIT tag). |
| hr1 + hrp1 | 2026-11-16 `f98b29f` | ensemble of candidates: both nets' top 5 merged within 8 px, mean score; no parameter fitted | - | - | - | `ml/gold/tracker.py` input | Gold v1: net top 1 73.8 %, tracker v2 77.0 % (fast 77.0 %; vs r10 130 / 73 p 8e-5, vs hr1 73 / 34 p 2e-4, vs hrp1 78 / 31 p 8e-6); + repeated frames 78.2 % (fast 79.5 %); + gaps and rescoring **84.0 % (fast 86.0 %)**, 2-fold held-out 83.9 % (fast 86.2 %) | **current best research path**. Adding round 10 as third net: 75.6 % (worse). |
| hr2 | after 2026-11-16 `f98b29f` (no result commit) | BallHR | hr1 | same data | fresh warm-up and cosine schedule at half the learning rates | `kaggle/train_hr2_push.py hr`, kernel `handball-ball-hr2` | **none recorded in the repo** | trained: listed in `handball-ball-hrmodels` by `ml/gpu/JOBS.md` job 12 and `ml/gpu/prelabel_clips.py` defaults; gold results unverified/not yet measured |
| hrp2 | as hr2 | BallHRP | hrp1 | same data | half learning rates (backbone 1.5e-4, head 5e-4) | `kaggle/train_hr2_push.py hrp`, kernel `handball-ball-hrp2` | **none recorded in the repo** | as hr2 |
| OWLv2 (teacher, no training) | first bench 2026-11-05 (PR #3 `3c96676`) | OWLv2 base, open vocabulary, queries "a photo of a handball", "a ball", "a small ball in the air", 480 px tiles upscaled to 960 | Google weights (Apache-2.0) | - | - | `kaggle/owl_gpu.py`, gold kernel `ml/gold/kaggle/prelabel_gpu.py` (every 2nd frame) | T1 (24 balls): top 1 50 %, top 5 50 %, 10 of 11 boxes >= 0.5 are the ball; T2: 44 % / 66 %, >= 0.3 51 %, no-ball >= 0.5 10 % (optimistic, see T2); gold v1: top 1 46 %, ball in hand 58 % (overview page only, no README row) | in use as pseudo-label teacher and as tracker candidate source (rescoring weight +6.8). Cost: about 210 s per 3-minute segment for 150 frames on a T4 including download (`ml/gpu/owl_pseudo.py`), so up to about 1.4 s per frame on a GPU; far too slow for the product (a 60-minute game at every 2nd frame would be hours). |
| YOLOX-S "sports ball" (product) | in product before this research | YOLOX-S COCO (Apache-2.0), class 32 | COCO | - | - | `packages/vision/handball_vision/detection.py` | not measured on gold v1 | the product's ball detector today (see section 5) |
| ball holder classifier | 2026-11-04 (PR #3 `2c4e95f`) | per-player crop classifier | unverified | holder crops (`holder_crops.py`) | not recorded | `train_holder.py` | not recorded | side track, not pursued in the sources since |

## 5. Tracker lineage

All gold numbers: gold v1, 12 px, one point per frame.

| Step | Date, commit | What | Candidates | Gold v1 result | Status |
|---|---|---|---|---|---|
| Product ball path | before the research (PR #3 `55ee786`, `af17912`) | `packages/vision/handball_vision/balltrack.py`: peaks linked at physically possible speed into tracklets, static spots (canvas pixels) dropped, best chain by weighted interval scheduling; feeds `ballpossession.py` (holder = ball inside a player box, passes, turnovers), only while the match clock runs (`4a6992d`) | in the product: YOLOX-S "sports ball" detections (`ballpossession.py` lines 183 to 198); on gold: the research net + OWLv2 candidates (`ml/gold/suggest.py`) | 32.1 % with round 8 candidates, 35.8 % with round 9 (README round 9 table). Weaker than the net's top peak alone (49.7 %). | in the product today; to be replaced. Note: the gold number measures the balltrack algorithm on research candidates, not the product's YOLOX detector (not measured). |
| Tracker v2 (DP) | 2026-11-13 `198fcc7`; static spots per detector `72bbe96` | `ml/gold/tracker.py`: dynamic programming over net peaks (every frame) and OWLv2 boxes (every 2nd frame), merged within MERGE px; reward = detector scores + agreement bonus; cost for misses and new segments; constant-velocity step cost with speed-dependent tolerance, `vmax`; predecessor up to `gap` = 2 frames back; static spots earn nothing; optional linear fill | net + OWLv2 | 69.0 % with round 8 (fast 70.3 %); 71.3 % with round 9; 73.4 % with round 10; 74.5 % hr1, 74.0 % hrp1, 77.0 % hr1 + hrp1 | superseded by the steps below (same file) |
| Parameter tuning | round 9 re-tune (2026-11-14/15, overview page only); per net 2026-11-16 `f98b29f` | `ml/gold/tune_tracker.py`: random search, 150 settings, 2-fold cross-validation over gold clips | hr1, hrp1 | held-out 74.4 % -> 75.1 % (hrp1), 74.2 % -> 74.4 % (hr1); re-tuning on round 9 "brought nothing" (overview page, no numbers) | defaults kept. Parameters of v2 were originally tuned on round-8 output (README round 9). |
| Repeated-frame step | 2026-11-16 `5a4e944` | `dup_px` (5 px), `dup_max` (1): a candidate within 5 px of its predecessor one frame back, while the ball moves, keeps the predecessor's velocity (videos storing 25 fps as 50 or 30) | as before | r10 73.4 -> 75.5 % (fast 76.7 -> 80.4, 50/60 fps 62.8 -> 67.9); hr1 74.5 -> 75.8 %; hrp1 74.0 -> 75.2 %; hr1 + hrp1 77.0 -> 78.2 % (fast 77.0 -> 79.5 %, 50/60 fps 64.0 -> 67.3 %), paired +23 / -5 (p 9e-4) | current. Found by error analysis on gold (g08: tracker 52 % vs net top peak 95 %). No parameter fitted on gold. |
| Fast-ball gaps | 2026-11-16 `46331ba` | `gap_fast` 4, `v_fast` 8 px per frame at 30 fps: a fast predecessor may lie up to 4 frames back | as before | without it hr1 + hrp1 drops from 84.0 % to 82.2 % (fast 83.1 %) | current. Larger values or a gap in seconds change nothing. |
| Learned rescoring | 2026-11-16 `46331ba` | `ml/gold/tracker_rescore.py`: logistic regression on net score, top-1, OWLv2 score, agreement, static, moving support, slow persistence; weights `ml/gold/data/tracker_rescore.json` (bias -4.40, net +3.31, top1 +1.55, owl +6.80, both -0.72, static -4.13, move +2.52, slow -1.56); trained on the training clips (39 375 candidates, 5 241 on a ball) with round-8 candidates that never saw those labels; reward = `rescore` 3 x probability | as before | with gaps, "before" = repeated-frame step on, gap 2, hand-set reward: r10 75.5 -> 75.8 % (+94 / -90, p 0.83); hr1 75.8 -> 79.1 % (fast 78.7 -> 83.1); hrp1 75.3 -> 80.1 % (fast 74.0 -> 80.6); **hr1 + hrp1 78.2 -> 84.0 % (fast 79.5 -> 86.0 %, 50/60 fps 67.4 -> 76.4 %)**, paired all +124 / -34 (p 3e-13), fast +62 / -14 (p 2e-8). Without the repeated-frame step: 81.3 % (fast 81.3 %) | current. The scale 3 is the only choice made on gold (2-fold by clip: held-out 83.9 % / fast 86.2 %). Must be retrained when the candidate source changes (calibrated on BallNet3 round-8 scores; round 10 does not gain). |

Note on the "before" columns: the repeated-frame table gives hrp1 "after" as 75.2 % and hr1 + hrp1 as
78.2 %; the rescoring table's "before" gives hrp1 75.3 % and the 50/60 fps "before" values differ by
0.1 to 0.3 points (e.g. r10 68.0 % vs 67.9 %). The README does not explain this; it may be the
2 rejected gold points (`75bd04d`, between the two commits). Unverified.

Uncertainty and the OWLv2 ablation (2026-11-16, same code as `46331ba`, hr1 + hrp1, bootstrap over
the 42 clips, 2 000 resamples, 95 % interval):

| Candidates | all balls | fast balls |
|---|---|---|
| net + OWLv2 | 84.0 % [78.7, 88.7] | 86.0 % [77.2, 93.0] |
| net only (OWLv2 removed, rescoring weights unchanged) | 78.6 % [72.8, 83.7] | 81.8 % [72.9, 89.3] |

So the headline is about +-5 points uncertain (fast about +-8): the large steps (77 -> 84 %) are real,
differences of 1 to 2 points are noise. OWLv2 is worth about 5 points but is not shippable (cost,
section 4); the rescoring was learned with OWLv2 features and has not been retrained without them.

**Shippable tracker without OWLv2 and confidence (2026-11-16, `ml/gold/tracker_eval_conf.py`).**
The rescoring was relearned without OWLv2 (`tracker_rescore.py --noowl`, weights
`ml/gold/data/tracker_rescore_noowl.json`: training clips, round-8 net candidates with the OWLv2 boxes
removed, 27 627 candidates, 4 703 on a ball; bias -3.86, net +3.48, top1 +1.62, move +2.43, slow -1.69,
OWLv2 columns and static 0). `tracker.py` picks these weights automatically for a clip without OWLv2
output (`Params.rescore_w = "auto"`). Gold v1, hr1 + hrp1, 12 px, 95 % clip bootstrap:

| Tracker | all | fast | 50/60 fps |
|---|---|---|---|
| with OWLv2 (reference, not shippable) | 84.0 % [78.7, 88.6] | 86.0 % [77.0, 93.0] | 76.4 % [65.0, 87.6] |
| no OWLv2, OWLv2-trained weights | 78.6 % [72.6, 83.7] | 81.8 % [72.1, 89.7] | 74.7 % [63.4, 87.5] |
| **no OWLv2, no-OWLv2 weights (shippable, new headline)** | **80.0 % [74.7, 84.9]** | **83.3 % [75.2, 90.1]** | 75.3 % [63.1, 86.6] |
| same without the repeated-frame step | 78.2 % [72.7, 82.9] | 79.7 % [70.1, 87.3] | 70.8 % [60.7, 82.5] |
| same without the fast-ball gaps | 78.4 % [72.7, 83.3] | 80.4 % [71.7, 87.6] | 74.7 % [64.1, 86.3] |

Paired (all balls): no-OWLv2 weights against OWLv2-trained weights +31 / -9 (sign p 7e-4, difference
[+0.5, +2.4] points); the repeated-frame step +39 / -10 ([+0.2, +4.5]); the fast-ball gaps +34 / -8
([+0.2, +3.3]). Both steps still help without OWLv2. The cost of dropping OWLv2 is now 4 points
overall and 2.7 fast.

Confidence: `track_clip_conf` gives each point the geometric mean of its ball probability
(rescoring; filled frames the lower end) and the mean probability of its segment; `Params.conf_min`
leaves points below it out (default 0, output unchanged). Precision = hits / output points on
labelled frames (1 553 ball frames, 14 "out" frames, so it measures right against wrong points far
more than invented balls); recall = hits / ball frames. Shippable tracker:

| threshold | 0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
|---|---|---|---|---|---|---|---|---|
| precision | 81.9 % | 84.5 % | 87.4 % | 89.5 % | 92.1 % | 93.2 % | 95.5 % | 98.0 % |
| recall | 80.0 % | 75.5 % | 67.9 % | 63.0 % | 55.8 % | 45.1 % | 32.6 % | 15.8 % |

Threshold chosen on one half of the clips, applied to the other (both ways): for 95 % precision held
out 93.9 % precision at 40.5 % recall (threshold about 0.6; on all clips at 0.59: precision [91.3,
98.3], recall [23.7, 45.2]); for 90 % precision held out 90.3 % at 61.4 % recall (threshold about
0.3; on all clips at 0.32: precision [85.8, 93.5], recall [51.8, 70.6]). With OWLv2 for reference:
95 %: 94.7 % / 39.5 %; 90 %: 90.0 % / 69.6 %. Point-only and segment-only confidence give the same
picture within noise (95 %: recall 37.6 % and 44.3 %; 90 %: 58.0 % and 66.6 %, held out). Reading:
the confidence separates right from wrong points only moderately; a "sure" output at 90 % precision
keeps about 60 % of the balls. A better confidence (e.g. from player boxes or a learned segment
classifier) is open; whether 90 % precision is the right operating point depends on the use (shot
analysis vs. ball possession).

Error budget after rescoring (hr1 + hrp1, fast balls, `tracking-strategie.md` section 9): 8.5 % tracker
picks the wrong candidate, 5.4 % no detector sees the ball. Before rescoring (README "repeated frames",
357 misses of 1555): 8.2 % of balls on the net's top peak and 5.6 % among its top 5 but another
candidate chosen, 2.4 % only OWLv2 has the ball, 6.2 % no detector.

## 6. Labelling pipeline lineage

**Test set 2 page** (2026-11-09, `be3b2ec`, `206ec85`, `c91e955`): owner clicks the ball in single
frames, OWLv2 suggestions pre-selected from 0.6, up to three hints with snap, optional tag for a
wrong top suggestion (head, hand, foot, other).

**"Ball oder nicht?"** (2026-11-10, `a9e95f0`, `b5761ad`; `labelling/crops.html`): one key press per
confident net peak (three-frame crop plus scene). Rounds 1 and 2: round 7 peaks >= 0.4 (D11). Round 3
(`237bf02`, 2026-11-12; `labelling/build_crops.py`, `hardneg_pick.py --clock-only`, round 8, min score
0.2, 1280 px scenes, "elsewhere" click): prepared but **deprioritised** by the strategy
(`tracking-strategie.md` section 7); no labels from it in the sources. The same format is later used
for reviewing Claude's "check" points (`ml/gold/check_items.py`).

**Gold v1 pipeline** (2026-11-12 to 2026-11-13):
1. Clips and pre-labels: `pick_clips.py`, Kaggle kernel `handball-gold-prelabel`
   (`ml/gold/kaggle/prelabel_gpu.py`: frame-exact clip mp4s, net top 5 every frame, OWLv2 every 2nd
   frame), suggestions via the product's balltrack (`suggest.py`, later `--v2` for tracker v2,
   `2b7341a`). Commit `a0e3b6d`.
2. Owner rough track: labelling page `ml/gold/labelling/gold.html`, follow mode (pointer recorded every
   frame at 0.25x to 1x, H/V/O keys for states, `abde5e2`), rough-track mode `#grob` (`33ded04`). The
   rough track lags 1 to 2 frames and misses throws and bounces: **never a label**, only where to look
   (`ml/gold/export.py`). Precision mode (3x view, one click per keyframe, `3b943d1`) gives tier
   "owner" (10 points in gold v1).
3. Claude's keyframe pass: contact sheets (`llm_sheets.py`, 240 px crops around the guess every 6
   frames, candidates as numbered rings, `321f663`); answers applied by `llm_apply.py` (src "llm").
4. Second pass: `llm_dense_sheets.py` for fast passages and open keyframes next to a precise point
   (`4ff4b47`, `ce559d7`). The commit says fast = more than 12 px per frame; the script's default is
   `--fast 25`; which threshold was used for gold v1 is unverified.
   Answer files (added to the repo on 2026-11-16): `ml/gold/data/gold1_llm/llm` (pass 1: per clip the
   sheet meta `<clip>.json`, `<clip>_answers.json`, the resulting `<clip>_doc.json`) and
   `ml/gold/data/gold1_llm/llm2` (pass 2). How the answers split: pass 1, 1 870 rows: 54 % left open
   ("?"), 36 % a candidate number, 9 % an own point, 1 % no ball; pass 2, 1 378 rows: 48 % open, 35 %
   candidate, 17 % own point. Where a point was given, it was a detector candidate in 80 % (pass 1)
   and 66 % (pass 2) of the cases. Consequence: gold points lie preferentially where a detector
   already had the ball (section 11, review 1, item 3).
5. Tiers (`export.py`, agree 60 px): owner; sure (Claude's point within 60 px of the owner's rough
   track at f-1..f+1: two looks agree); track (smooth run anchored to an owner/sure point, `bb3af78`);
   check (neither). Commit `68876f3`.
6. Owner review of the check tier (`check_items.py`, crops page, J = confirmed, F = rejected): 663
   confirmed, 8 rejected; 1 555 usable points (`9a5ac20`). On 2026-11-16 the owner checked all 194
   points of g34, g08, g03: 192 right, 2 rejected (`75bd04d`).

**Training labels pipeline** (2026-11-13 to 2026-11-15):
1. Clips: `ml/gold/train_clips_v1.json` (171 clips, `b47dc04`).
2. Overview pass replaces the owner's rough track (`llm_overview.py`, whole frame 1280 px with a
   100 px grid every 0.2 s, candidates numbered; `72bbe96`). Reason: the tracker's guess sits on a
   lamp, logo or bench bag about a third of the time, so crops around it miss the ball.
3. Keyframe pass (s1, `llm_sheets.py`, `--only-rough` `7556a55`) and dense pass (s2), as for gold.
4. Pilot: 8 gold clips without the owner's rough track (`c06b972`, `ml/gold/data/pilot_nolead`): 98 %
   of sure points within 12 px of gold.
5. Export (`export_train.py`, agree 30 px): tiers sure / track exported; check optional (`e070c78`).
6. Owner review of the check points (`798f502`; review parts `ml/gold/data/train1_review/p1` to
   `p4`): 2 832 confirmed, 55 rejected; tier "confirmed" (`a7cf93d`).
7. Training JSON with hard negatives: `train_labels_r9.py` (D14).
Work was done in snapshots (many "Training ball labels: snapshot" commits 2026-11-14/15, one after
a usage limit stopped the labelling agents, `551e49a`); 46 clips were ready for round 9 (`5ecbabe`),
all 171 by `61b97bf`.

**Shot gold** (2026-11-16): picked (`82889c6`), split frozen (`1a40b6a`); pre-labels by Modal job 12
(nets hr1, hrp1, hr2, hrp2 and OWLv2) planned; labelling with visibility levels and owner yes/no per
`tracking-strategie.md` section 9 step 0. Not done yet.

## 7. Things tried that did not help or were set aside

| What | When, where | Numbers | Reason set aside |
|---|---|---|---|
| Single-frame net | before 2026-11-04 | T1 6 % / 14 % | learned a fixed wall spot (Möhlin labels); three frames needed |
| Translation-only camera compensation | early (README "Findings") | static test separates balls (median 0.5) from fixed things (0.08) | breaks on zooming broadcast cameras; replaced by the local static test |
| Roboflow still frames (round 4) | PR #3 | T1 33 % -> 23 % top 1 | no motion in still frames; removed from the mix in round 6 |
| Rounds 5 and 5b | 2026-11-05 | no training step | DataLoader deadlock; fixed in round 6 with threads |
| More negatives of the same kind (round 7) | 2026-11-10 | no-ball >= 0.5: 43 % -> 54 % | false alarms not fixed by more of the same negatives |
| Pose hand filter / static filter against false peaks | 2026-11-10 `0c0c17e` (PR #35), `false_alarms.py` | 45 % of true balls within 15 px of a wrist (as many as false peaks); static filter removes 25 % of false peaks but 12 % of balls are static | poor ratio; the confusion is appearance (empty hand vs hand with ball) |
| Verifier v1 | 2026-11-10 `f1ba15d` | T2 top 1 +2 balls (p = 0.79) | no measurable gain; rejects 22 % of true balls; 47.5 % of balls not among the top 5 anyway |
| Verifier v2 (human hard peaks) | 2026-11-12 `4db309e` | tuning AUC +0.14, T2 top 1 +0.6 points (p = 1.00) | no measurable gain on T2; human crops add only about +0.02 AUC |
| Owner's 1 000 peaks alone (round 8) | 2026-11-12 `2706af2` | T2 35 % -> 33 % (p = 0.50) | main loss is recall, not false alarms |
| "Ball oder nicht? 3" labelling round | prepared 2026-11-12 `237bf02` | - | deprioritised by the tracking strategy (dense clip labels instead) |
| Owner's rough track as a label | 2026-11-12/13 | lags 1 to 2 frames | only a hint; later replaced by Claude's overview pass |
| Product balltrack as gold path | 2026-11-13 | 32.1 % vs net top 1 49.7 % | weaker than the net alone; replaced by tracker v2 in research |
| Court mask from the product calibration | 2026-11-15 (README round 10) | calibration finds the court in 8 of 42 gold clips; only 57 of 447 round-9 tracker misses (13 %, 28 in one clip) lie above all gold balls of their clip | too little to gain, calibration too rarely available |
| Tracker re-tuning (round 9; per net) | 2026-11-14/15; 2026-11-16 | 74.4 -> 75.1 % (hrp1), 74.2 -> 74.4 % (hr1) | defaults are robust |
| Round 10 as third ensemble net | 2026-11-16 | 77.0 % -> 75.6 % | makes the ensemble worse |
| Wider hit radius | 2026-11-16 `75bd04d` | hr1 + hrp1 all / fast: 12 px 78.2 / 79.5, 16 px 78.8 / 80.1, 20 px 79.2 / 80.5, 25 px 79.6 / 81.0 | changes little after the repeated-frame fix; 12 px stays |
| Larger fast gap or gap in seconds | 2026-11-16 `46331ba` | "change nothing" | kept `gap_fast` 4 |
| Two repeats in a row (`dup_max` > 1) | 2026-11-16 `5a4e944` | "change little" | kept 1 |
| Rescoring on round 10 candidates | 2026-11-16 `46331ba` | 75.5 -> 75.8 % (p 0.83) | rescoring calibrated on BallNet3 round-8 scores |

## 8. Metrics and protocol

**Hit:** a point within 12 px of the label in the 1280 px wide frame (T1 `bench_labelled.py`, T2
`bench_testset2.py` `R_HIT = 12`, gold `eval_ball.py --radius 12`). For a ball of 8 to 20 px.

**Test set 2 metrics** (frame level): top 1, top 5, score at the ball >= 0.3, no-ball frames with a
peak >= 0.5, and "found at FA x" (top peak on the ball and above the threshold at which x of the 72
no-ball frames alarm), because scores of different scorers live on different scales.

**Gold v1 metrics** (`ml/gold/eval_ball.py`): usable points = tiers owner, sure, track, confirmed with
a position; at most one method point per frame; subsets "free" and "held" (gold state) and "fast"
(the ball moves more than 12 px per frame to the nearest gold point at most 2 frames away); "out"
labels count as false positives when the method gives a point. Also reported per frame rate (50/60 fps).
Since 2026-11-16 the fast subset is the main measure (goal agreed with the owner: about 80 % overall
is enough if fast balls are right).

**Significance:** paired comparison on the same points: gained / lost counts with an exact sign test
(McNemar on T2). On gold the points cluster in 42 clips and are not independent, so **gold p values
are optimistic** (README round 9). Bootstrap over games was used only for the verifier v2 tuning AUC.
Since 2026-11-16 every gold result is reported with a 95 % interval from a bootstrap over clips
(2 000 resamples); the per-point sign test stays as a paired comparison but is not the evidence.

**Metrics agreed on 2026-11-16** (`docs/plans/tracking-strategie.md` section 9, apply to every
evaluation from now on):
1. Recall, precision and F1 at 12 px, plus 25 px; for all, fast and held balls. Today the tracker
   almost always outputs a point (recall = precision) and never says "don't know".
2. A confidence per tracker point and a precision-recall curve; additionally report recall at 95 %
   precision.
3. Frames without a ball are labelled too, with a visibility level (visible, partly occluded, fully
   occluded, outside the picture). Gold v1 has only 14 such frames.
4. Per shot: share of shots whose flight from release to goal or goalkeeper is tracked without a
   break; error at the release and at the target point; switches to another object per shot.

**Protocol rules** (same section): gold is not used for fitting (at most with cross-validation over
clips); learning happens on the training clips. Shot results from halls that appear in training are
somewhat easier than gold v1 and must say so. The shot gold "test" split is used once at the end.
GPU first on Kaggle, Modal only with the owner's approval.

## 9. Timeline

Dates are commit dates (UTC); PR #3 commits are author dates on GitHub.

- 2026-11-04 (PR #3): ball detector experiments with TeamTrack (`03cc835`), ball path and possession
  in the product (`55ee786`, `af17912`), three-frame tooling (`f0b431e`), labelling pages and user
  benchmark (`3445e43`), Roboflow tiles (`6da0bb1`), GPU augmentation and Kaggle self-training
  (`77b0fd6`), rounds 2 and 3 on the test half (`0489eab`), holder classifier work (`2c4e95f`).
- 2026-11-05 (PR #3): OWLv2 pseudo-label kernel (`622ee22`), OWLv2 beats the net on the test half
  50 % vs 29 % (`3c96676`), round 5 kernel (`2713226`, `8e2fd96`); PR #3 squash-merged (`7581b26`)
  with round 4 in the README.
- 2026-11-05/06: Modal OWLv2 job 2, 189 of 300 segments (`67d5d94`).
- 2026-11-09: round 6 kernel (`7c943d0`); round 6 result and handover (`00ca931`); test set 2 picks and
  page (`be3b2ec`, `206ec85`, `c91e955`); test set 2 result, round 6 29 % vs round 3 15 % (`db692b4`);
  OWLv2 for round 7 on Kaggle (`8563763`); round 7 recipe (`2c22c4d`).
- 2026-11-10: round 7 result 35 % (`89e6e9c`); false-alarm analysis (`0c0c17e`); verifier v1, no gain
  (`f1ba15d`); hard-negative labelling page (`a9e95f0`, `b5761ad`).
- 2026-11-12: round 8 recipe (`4ee62d3`); verifier v2, no gain (`4db309e`); labelling round 3 tooling
  (`237bf02`); round 8 result, no gain (`2706af2`); tracking strategy draft and the owner's decisions
  (`a3304ac`, `bc9aad2`); state-of-the-art review (`498a845`); phase 0 measurement plan (`050b85a`);
  gold standard phase 0 (`a0e3b6d`); follow mode (`abde5e2`).
- 2026-11-13: precision mode (`3b943d1`); contact sheets (`321f663`); rough-track mode (`33ded04`);
  gold labels v1 (`68876f3`); training clips v1 (`b47dc04`); second pass (`4ff4b47`, `ce559d7`); tier
  track (`bb3af78`); owner review, 1 555 points (`9a5ac20`); tracker v2 69 % vs 32 % (`198fcc7`);
  suggestions v2 (`2b7341a`); overview pass (`72bbe96`); `--only-rough` (`7556a55`).
- 2026-11-14: pilot without rough track (`c06b972`); training export (`e070c78`); owner review in the
  export (`798f502`); round 9 recipe and labels (`bcad5f7`, `5ecbabe`); round 9 result, tracker 71.3 %
  (`0d6734a`); basketball game excluded (`aae1fb8`).
- 2026-11-15: all 171 training clips labelled (`61b97bf`); round 10 recipe with the owner's review
  (`a7cf93d`, `39351d8`); BallHR (`c8b247f`); BallHRP (`0eb79f0`); round 10 result, top 1 56.5 %,
  tracker 73.4 % (`58337e5`).
- 2026-11-16: hr1 / hrp1 results and ensemble 77.0 %, hr2 recipe (`f98b29f`); repeated-frame step,
  78.2 % (`5a4e944`); 2 gold points rejected, radius note (`75bd04d`); shot gold, 61 shots (`82889c6`);
  fast-ball gaps and learned rescoring, 84.0 % / fast 86.0 % (`46331ba`); ball roadmap with metrics
  (`4f7d591`); frozen final-test split of shot gold (`1a40b6a`); this lineage file.

## 10. Current state, open questions, next steps

**State 2026-11-16.** Best research path: candidates of hr1 + hrp1 (merged) plus OWLv2, tracker v2 with
repeated-frame step, fast-ball gaps and learned rescoring: gold v1 84.0 % all [78.7, 88.7], 86.0 % fast
[77.2, 93.0] (12 px, 95 % clip bootstrap); without OWLv2 78.6 % / 81.8 %. Gold v1 is a development set.
Product: YOLOX-S "sports ball" plus `handball_vision.balltrack`, not measured on gold with its own
detector. Target agreed with the owner: 85 to 90 % for fast balls and shots; 95 % is not a target.

**Open questions and caveats** (for any paper, these must be resolved or stated):
- Gold v1 has been used for tracker development; a clean final number needs the frozen shot gold test
  split (20 shots, 4 halls) or a new untouched gold set.
- hr2 and hrp2 were trained but no result is in the repo.
- Every net from round 3 on, including hr1 and hrp1, was trained with DeepSport (CC BY-NC-SA): not
  shippable as is. A product net needs a retrain without DeepSport (and a check of the ImageNet
  `hrnet_w18` weight licence).
- Significance on clustered points: clip bootstrap done (section 5); differences under about 4 points
  are not resolvable on gold v1.
- OWLv2 adds about 5 points but cannot run in the product; the shippable path is net only.
- Gold labels favour frames a detector already found (section 6), so "no detector sees the ball" is a
  lower bound and recall is probably optimistic; a blind labelling check is planned (section 11).
- The frozen shot test (20 shots, 4 halls) is too small to resolve anything (17 of 20 is compatible with
  62 % to 97 %); to be replaced by at least 100 shots from at least 15 never-trained halls.
- Unverified items listed inline above (round 1 to 4 details, round 6 segment count, Roboflow in hr
  data, dense-pass threshold, small "before" differences in the tracker tables, 15 unaccounted
  training check points, whether the latest numbers use 1 553 or 1 555 gold points).

**Next steps**: adjusted after review 1 (section 11); the binding plan is
`docs/plans/tracking-strategie.md` section 9. Prioritised on 2026-11-16 (now: shot end test of at least 100 shots
labelled without candidate rings, shippable tracker without OWLv2 as the headline, confidence and
"don't know"; then nets without DeepSport in 2 folds; parked or dropped: OWLv2 in the product, a
separate DeepSport ablation, further gold v1 tuning, TOTNet until the end test can resolve 2 points). Before the adjustment: step 0 shot gold labels with visibility
levels and pre-labels from Modal job 12; step 1 tracker confidence per point (metric 2), more "ball
among candidates, wrong choice" cases, retrain rescoring for each net generation; step 2 targeted data
(ensemble over training clips, label where unsure: shots, hard passes, high balls in front of a wall
such as g34, videos with repeated frames, new halls); step 3 net generation 2 with TOTNet ideas
(arXiv 2508.09650, MIT: 5 input frames, 3D convolutions, synthetic occlusions, visibility-weighted
loss) in a fair comparison on the same data, then retrain the rescoring; step 4 interim verdict on
gold v1 and shot gold with all metrics; step 5 nets and tracker into the product with tests when shots
reach about 85 %.

## 11. Reviews and objections

Every review of the approach is recorded here with a verdict per objection (justified, partly
justified, rejected), the evidence and the action. A reviewer should be able to work from this file
alone; whatever a review had to infer because it was missing here is added to the sections above.

### Review 1 (2026-11-16, independent read of this file, the strategy, the state-of-the-art report
and the tracker and evaluation code; gold recomputed by the reviewer)

**Good, per the review:**
- The strategy change of 2026-11-12, from more rounds to dense clip labels and a gold standard.
- Data shown as the lever, through round 10 and the HRNet comparison on equal data.
- The label pipeline: LLM pre-label plus owner yes/no, about 98 % confirmed.
- The measuring discipline: separate halls, paired comparisons, failures documented, unverified
  items marked.
- The tracker work: the repeated-frame fix comes from a cause, and the rescoring was learned out of
  sample.

| # | Objection | Verdict | Evidence | Action |
|---|---|---|---|---|
| 1 | Gold v1 is thin and clustered: 1 553 of 11 752 frames labelled, 10 clips hold 47 % of the points, 5 clips 45 % of the fast ones | justified | clip bootstrap: +-5 points overall, +-8 fast (section 5) | intervals with every result; no decisions on differences under about 4 points |
| 2 | Headline uncertainty about +-4 points | justified (it is about +-5 / +-8) | section 5 | as 1 |
| 3 | Gold labels depend on the detectors: points mostly where a candidate was on the ball, many rows left open; "no detector" is a lower bound | justified, now shown on gold v1 itself, not only the pilot | section 6: 80 % / 66 % of given points are candidates, about half the rows open | blind check: label 5 gold clips without candidate rings and compare; shot gold labelled with visibility levels and a no-ball answer per row |
| 4 | Precision unknown: the tracker almost always outputs a point, 87 % of frames unjudged | justified | recall = precision = 84.0 % (section 8, metric 1); only 14 no-ball labels | confidence per point and a "don't know" output (metric 2); no-ball frames labelled in shot gold. Done 2026-11-16 (section 5): 90 % precision held out at 61 % recall, 95 % at 41 %; precision on no-ball frames still not measurable (14 frames) |
| 5 | DeepSport (non-commercial) in every net since round 3, its benefit never measured | justified | section 2 D5 | next net generation trained without DeepSport, with one comparison run with it |
| 6 | OWLv2 carries the largest rescoring weight, no ablation and no runtime in the log | justified; the "2 min per frame on CPU" in this file was wrong (about 1.4 s per frame on a T4) | ablation in section 5: -5.4 points overall, -4.2 fast; cost in section 4 | rescoring retrained without OWLv2; the net has to close the gap; OWLv2 stays a labelling tool. Done 2026-11-16 (section 5): shippable tracker 80.0 % [74.7, 84.9] all, 83.3 % [75.2, 90.1] fast; gap to OWLv2 now 4 / 2.7 points |
| 7 | Calibration finds the court in only 8 of 42 gold clips, a bigger blocker for tactics board and shot zones than the ball | justified (outside the ball work) | section 7 (court mask row) | owner to prioritise as its own track |
| 8 | Shot test too small (20 shots, 4 halls); 46 of 61 shot clips are 50/60 fps, where the tracker is weaker | justified | `ml/gold/shot_clips.json`: fps 60 x 36, 50 x 10, 30 x 15 | the 61 logged shots become a development set; new frozen test of at least 100 shots from at least 15 never-trained halls (gold and test set 2 halls), found by viewing, not by a detector |
| 9 | Players are ignored by the tracker although 78 % of the balls lie in a player box | justified (number from the reviewer, not rechecked here) | - | player boxes as tracker evidence, after metric 2 |
| 10 | Rescoring for the HRNet nets needs candidates from nets that never saw the clips (fold training) | justified | section 5: the rescoring is calibrated on round-8 scores | next GPU runs as 2 folds over the training clips; the fold nets also form an ensemble |
| 11 | Hall variety: the training clips come from 57 of 226 games | justified | section 2 | targeted data from new halls (step 2) |
| 12 | Net generation 2 (TOTNet) only after the above: the tracker errs more often (8.5 %) than the detectors miss (5.4 %), and gold v1 cannot resolve a 2-point architecture gain | partly justified: the order is right; the GPU week is still used, for the runs that answer questions (no DeepSport, folds) | sections 5 and 10 | TOTNet after the shot test is large enough |
| 13 | Smaller items: hr2 and hrp2 not measured; 561 vs 738 fast points; eight days on the small net; basketball in rounds 8 and 9 | justified; 561 vs 738 fixed (section 3, 738 is the evaluated count) | sections 3, 4 | hr2 and hrp2 measured on 2026-11-16 (CPU kernels) |
