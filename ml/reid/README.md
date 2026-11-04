# Own player re-identification model (research, not shipped)

Goal: replace the FastReID BoT-R50 trained on MSMT17 (`ml/models/reid-fastreid.md`, licence
question Q-ML-5) with a model trained only on our own handball crops, labelled automatically
through the shirt numbers (no hand labelling). Same interface as `handball_vision.reid.Embedder`
(N x 3 x 256 x 128 RGB 0..255 in, L2-normalised vectors out), so it drops into the existing
per-match PCA + LDA and the constrained assignment (`reid.assign`, ADR 027).

**Result so far: not good enough to replace the MSMT model.** Trained on two 5-minute clips it is
clearly worse than the MSMT model on the third clip (table below). The pipeline (labels from
numbers, training, evaluation, export) works and is the starting point once more footage with
number readings exists.

## Scripts
| Script | Environment | What |
|---|---|---|
| `build_dataset.py` | project (`uv run`) | track() from stored observations, labels from shirt-number readings, crops 128 x 256 JPEG + `index.json` |
| `common.py` | torch | dataset index, model-free cleaning, model (ResNet18 + 256-d BNNeck) |
| `train.py` | torch | P x K training, batch-hard triplet + identity cross-entropy |
| `evaluate.py` | torch (+ onnxruntime) | same-team retrieval on a held-out clip, any `.pt` or ONNX embedder |
| `export_onnx.py` | torch | ONNX export with the Embedder interface (flip averaging inside) |
| `hidden_numbers.py` | project | ADR 027 hidden-number test with any ONNX embedder (or the stored MSMT vectors) |

The torch environment is a separate venv with torch 2.5.1 / torchvision 0.20.1 (CPU), opencv,
onnx, onnxruntime; the project environment does not carry torch.

## Data (labels from shirt numbers)
Three 5-minute clips with stored observations (`data/views/<clip>-obs.npz`): NLB 2017 Horgen vs
Möhlin, Horgen vs Stäfa, SPL2 2024 Leimental vs Arbon (women). Shirt numbers read with
`handball_vision.numbers.NumberReader` (PP-OCRv4) on every 3rd (Stäfa) or 6th (Möhlin, Leimental)
video frame.

Labelling, first attempt (track votes): identity = clip / team label / voted number of the track,
crops of the whole track. Contact sheets showed this is too noisy: tracks jump between people,
including between teams, the team label of a track is sometimes wrong, and a misread number
(24 for 14, 57 for 51) creates a second identity for one player.

Labelling used (`build_dataset.py --anchor 2.0 --tracklets --every 2`):
- a crop is labelled with a **confident reading (>= 0.85) of its own track at most 2 s away**
  (a track rarely swaps people within 2 s); crops every 2nd detected frame (every 6th video frame),
  box at least 64 px tall, resized to 128 x 256;
- the crop's team comes from **its own shirt colour** (nearest team colour of the clip, starting
  at the manifest kits, refined by k-means); crops near neither team colour (referees,
  goalkeepers, bench) are dropped; identity = clip / team / number; on Leimental-Arbon the number
  must be on the official roster of that team;
- crops more than half covered by another person's box, and crops whose shirt colour is far from
  their identity's median, are dropped; an identity needs 8 crops from at least 3 readings;
- **tracklets**: team tracks of 5 s or more without any reading become their own pseudo-identity
  (positives within the track; negatives only against tracks of the same clip on court at the
  same time for more than 2 s, since a tracklet may be a numbered player).

| Clip | labelled crops (before cleaning) | after cleaning: identities (home / away) | crops | readings behind them | tracklets (crops) |
|---|---|---|---|---|---|
| NLB 2017 Horgen-Möhlin | 3314 | 26 (14 / 12) | 2697 | 951 | 35 (1889) |
| NLB 2017 Horgen-Stäfa | 2314 | 21 (8 / 13) | 1714 | 430 | 43 (2702) |
| SPL2 2024 Leimental-Arbon | 1763 | 11 (6 / 5) | 1218 | 257 | 57 (3962) |
| **total** | 7391 | **58** | **5629** | 1638 | 135 (8553) |

