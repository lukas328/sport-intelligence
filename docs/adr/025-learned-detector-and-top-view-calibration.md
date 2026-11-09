# 025. Learned person detector, single observation pass, automatic calibration via a top view

- Status: accepted
- Date: 2026-11-04
- Updates ADR 012 (detector default), ADR 020 (calibration of moving cameras no longer needs
  clicked points in the common case)

## Context
On the three real clips (NLB men 2017 x2, SPL2 women 2024; panning club and broadcast cameras in
multi-sport halls) the classical pipeline (ADR 012, 020) found the camera motion but neither people
reliably nor the court: automatic calibration failed or returned a wrong court on all three. Pretrained
weights were unreachable when ADR 012 was written; GitHub release assets are reachable now.

## Decision
1. **Detector: YOLOX-S COCO (Apache-2.0 code and weights)** via ONNX Runtime
   (`YoloxDetector`, model card `ml/models/yolox-coco.md`), weights baked into the GPU worker image
   at build time from the pinned GitHub release with a SHA-256 check (never in git). People in the
   whole frame; `filter_on_court` keeps feet on the court with a plausible box height and drops boxes
   cut by the frame edge. Without the weights file the classical path still runs.
2. **One decoding pass** (`observe.observe`): camera motion on every frame, detection on every 3rd,
   floor-marking segments every 90th, a small Lab sample of each torso. Stored as
   `analysis/observations.npz` next to `motion.npz`: a re-run with clicked points skips decoding and
   detection (seconds instead of minutes).
3. **Automatic calibration via a metric top view** (`topview.py`, `observe.auto_calibrate`):
   floor orientation from the two orthogonal marking directions (segments of many frames, walls and
   people masked, focal length from the camera motion); scale from person heights (1.75 m); a top
   view drawn from the aligned segments only; court template search (lines, players on the court,
   nobody behind the goal lines, goalkeepers in the goal mouths; six weightings in one pass); the
   candidates are refined on the goal frames (projected 3D posts and crossbar must fall on striped red
   and white paint) and the best goal fit wins. Court coordinates are normalised (camera on the near
   side y < 0, goal x = 0 on the camera's left). Plausibility: camera 1.5 to 25 m above the floor and
   outside the court, at least half of the people on the court, a minimum goal fit; otherwise
   `needs_calibration` and the dialog as before.
4. **Pose calibration from clicks**: with a known focal length only the camera pose is fitted
   (`calibrate_pose`); four goal-post feet are enough, crossbar points (`height_m = 2`) help.
5. **Tracking for panning cameras**: a track outside the current view waits (up to 90 s) instead of
   ageing and is matched again with a wider gate when the player comes back; a confident team label
   never jumps to the other team; stitching compares shirts by hue (video washes colours out) and the
   kit match uses hue for coloured kits and lightness for white, black and grey ones.

6. **Teams by this match's colours**: the tracks' median torso colours are clustered (3 to 5
   clusters, the pair with most players that is clearly apart and balanced are the teams) and matched
   to the entered kits by order (lighter to lighter, hue to hue); hall lighting shifts absolute
   colours too much. **Goalkeepers by position** (most of the time within 6.5 m of a goal) and by the
   team that defends that goal in set attacks.
7. **What video gives without the ball**: possession phases with a summary per side
   (`GET /matches/{id}/possessions`), fast breaks (the team runs 18 m towards the other goal within
   4 s of winning the ball), physical load per team and per track; the analysis tab shows them when no
   events were recorded, with the way to goals and shots (courtside marks, match sheet).
8. **Fallback**: when the detector finds fewer than three people in the median frame, the classical
   path runs (unusual footage; the synthetic test video).
9. **GPU image** (`Dockerfile.cuda`, CUDA 12.6, ONNX Runtime GPU, detection on every frame).

## Consequences
- All three real clips calibrate automatically (court about 0.5 to 1.5 m accurate judged by the
  goal frames and lines; docs/perf/real-videos.md). People per frame on the court: 13 to 15.
- CPU cost for 5 minutes of video on 4 cores: about 9 to 10 minutes (detection 4.5 to 6, camera
  motion 2.3, calibration 0.8 to 1.5). On a GPU the detection drops to well under a minute.
- The ball is not found by a COCO model; ball and shot events stay with tagging and imports.
- Track identities still fragment when players leave the view for long or cross each other; player
  identity needs shirt numbers (OCR) or manual assignment (existing UI).
- Goal detection assumes striped goal frames (red and white in all three halls); other colours lower
  the goal fit and send the match to the confirmation dialog.

## Addendum 2026-11-04: flat views and multi-sport floors
- Automatic calibration now stops within seconds when the camera sees the players less than 10
  degrees below the horizon (`MIN_VIEW_DEG`): low cameras (Veo at about 1.9 m) and corner positions
  in the stands make the top view unreliable, and a wrong court was accepted before (Cottbus). The
  working halls see the players 14 to 18 degrees below the horizon. Such videos go to the manual
  calibration (clicked points).
- When the search over all floor lines gives no trustworthy court, the court is searched again on
  the lines of the colours that best match the handball template (multi-sport floors). The working
  halls keep their calibrations exactly; on the real failing halls (Mülheim, Cottbus) it did not
  help yet.
- Open: a pose fit against the panorama in pixels for flat views; goal detection only knows red
  stripes (black-and-white goals are missed, red banners can fool it).

## Addendum 2026-11-05 (2): stream and amateur footage, a court once per hall
Measured on 39 games (backlog item 1), one 90 s piece per game (from 20 s into a segment, mostly
the first-half one; the worker's proxy: 1280 px, 25 fps; people every 12th frame, markings every
90th): 17 SG Wädenswil/Horgen (SGWH) stream games from handball-segs-b01..b03 and 22 games of the
owner's batches l01..l03 (HLA TV, cup finals, 1. and 2. Liga, women's amateur recordings). Every
court was checked by eye on a contact sheet with the court and the goal frames drawn on the hall
image (`<scratch>/calib2/`, local only).

