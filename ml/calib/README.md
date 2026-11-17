# ml/calib: calibration test set, truth and measurement (research)

Measures the product's automatic court calibration (`handball_vision.observe.auto_calibrate`)
against clicked truth. The product imports nothing from here. Plan, every measurement and what did
not help: `docs/plans/kalibrierung.md` (German).

## Files

| What | File |
|---|---|
| frozen test set: 70 pieces of 90 s, 67 halls, split by hall (33 dev, 37 end test) | `testset.json`, `testset.py` |
| product run: worker proxy, `observe()`, `auto_calibrate`, frame -> court maps | `run.py` (`observe`, `calibrate`) |
| labelling pages (artifacts with a database) | `labelling/feld.html` (round 1, named points), `labelling/feld2.html` (rounds 1b and 2, lines with snapping) |
| truth: a court model fitted to the clicks per frame, consistency check, 1 m grid of pinned court points | `clicks.py` (v2), `truth.py` (v1 helpers) |
| metric: error in metres per piece, correct / wrongly accepted / rejected, bootstrap over halls | `evaluate.py` |
| features for a check against wrong courts, separation on the truth | `features.py` |
| experiments (rejected) | `motion_refine.py`, `experiments/best_window.py` |

Data: `truth_dev.json` (30 dev pieces, 46 frames), `data/round1_answers.json`,
`data/round1b_answers.json` (raw clicks), `results_base.json` (product before the stricter check),
`results_strict.json` (with it), `data/horgen_product.json` and `data/truth_horgen.json` (two
10-minute TV clips, end-test hall: check only).

## Lineage

| Date | Step | Result (dev, 30 pieces with truth) |
|---|---|---|
| 2026-11-16 | test set frozen, product run on all 70 | 15 of 70 courts accepted |
| 2026-11-17 | round 1 (named points): 15 frames with clicks, 8 consistent | too few named points visible on panning club cameras |
| 2026-11-17 | round 1b (lines with snapping): 86 frames, 42 consistent | truth for 30 of 33 dev pieces |
| 2026-11-17 | product before #72 | correct 1 (3 %), wrongly accepted 5 (17 %, 95 % [3, 33]), rejected 24 |
| 2026-11-17 | #72: `court_doubt` (goal >= 0.45, lines >= 1.0, floor >= 0.45), thresholds set before half the truth was in | correct 1, wrongly accepted 0 (0 %), rejected 29 |
| 2026-11-18 | round 2 (end test) | only 1 of 69 frames saved; end test not measured yet |

Rejected along the way (each with numbers in the plan, section 5): lowering `MIN_VIEW_DEG`, scaling
the focal length, radial distortion on the segments, rotation refinement per marking frame,
calibrating on the best window, line agreement with the stored segments.

## Run

    uv run --project packages/vision python ml/calib/run.py observe CACHE --jobs 2 --model yolox_s.onnx
    uv run --project packages/vision python ml/calib/run.py calibrate CACHE ml/calib/results_X.json
    # answers exported from the page's database (collection "lines") into ANSWERS/
    uv run --project packages/vision python ml/calib/clicks.py pull ANSWERS truth.json --cache CACHE
    uv run --project packages/vision python ml/calib/evaluate.py ml/calib/results_X.json truth.json --split dev
