# 027. Shirt numbers read once, players recognised by appearance

- Status: accepted (numbers), proposed (re-identification, licence open: Q-ML-5)
- Date: 2026-11-04
- Implements BRIEF 7.2 stage 6; builds on ADR 025

## Context
Per-player figures need identities. The tracker loses players in crowds and on camera pans: a
5-minute clip gives 120 to 200 track pieces for about 16 people. A shirt number is readable on
about one crop in ten (back to the camera, sharp, unoccluded), so reading it on every piece is
impossible; but it only has to be read once per player, after that the player is recognised.
Tesseract read none of the numbers on 720p footage.

## Decision
1. **Reading** (`numbers.py`): PP-OCRv4 detection and recognition (Apache-2.0, ONNX, from the
   pinned `rapidocr_onnxruntime` wheel; ml/models/ppocr-v4.md) on the upper body of players at least
   80 px tall, sharp, inside the frame, green channel, enlarged three times. Every 6th frame on CPU,
   every detection frame on the GPU image.
2. **Per track**: confident readings (0.8 or more) are voted; a number needs 70 % of them and at
   least three readings (two only when both are very sure and alone). Where a track reads one number
   for a while and then another, it is cut there (the tracker swapped two players). Fragments of one
   team with the same number that do not overlap in time become one player (goalkeeper and field
   labels included: the number is the better witness).
3. **Recognising** (`reid.py`): an appearance network gives one vector per player and second; the
   tracks with a well-read number (at least four readings) teach, per match and team, a projection
   (PCA + LDA) that separates today's players. Every track without a number goes to the nearest
   player when clearly nearer than the second, the player is not on court elsewhere at that time,
   and the distances before and after can be run. Unsure stays unknown.
4. **In the API**: own players (home kit) with a number are linked to the roster entry with that
   shirt number; manual assignments still win and survive re-runs.

## Results (NLB 2017 clip, 5 minutes)
| | numbered player time |
|---|---|
| numbers read every 15th frame | 12 % |
| read on every detection frame, vote, split and join | 22 % (1716 s) |
| plus recognition by appearance | 30 % (2375 s) |

Hidden-number test (12 numbered players, 15-second pieces): 65 % assigned, 70 to 75 % of those
right. The remaining error source is a wrong anchor: a junk track (referee and spectators) with a
misread number attracts others.

## Consequences
- Numbers and the vote ship now; re-identification ships when Q-ML-5 is answered (the code path is
  in place and skipped without a model).
- CPU cost: reading numbers adds about 0.5 x video length at every 6th frame; the appearance
  network about 2 x on CPU, a few percent on a GPU. The GPU image is the production path.
- Next: reject anchors whose own appearance is inconsistent (junk tracks), and use the numbers'
  vote across tracks to repair the tracker earlier (association with appearance during tracking).

## Addendum (2026-11-05): the team of a number, no guessed referee kit, players-only ReID
Measured on four SG Wädenswil/Horgen NLB stream segments (Emmen, Arbon, Gossau, Baden-Endingen,
5 min each, cached observations of the worker's CPU path) against the official match sheets.
The digits were mostly read right; the loss was the team: a track carried a white home player and
a black opponent in turn (the tracker swaps them in crowds), so the opponent's number counted for
the home team; bench, staff, referees and goalkeepers with a number taught ReID.

1. **Team of a number from the shirt it was read on** (`pipeline.split_by_reading_colour`,
   `teams.team_centres / side_of / colour_runs`). Every confident reading gets the team of the
   torso colour sampled on the same crop, against this match's two team colours (2-means over the
   field tracks' single looks, started at the teams' track medians: a dim hall shows white shirts
   grey, Emmen L 60 to 70). A field track with two or more readings on the other team's shirt is
   cut at its colour switches (single looks smoothed over 1 s, stretches under 1 s ignored), each
   piece taking the team of its colour; then every reading that still disagrees with its track's
   team is dropped. Goalkeeper and referee tracks are left alone. Without two clearly different
   team colours nothing changes.
2. **No guessed referee kit.** The API sent `#1a1a1a` for the referee in every job; the referees of
   all four games wore yellow or orange, and a black "referee" kit next to black opponents splits
   the opponents between two labels. The match now has an optional `kit_referee` (user choice,
   migration 0030); the job carries it only when it is set and at least delta E 25 from both field
   kits (`core.colors.analysis_kits`), else referees come from the role classifier and the
   colour clusters. `roles.apply_roles` keeps its colour gap: it is what stops dark-kit players
   from being taken for referees; a referee in a team's colour is therefore not relabelled, and
   step 3 keeps such a track out of ReID instead.
