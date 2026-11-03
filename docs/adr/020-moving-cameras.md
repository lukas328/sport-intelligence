# 020. Moving cameras: rotation model, hall panorama, per-frame court homography

- Status: accepted
- Date: 2026-11-03

## Context
The first real test videos (Q-DATA-1, `docs/perf/real-videos.md`) all come from an operator who pans
(and sometimes zooms) with play; one is a TV broadcast with overlays. The vision baseline (ADR 012)
assumed a fixed camera everywhere: calibration from a median frame, background model per pixel. On real
footage it failed on all three clips. The platform has to accept the videos clubs actually have, fixed
or moving, instead of asking clubs to film differently.

## Decision
1. **Camera model: tripod rotation plus zoom.** Frames are related by H = K_a R_ab K_b^-1. `motion.py`
   tracks KLT features frame to frame, fits rotation and zoom directly to the point pairs (Huber
   Gauss-Newton, 4 parameters instead of a free 8-parameter homography, so errors do not grow into
   distortions), anchors every 10th frame to earlier keyframes of the same view (ORB, loop closure),
   estimates the focal length from pairs 8 to 30 degrees apart, and places segments after cuts by
   registering them to placed keyframes; segments that never connect are dropped.
2. **Hall panorama as a virtual fixed camera.** A planar canvas (pinhole, axis in the middle of the pan
   range, limited to 70 degrees around it) holds the median of warped samples: the empty hall. Calibration
   runs once on the panorama; automatic calibration is only accepted if the camera showed at least 85 %
   of the court. Manual points (`calibrate_points`) refer to one frame and are carried to the panorama.
3. **Detection stays in the original frame.** Per frame: court homography = canvas -> frame @ panorama
   calibration; the background is rendered from the panorama into the frame; court mask and expected
   player heights follow from that homography (`MovingBackgroundDetector`). Tracking, teams and
   physical load run unchanged in court coordinates.
4. **Fixed cameras keep the old path.** `camera_moves` checks a few short windows across the video first
   (feature shift over 5 frames); only moving cameras pay for the motion pass.
5. **Line colours.** Multi-sport floors carry several line sets and the handball lines are not always
   white. Calibration tries the classic white mask and one mask per colour (top-hat / black-hat relative
   to the local floor) and keeps the court that explains most line points beyond chance.
6. **Synthetic panning footage** (`SyntheticConfig(pan=..., zoom=...)`, textured walls, per-frame ground
   truth homography) tests the whole chain; `ml/eval/run.py` has `pan-follow` and `pan-zoom` scenarios.

## Consequences
- Synthetic pan: rotation error about 0.2 degrees, focal length within 1 %; tracking quality on par with
  fixed cameras (`docs/perf/eval.md`). Real clips: camera motion and panorama work on all three (pan 80
  to 86 degrees, 100 % of frames placed).
- Automatic calibration is not reliable on the real halls yet (faint or coloured handball lines among
  many other lines, near sideline hidden by spectators): it fails or, in one of three clips, returns a
  court several metres off that passes every automatic check. Until a top-view search, goal detection or
  a learned court model is in place, calibrations of moving cameras need user confirmation or clicked
  points: every analysis stores a hall image (`analysis/panorama.jpg`, plus `motion.npz` so a re-run keeps
  the same panorama coordinates); a failed automatic calibration ends as `needs_calibration` and the web
  dialog lets the user mark landmarks on the hall image (`POST .../calibration` with `space: "panorama"`).
- Cost: the motion pass adds about 0.35 x video length on CPU; the per-frame view rendering adds a few
  ms per frame.
- The stored calibration of a moving camera refers to the panorama (image size = canvas). Overlays in
  the web player that project court positions into the video need per-frame homographies (follow-up);
  until then the spotlight is hidden for moving cameras.
- Broadcast cuts to other cameras and replays are dropped unless they show a view seen before.

## Alternatives considered
- **Free homography chain** (8 parameters per step): tried first; drift grew to apparent 13x zoom over
  5 minutes and the panorama smeared.
- **One planar panorama of everything**: a balcony camera turns 80 degrees and more; a planar canvas
  degenerates beyond about 70 degrees around its axis, so the panorama is only used for the background
  and calibration, never as the detection image.
- **Asking clubs to film with a fixed camera**: still the recommended setup (better quality), but not a
  requirement.
