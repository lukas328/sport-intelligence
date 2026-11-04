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

DATASET_TABLE

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

TRAINING_DETAILS

## Evaluation
Leave-one-clip-out: trained on two clips, tested on the third. Same-team retrieval over the
labelled crops of the held-out clip (every 4th detected frame): a query's gallery is every crop
of the same team in other 10-second windows; right = same identity. "Window" = the same with the
mean vector of each identity's 10-second window (closer to how `reid.assign` uses fragments).
The MSMT model is `data/models/reid_bot_r50_msmt.onnx` (2048-d) on the same crops; "ImageNet"
is the untrained ResNet18 (average-pooled 512-d) as a floor.

RESULTS_TABLE

HIDDEN_TABLE

## Licence
- Backbone weights: torchvision ResNet18 ImageNet weights (BSD-3-Clause, torchvision); ImageNet
  itself is research-licensed, the usual industry practice is to treat ImageNet-pretrained
  backbones as usable, but this is the remaining question for legal (much smaller than MSMT17,
  which is a person re-identification dataset with non-commercial terms).
- Training data: our own crops from our own clips, labels from our own number reader; no
  third-party person data.

## Limitations and next steps
LIMITATIONS