About 180 MB of JPEGs. Build: about 1.5 minutes for the three clips (tracking from stored
observations plus one decode of each video). Reading the numbers on Möhlin and Leimental every
6th frame took 21 and 16 minutes on one CPU core.

Remaining noise (visible in contact sheets): OCR confusions (51/57, 3/13), some crops of a team
mate after a track swap within 2 s, Horgen players appear in two clips (same club, same season:
leave-one-clip-out on the two NLB clips is not fully independent; Leimental-Arbon is).

## Method
- torchvision ResNet18, ImageNet weights (`IMAGENET1K_V1`, BSD-3-Clause), stem and layer1 frozen
  (ImageNet batch-norm statistics), global average pooling, linear 512 -> 256, BNNeck.
- Input resized inside the model (so the 256 x 128 interface stays), ImageNet normalisation inside.
- Loss: batch-hard triplet (margin 0.3) on the 256-d feature + label-smoothed (0.1) identity
  cross-entropy on the BN feature.
- Batches: 2 clip-team groups x 8 identities (half numbered players, half tracklets on court at
  the same time) x 4 crops = 64 crops; all identities in a group wear the same kit, so the hard
  negatives are team mates (the model has to use hair, skin, build, shoes); triplet negatives
  only within a clip.
- Augmentation: horizontal flip, random crop (80-100 % per side), random down-and-up scaling
  (40-100 %, distant players), blur, brightness/contrast/saturation jitter, no hue jitter (kit
  colour separates teams), random erasing.
- AdamW 3e-4, weight decay 5e-4, warm-up then cosine; CPU only.
- Test: vectors of the crop and its mirror image averaged (inside the exported ONNX graph).

| Run | input | iterations x crops | train set (leave-one-out fold) | CPU time (2 threads, machine shared) |
|---|---|---|---|---|
| v1 (all three folds) | 128 x 64 | 500 x 64 | about 9,000-9,800 crops, 125-132 identities (32-47 numbered + 78-100 tracklets) | 10-25 min |
| v2 (Leimental fold, final model) | 160 x 80 | 800 x 64 | same; final: all 14,182 crops, 193 identities (58 + 135) | 42 min (fold), 74 min (final, machine load about 25) |

Inference: about 20-40 ms per crop (with the mirror image) on a loaded 4-core CPU, against 700-900 ms
for the MSMT R50 on the same machine.

Final model: v2 on all three clips, exported as `reid_handball_r18.onnx` (45 MB, 256-d; not in
git, kept with the experiment outputs). The fold models (`fold_staefa.onnx` v1,
`fold_leimental_v2.onnx`) were exported the same way for the held-out tests.

## Evaluation
Leave-one-clip-out: trained on two clips, tested on the third. Same-team retrieval over the
labelled crops of the held-out clip (every 4th detected frame): a query's gallery is every crop
of the same team in other 10-second windows; right = same identity. "Window" = the same with the
mean vector of each identity's 10-second window (closer to how `reid.assign` uses fragments).
The MSMT model is `data/models/reid_bot_r50_msmt.onnx` (2048-d) on the same crops; "ImageNet"
is the untrained ResNet18 (average-pooled 512-d) as a floor.

| Held-out clip | queries / identities | ImageNet R18 (floor) | **ours v1** | ours v2 | MSMT R50 |
|---|---|---|---|---|---|
| Leimental-Arbon (women, other hall; no overlap with training) | 609 / 11 | 0.535 / 0.361 | 0.586 / 0.406 | 0.593 / 0.431 | **0.742 / 0.555** |
| ... window means | 76 | 0.632 / 0.486 | 0.645 / 0.522 | 0.711 / 0.530 | **0.711 / 0.634** |
| Horgen-Stäfa | 847 / 21 | 0.430 / 0.263 | 0.515 / 0.338 | | **0.569 / 0.410** |
| ... window means | 165 | 0.467 / 0.336 | 0.473 / 0.405 | | **0.503 / 0.449** |
| Horgen-Möhlin | 1359 / 26 | 0.430 / 0.221 | 0.478 / 0.283 | | **0.555 / 0.319** |
| ... window means | 209 | 0.426 / 0.309 | 0.498 / 0.376 | | **0.522 / 0.378** |