3. **Players-only ReID** (`reid.plays`, `reid.fragment_roles`). A fragment teaches or gets a number
   only when it is labelled a field player and the role classifier, averaged over its looks (for a
   numbered fragment the looks within 2 s of its readings), gives "player" at least 0.75.

| game | step | read numbers on the sheet (tracks, time) | incl. appearance | numbered player time read / +appearance | active players found home / away | with roster | ReID hidden-number test right / wrong / none |
|---|---|---|---|---|---|---|---|
| Emmen | before | 9/17 (70 %) | 14/23 (72 %) | 31 / 37 % | 4/12, 5/15 | 11/14 (93 %) | 31 / 12 / 7 |
| | 1 | 9/14 (79 %) | 17/22 (82 %) | 30 / 35 % | 4/12, 5/15 | 11/13 (94 %) | 29 / 5 / 17 |
| | 1+2 | 9/14 (80 %) | 23/30 (82 %) | 26 / 34 % | 4/12, 5/15 | 11/13 (98 %) | 32 / 3 / 14 |
| | 1+2+3 | 9/14 (80 %) | 18/23 (83 %) | 26 / 32 % | 4/12, 5/15 | 11/13 (98 %) | 26 / 0 / 23 |
| Arbon | before | 14/18 (80 %) | 20/28 (76 %) | 38 / 48 % | 8/13, 4/11 | 15/17 (95 %) | 55 / 11 / 8 |
| | 1 | 14/15 (99 %) | 30/35 (90 %) | 27 / 44 % | 8/13, 4/11 | 14/15 (99 %) | 51 / 7 / 9 |
| | 1+2 | 14/15 (99 %) | 29/35 (92 %) | 23 / 41 % | 8/13, 4/11 | 14/15 (99 %) | 38 / 8 / 11 |
| | 1+2+3 | 14/15 (99 %) | 29/35 (92 %) | 23 / 39 % | 8/13, 4/11 | 14/15 (99 %) | 34 / 8 / 15 |
| Gossau | before | 15/22 (81 %) | 31/49 (78 %) | 32 / 48 % | 8/12, 5/12 | 17/17 (100 %) | 38 / 15 / 23 |
| | 1 | 14/20 (92 %) | 35/58 (79 %) | 28 / 44 % | 8/12, 5/12 | 15/15 (100 %) | 45 / 14 / 18 |
| | 1+2 | 14/21 (87 %) | 40/58 (77 %) | 29 / 49 % | 8/12, 5/12 | 15/16 (97 %) | 42 / 13 / 25 |
| | 1+2+3 | 14/21 (87 %) | 31/42 (82 %) | 29 / 40 % | 8/12, 5/12 | 15/16 (97 %) | 29 / 9 / 42 |
| Baden-Endingen | before | 11/12 (95 %) | 19/23 (88 %) | 26 / 41 % | 6/11, 4/15 | 12/13 (96 %) | 9 / 4 / 10 |
| | 1 | 11/12 (95 %) | 18/22 (88 %) | 27 / 41 % | 6/11, 4/15 | 12/13 (96 %) | 8 / 4 / 12 |
| | 1+2 | 11/12 (97 %) | 13/19 (87 %) | 34 / 41 % | 6/11, 4/15 | 12/13 (98 %) | 17 / 8 / 5 |
| | 1+2+3 | 11/12 (97 %) | 13/19 (87 %) | 34 / 41 % | 6/11, 4/15 | 12/13 (98 %) | 12 / 5 / 13 |

"On the sheet" counts a track as right when its number is on its team's official list; the
percentage weights by track time. Hidden-number test: numbered tracks cut into 10 s pieces, each
piece in turn loses its number and readings and must be found again (pieces differ per step
because the numbered tracks do).

- Step 1 removes the black-shirt numbers from the home team: Arbon's wrong home numbers 7, 8, 28
  -> 28, Emmen's 5, 6, 14, 19 -> 5, 8. The numbered time drops (Arbon 38 -> 27 %) because time a
  numbered track spent on the other team's player no longer counts; correct numbered minutes
  stay about the same (Arbon 11.6 -> 10.1 read, 13.8 -> 14.9 with appearance; Emmen 6.8 -> 7.3).
  ReID wrong answers fall (Emmen 12 -> 5, Arbon 11 -> 7). Remaining wrong numbers are misread
  digits on the right shirt (Gossau 69, 93, 15 on white shirts), which the roster fixes.
- Step 2 is right in principle (no game had a black referee) but moves the numbers both ways:
  the tracker uses the per-detection colour label, so its tracks change (Arbon's #4 track
  breaks into pieces that fall below the 70 % vote); the share of player time also grows because
  short black tracks are no longer called referees.