| result (39 games) | before | after |
|---|---|---|
| court found, right by eye (goal frames on the goals, lines on lines) | 5 | 7 |
| court found, wrong (accepted by the checks) | 2 | 2 |
| no clear floor (`no_floor`) | 23 | 20 |
| court not trustworthy (`court`) | 5 | 6 |
| flat view (`flat_view`) | 4 | 1 |
| camera motion lost (`camera_motion`) | - | 3 |

Right before and after: 1. Liga Stäfa, 2. Liga Zofingen (2 halls), Aufstieg Schwamendingen, SGWH
- Yellow/Pfadi. New: Cup Kriens - Yverdon (fixed camera, focal 0.65 frame widths instead of the
long lens) and SGWH - Emmen 2022 (loose floor tolerance; goals placed on the goal frames, the
ghosted panorama leaves about a metre of doubt). Wrong in both: 1. Liga Leimental (low camera,
2.1 m, court shifted onto a door) and the 2015 cup final broadcast. Of the 17 SGWH stream games
two calibrate; the HLA broadcasts and the cup finals (cuts, replays, zoom) fail as before, now
partly with the right reason. The two fixed half-time views and the Chenois gallery camera no
longer "look flat" but reach the court check, which rejects them (a wrong court at another focal
length passed the goal check there in a test with a forced focal length: the goal check is the
only guard).

What the measurement showed:
- **SG Wädenswil/Horgen streams** (SGHW-TV): an operator pans and zooms a wide-angle camera at
  about bench height (2 to 4 m, beside the near sideline); at half-time the stream switches to a
  fixed camera high behind a goal, with a score panel. The camera motion of the game camera is a
  degree or two off between frames (the panorama shows the banners twice): one frame alone has
  50 to 60 % of its line length along two floor directions, all frames together 12 to 33 %, so the
  automatic court stopped at "no clear floor". Where the floor passed, the goal frames in the
  ghosted panorama were too blurred for the stripe check.