(rank-1 / mAP.) Training on our crops closes roughly half of the gap between ImageNet features and
the MSMT model; v2 (larger input, longer) helps a little on the one fold it was run on.
The test labels are as noisy as the training labels (see Data), so all absolute values are low and
the comparison between models is what counts.

### Hidden-number test (ADR 027), Horgen-Stäfa
`hidden_numbers.py`: tracks with a well-read number (at least 4 readings, no appearance involved)
cut into 15-second pieces, 9 players, 59 pieces; each piece in turn loses its number and
`reid.assign` must find it. Vectors once per second per player. Ours: the v1 model trained on
Möhlin and Leimental only (ONNX through `handball_vision.reid.Embedder`).

| `reid.assign` variant | MSMT R50: found / right of found | ours: found / right of found |
|---|---|---|
| as shipped (PCA + LDA, consistency gates 0.68 / 0.62) | **75 % / 84 %** | 63 % / 68 % |
| consistency gates off | **85 % / 86 %** | 69 % / 73 % |
| no projection, gates off | 66 % / **87 %** | 63 % / 78 % |

The consistency gates were tuned on MSMT vectors; for ours they are not calibrated (a 256-d
vector space has other similarity levels), the "gates off" row is the fairer comparison.

## Licence
- Backbone weights: torchvision ResNet18 ImageNet weights (BSD-3-Clause, torchvision); ImageNet
  itself is research-licensed, the usual industry practice is to treat ImageNet-pretrained
  backbones as usable, but this is the remaining question for legal (much smaller than MSMT17,
  which is a person re-identification dataset with non-commercial terms).
- Training data: our own crops from our own clips, labels from our own number reader; no
  third-party person data.

## Limitations and next steps
- **Too little data.** 58 numbered identities from 15 minutes of video (32-47 per training fold)
  against 4,101 identities in MSMT17. The loss on the training set was still falling when
  training stopped (triplet accuracy 0.44-0.6), so the model is limited by data and CPU, not by
  over-fitting. The obvious next step is more footage: every full game with stored observations
  and number readings (GPU worker: every detection frame) adds 20-30 identities per half without
  any hand labelling. Re-run `build_dataset.py` + `train.py` then.
- **Label noise**: OCR confusions (51/57, 3/13, 14/24) create false identities; tracks swap
  people within the 2-s window; shirt colour classification fails on two-colour kits (Möhlin red
  with white) and sends referees in yellow to a team. A model-based cleaning round (drop crops
  far from their identity centre after a first training, retrain) was not tried for lack of time.
- **Not independent folds** on the two NLB clips (Horgen plays in both); Leimental-Arbon is the
  clean test and there the gap to MSMT is largest (rank-1 0.59 against 0.74).
- Resolution: 128 x 64 / 160 x 80 for CPU time; the MSMT model sees 256 x 128. Training at
  256 x 128, unfreezing the stem and a larger backbone (ResNet50 ImageNet, also BSD) are open and
  need a GPU.
- The hidden-number test was run only on Stäfa (the only clip with stored MSMT vectors; computing
  them for the other clips takes over an hour on this CPU).

## Reproduce
```bash
S=<scratch dir>; T=<torch venv>/bin/python
# number readings for clips without them (scratchpad num/addnums2.py: <clip> <every> <out.npz>)
uv run python ml/reid/build_dataset.py --out $S/ds2 --cal-dir <dir with <clip>-cal.pkl> \
    --every 2 --tracklets --anchor 2.0 --obs <clip>=<obs with numbers.npz> ...
$T ml/reid/train.py --data $S/ds2 --test-clip ch-spl2-2024-leimental-arbon --out fold.pt \
    --iters 500 --height 128 --tracklets              # v2: --iters 800 --height 160
$T ml/reid/evaluate.py --data $S/ds2 --clip ch-spl2-2024-leimental-arbon --model fold.pt \
    --onnx data/models/reid_bot_r50_msmt.onnx --imagenet --cache $S/emb
$T ml/reid/export_onnx.py fold.pt reid_handball_r18.onnx
uv run python ml/reid/hidden_numbers.py ch-nlb-2017-horgen-staefa --cal-dir <dir> \
    --onnx reid_handball_r18.onnx --cache $S/hidden     # --stored: the MSMT vectors in the obs
```