- Step 3 trades recall for precision: hidden-number wrong answers 32 -> 22 over the four games,
  right ones 129 -> 101. Filtering only the anchors (not the candidates) kept 112 right but had 33
  wrong: the dirty anchors are mostly numbers that are not on the sheet anyway; the candidates
  (referee and staff stretches that look like a player) are where the filter helps.
- Still open: the tracker swaps players of different teams (step 1 repairs the numbered tracks
  only); recall of active players is unchanged (4 to 8 of 11 to 15 per team); the role threshold
  (0.75) and the colour-run length are set on these four games only; the web form has no field for
  the referee kit yet.

## Addendum (2026-11-09): measured broadly, role threshold 0.45
Twelve uploaded games of season 2023/24 and later with an official player list on both sides,
from at least eleven halls and six producers (wackerTV, a private stream, Handball Nordwest, the
HSG Leimental camera at home and in three away halls, SG Wädenswil/Horgen, handball.ch), one 3-minute
segment each (the second of five), observed like the GPU image (yolox_s every 3rd frame, numbers
on every detection frame, ReID and roles every 30th) on the 1280 px / 25 fps proxy.

**Court.** The worker's automatic court was accepted on 6 of 13 segments and wrong on one of
those (Switzerland - Romania men: goal fit 0.22, court rotated; that game is also left out
because the official data has no Romanian player list). Where it failed, the court comes from
the clicked-court-free path of the first addendum's measurement: floor plane and camera height
from the markings and the people, the court laid on the players' feet and now scaled so that
their 2nd to 98th percentile spans 38 m ("rough", 3 games: one implausible automatic court, one
flat view, one goal fit too weak). On the four TV-style views with cuts and zoom (no floor:
22 to 32 % of the marking length on the floor directions) the floor itself is wrong (the rough
court came out 70 to 180 m long), so the feet box on the panorama is stretched onto the court
without perspective ("feet box"); good enough to follow players and drop the stands, not for
positions. Kits: the colours as seen in the video; which one is home was decided by the
readings against both lists (in one game the guess from the club names was wrong: ATV/KV Basel
played at home in yellow).