- **Fixed cameras** (half-time camera, tripods): the focal length was taken from the line fit
  alone, which cannot tell a long lens tilted a little from a wide one tilted more when the camera
  looks square onto the sidelines (the fit rises by 5 % from 0.5 to 2.5 frame widths, 3 times off
  on a synthetic camera). It picked the long lens, so the view "looked" flat (players 3 to 5
  degrees below the horizon for a gallery camera 6 m up).
- **Lost camera motion**: streams with cuts and replays gave focal lengths of 4 frame widths; the
  panorama shows the hall several times and the failure said "flat view".

Decisions:
1. **Fixed cameras try the focal lengths the lines allow** (`observe._fixed_focals`): within 10 %
   of the best line fit, its optima first, then where the fit is flat the ones farthest from those
   taken (at least 25 % apart, at most four), each calibrated; the best goal fit wins and the info
   carries `focal_px`. Costs up to four calibrations for a fixed camera.
2. **Lost camera motion fails at once with its reason** (`check_motion`: focal length beyond three
   frame widths or zoom beyond x6; an amateur zoom of x3.2 still had a court).
3. **A slightly wrong motion gets a looser floor tolerance**: moving cameras whose lines miss the
   strict fit (35 % within 1 degree) are accepted when 45 % lie within 2 degrees
   (`floor_tolerance_deg` in the info); the court checks stay the same, and a loose floor that
   still looks flat reports "no clear floor".
4. **Stream overlays are masked**: edges that stay at the same frame pixels while a moving camera
   pans (score bug, logo, "LIVE") are stored with the observations (`Observations.static`) and the
   segments on them dropped.
5. **Every failure has a reason** (`CalibrationError.reason`, `calibration_info.reason`):
   `camera_motion`, `no_floor`, `flat_view`, `few_people`, `court`.
6. **A court once per hall** (`hallmatch`, `services/halls.py`): the API sends the analysis the
   courts a person clicked or confirmed on earlier videos of the same hall (the match venue from
   the official game data, handball.ch `venueName`; a home game without a venue takes the team's
   usual home hall), newest first, at most three. The worker matches the two hall images (SIFT on
   both, one homography for a camera at the same place, the floor alone when the walls moved) and
   carries the court over before it tries the automatic court; the result is shown as an
   automatic court (`calibration_info.method` "hall") for the coach to confirm. Measured on 18 hall images of the
   sample (13 SGWH games, half-time views included), all 306 ordered pairs: 5 matches, all
   between game panoramas of one SGWH hall (4 games, floor error 1 to 2.5 px median, floor lines
   on each other in the blend); 3 of its 4 later games would have taken the court over from an
   earlier one. No pair of different halls or cameras matched once matches had to cover 5 % of
   the floor (before that rule a stream logo at the same screen place matched half-time views to
   game panoramas). In the other SGWH hall the camera stood at a different place in each game and
   nothing matched; there the coach clicks again (and that game becomes the next reference).

Open:
- The game camera of the SG Wädenswil/Horgen streams needs a better camera motion (lens
  distortion of the wide lens, zoom) before any court, clicked or automatic, gives positions to
  better than a metre or two; a stream that switches cameras needs the video split per camera.
- A pose fit against the line mask in image pixels (for flat views) was tried: from the top-view
  start a bounded Powell fit did not converge reliably even on synthetic courts (it slides lines
  along each other); it needs a two-sided chamfer and several starts.
- The goal check only knows red and white stripes and needs a sharp hall image; it let two wrong
  courts through (goal fit 0.23 and 0.33) while right ones scored 0.23 to 0.63.
- The lines alone do not fix the tilt of a camera in the middle of the sideline looking square
  (synthetic: the line fit is flat from 1 to 27 degrees); the spread of the players' heights
  finds it (minimum at the true tilt). On the real halls the line fit had a clear peak at the
  same tilt as the players, so this is not what fails there and was not built in.
