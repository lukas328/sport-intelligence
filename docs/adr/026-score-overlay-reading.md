# 026. Goals and match clock from the broadcast score overlay

- Status: accepted
- Date: 2026-11-04
- Implements BRIEF 7.2 stage 10 (source `scoreboard_ocr`); complements ADR 025

## Context
On the real clips, the throw-off heuristic (all players in their own half, one at the centre)
found **no goal at all**: 0 of 5 on the SPL2 2024 clip. Amateur teams restart quickly after a goal,
and a panning camera rarely shows both halves at the throw-off. The ball is found in only 1 to 5 %
of frames by the COCO detector, so it cannot carry goal detection either.

League streams (here SPL2, 2024) burn a score bug into the picture: team abbreviations, score and
a running match clock. That is the most reliable goal source available without a goal camera.

## Decision
1. `handball_vision.scoreboard` reads the overlay with **Tesseract 5** (Apache-2.0), installed as a
   Debian/Ubuntu package in both GPU worker images. No model to train, no weights to ship.
2. **Finding it:** on 36 frames spread over the video, overlay pixels stay the same while the panning
   camera changes everything else; stable, textured blobs in the top or bottom quarter are the
   candidates. Videos from a fixed camera (most of the frame is stable) are skipped.
3. **Fields:** Tesseract word boxes on a few crops (read as is and inverted, since overlays mix
   light and dark text): `2:1` is a score, `03:34` a clock; a "clock" that does not move is a score.
4. **Reading** happens in the same decoding pass as the detector (`observe(on_frame=...)`). The score
   field is read when its pixels change (otherwise every 15 s), the clock every 15 s: about
   100 calls per 5 minutes, a few seconds per hour of video.
5. **Cleaning:** a score counts once it is read twice in a row and may add one goal; a bigger jump
   (overlay hidden) must hold for six readings and adds at most three. A goal is placed at the first
   reading of the new score (a few seconds after the actual goal, the operator's delay).
6. **In the API** (`auto_events.apply_scoreboard`): the overlay's left team is the home team, so
   `Match.is_home` decides own and opponent. Goals become `shot`/`goal` events with source
   `scoreboard_ocr` and confidence 0.95, with period and match clock from the overlay clock. A goal
   tagged by hand within 20 s on the same side wins. When the overlay gave goals, the throw-off
   heuristic adds none. Each goal moves to the end of the scoring side's attack that ended up to
   15 s before the overlay changed (the operator's delay), and that attack is marked as a goal: the
   goal clip shows the finish. The overlay clock sets throw-off times nobody set (negative when the
   video starts after the throw-off), and the final score when the video reaches the end of the
   match and no result is stored.

7. **Scorer** (added 2026-11-04): after a goal the stream shows a name banner in the overlay colour
   ("7 Lisa ZIMMERLI"), left for the home team, right for the away team. The reader finds wide bars
   of that colour outside the score bug, reads them a few times, and votes the number per name over
   the match (OCR reads 11 as 44 now and then). Each goal gets the first banner on its side within
   20 s. Own scorers are linked to the roster by shirt number.
8. **Where from** (`shots.py`): the scorer's track (shirt number from `numbers.py`/`reid.py`), or
   else the attacker nearest to the attacked goal in the 10 s before the overlay changed, gives the
   shot position (normalised, attacked goal at x = 40) and the throw time; the goal event carries
   both and `position_source` (`number` or `nearest`).

## Results (5-minute clips)
| Clip | Overlay | Goals read | Actual | Clock |
|---|---|---|---|---|
| SPL2 Leimental vs Arbon 2024 | yes | 5 (1:1, 2:1, 2:2, 2:3, 3:3) | 5 | runs from 02:00 |
| NLB Horgen vs Stäfa 2017 | none | 0 | not checked | - |
| NLB Horgen vs Möhlin 2017 | none | 0 | not checked | - |

Single misreadings (`41:0`, `2:7`) occur and are filtered by rule 5.

Scorers on the SPL2 clip: all 5 banners read and attached to the right goals (7 Amy HOCHREUTENER,
7 Lisa ZIMMERLI, 5 Zerin OZCELIK, 11 Sophie WINDLER, 33 Denise SCHWAIGER); a sixth banner after the
last overlay change was corrected from 44 to 11 by the name vote. Shot positions: 1 of 5 from the
scorer's own track (numbers read only every 15th frame on that run), 4 from the nearest attacker,
all 3 to 6 m from the goal.

Cross-check with the tracking: before each of the 5 goals, the possession segmentation (ADR 025)
had the scoring team attacking (5 of 5); the attack ended 1 to 3 s before the overlay changed.

## Consequences
- Recordings without an overlay (club cameras, the 2017 clips) still have no automatic goals. The
  sources there stay courtside marks, the paper match report and the official match feed.
- The hall's own scoreboard (on the wall, moving with the camera) is not read yet.
- Tesseract is a system binary: without it (local dev without the package) the step is skipped.