| game (producer) | court | half | read numbers on the sheet (tracks, time) | incl. appearance (0.75 / 0.45) | numbered player time read / +appearance (0.75 / 0.45) | active players found home, away | wrong-team numbers (tracks, time) | bench, staff, referee numbers (by eye) |
|---|---|---|---|---|---|---|---|---|
| RTV Basel - Kadetten (cup, wackerTV) | feet box | tune | 16/18 (93%) | 33/38 (92%) / 36/41 (91%) | 35% / 54% / 61% | 7/13, 7/14 | 0 (0%) | 2 bench (42 s, 7 %); 1 half staff |
| Kadetten - Kriens-Luzern (Supercup, wackerTV) | feet box | check | 13/14 (96%) | 14/17 (94%) / 16/19 (94%) | 51% / 55% / 58% | 6/12, 7/13 | 0 (0%) | 0 |
| Brühl - LK Zug (women's cup, wackerTV) | feet box | tune | 6/7 (92%) | 12/13 (94%) / 12/13 (94%) | 14% / 20% / 20% | 0/9, 6/13 | 1 (8%) | 0 |
| Uster - Seen Tigers (cup, private stream) | auto | check | 6/8 (95%) | 15/17 (96%) / 15/17 (96%) | 23% / 32% / 32% | 6/13, 0/14 | 0 (0%) | 0 |
| ATV/KV Basel - Yellow 2 (F1, Handball Nordwest) | auto | tune | 8/9 (96%) | 18/23 (89%) / 18/24 (88%) | 17% / 35% / 36% | 5/14, 3/14 | 1 (4%) | 0 |
| Leimental - Stans (SPL2, club stream) | auto | check | 9/9 (100%) | 18/18 (100%) / 19/19 (100%) | 20% / 33% / 33% | 6/13, 2/14 | 0 (0%) | 1 bench (4 s, 1 %) |
| Spono II - Leimental (SPL2, away) | rough | tune | 7/7 (100%) | 15/15 (100%) / 17/17 (100%) | 9% / 18% / 25% | 3/14, 3/12 | 0 (0%) | 0 |
| LK Zug II - Leimental (SPL2, away) | auto | check | 11/12 (94%) | 17/18 (95%) / 19/20 (96%) | 37% / 45% / 48% | 6/11, 5/12 | 0 (0%) | 0 |
| Wädenswil/Horgen - RTV (NLB, club stream) | auto | tune | 12/18 (78%) | 19/27 (80%) / 19/25 (84%) | 30% / 41% / 40% | 4/12, 7/11 | 3 (2%) | 0; 1 part referee (off the sheet) |
| Switzerland - Iceland women (handball.ch) | feet box | check | 5/7 (89%) | 7/10 (88%) / 7/10 (88%) | 35% / 42% / 42% | 2/11, 3/13 | 0 (0%) | 1 referee, 1 staff (167 s, 51 %) |
| Leimental - Vaud La Côte (U15, club stream) | rough | tune | 6/6 (100%) | 6/6 (100%) / 8/8 (100%) | 17% / 17% / 18% | 4/14, 2/7 | 0 (0%) | 0 |
| Arbon - Leimental (SPL2, away) | rough | check | 7/8 (96%) | 17/18 (97%) / 17/18 (97%) | 23% / 32% / 32% | 3/11, 4/13 | 1 (4%) | 0 |

"Wrong-team" counts a numbered track whose number is not on its team's list but on the other
team's. "By eye": contact sheets of every read-number track (8 crops), a track counted when most
of its crops show a bench player, a coach or a referee. With the teams' lists as rosters only
listed numbers are kept, so that column is 100 % by construction and left out.

- Over the twelve games: 94 % of the read-number track time is on the sheet (106 of 123
  tracks), 25 % of the player time carries a read number, 35 % with appearance (37 % at 0.45);
  101 of 297 active players are found. The four games of the first addendum (80 to 99 %) were
  the hard end: the dim Wädenswil/Horgen hall is again the weakest here (78 %, black players
  labelled home in crowds, where the per-reading colour cuts only some of them).
- Wrong-team numbers are rare now (6 tracks, 2 to 8 % of the numbered time where they occur).
  Team-label errors whose number is on both lists stay invisible to this count (seen on the
  sheets: a Stans player as home #15, RTV players as home #23).
- Bench, staff and referees: 5 of 123 numbered tracks, but in the handball.ch national-team
  stream the referee (light green shirt, read #36) and a coach on the touchline (#8) hold half
  the numbered time, both with numbers that are on the sheet. The role classifier did not catch
  them (player 0.63 and 0.55), so "on the sheet" overstates that game; the TV stream shows the
  touchline more than club cameras do.
- Where few numbers are read the cause is the footage, not the vote: TV close-ups and cuts
  (Brühl - Zug: the panorama falls apart, 14 %), black shirts with yellow numbers (Seen Tigers:
  no away number at all), green shirts with white numbers (Brühl: none), far club cameras
  (Spono: 9 %).

**Thresholds**, tuned on the six "tune" games (correct minus twice wrong numbered seconds; for
ReID also the hidden-number test of the first addendum), checked on the six "check" games:

| setting | tune: right / wrong s (read) | check | decision |
|---|---|---|---|
| colour ratio `SIDE_RATIO` 0.5 / **0.6** / 0.7 / 0.8 | 1788/158, **1789/158**, 1762/158, 1787/158 | 2512/124, **2446/124**, 2446/124, 2446/124 | keep 0.6 |
| colour stretch `min_run_s` 0.5 / **1** / 2 / 3 s | 1788/158, **1789/158**, 1788/163, 1790/160 | 2426/124, **2446/124**, 2470/128, 2502/128 | keep 1 s |
| role `MIN_PLAYER_P` 0 / 0.3 / 0.45 / 0.6 / **0.75** / 0.9, incl. appearance | 3068/296, 2950/296, 2951/296, 2863/282, **2745/289**, 2447/195 | 3255/160, 3258/160, 3250/153, 3246/153, **3162/153**, 3010/154 | **0.45** |
| same, hidden-number test right / wrong / none | 143/32/33, 132/31/45, 130/28/50, 119/27/62, **107/23/78**, 77/23/108 | 209/27/38, 201/28/45, 200/29/45, 193/31/50, **183/30/61**, 163/27/84 | |

The two colour settings change almost nothing on any game (a track or two moves; 0.5 gains on
the check half only), so they stay. The role threshold of 0.75 rejected many real players: on the tune half every lower value
finds more numbers with about as many wrong, 0 (no role check) scores best and 0.45 is within a
few seconds of it. 0.45 is taken rather than 0 because it keeps the check for what the classifier
clearly calls a referee or goalkeeper (the sheets show such tracks); on the check half it gives
88 more correct numbered seconds than 0.75 at the same wrong time, and 200 instead of 183 right
hidden numbers with 29 instead of 30 wrong. `reid.MIN_PLAYER_P` is now 0.45.

Still open: the court on TV-style streams (no floor model holds across cuts; a clicked court per
hall would), bench and staff tracks that look like players to the classifier (a touchline check
needs the court), and recall: a third of the active players get a number in three minutes.
