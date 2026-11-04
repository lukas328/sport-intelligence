# Holder classifier (research, not shipped)

"Does this player hold the ball?" asked on a player crop instead of finding a 10-pixel ball in
the whole frame. 78 % of the user-labelled balls lie inside a player's box, so a good per-player
classifier would answer the product question (who has the ball) directly. First try
(`ml/ball/holder_crops.py`, `train_holder.py`: 31 positives) reached AUC 0.65.

**Status: better than the first try, not good enough to ship.** Best variant: crop AUC 0.78,
holder ranked first in 43 % of the held-out frames with a holder (0.26 on the benchmark half of the
single frames). The bar set for an export was AUC 0.85 and 60 %; no ONNX was exported (the
script is ready, see below).

## Data
`build_crops.py` decodes the labelled frames from the source videos exactly like the labelling
tools did (seek to t-G, read on, 1280 wide; checked against the label images), runs YOLOX-m on
the centre frame (boxes cached in `boxes.json`), assigns the clicked ball with
`handball_vision.ballpossession.holder()`: the holder is positive, every other player in the frame
negative; a frame whose ball is in no box ("free") gives only negatives. Crop: box + 25 % each
side, + 25 % above (arms overhead), + 5 % below, cut at the same place in t-G, t, t+G, 128x256 per
frame. Boxes under 24 px are not cropped; a holder that small drops the frame; a near-duplicate box
of the holder (IoU > 0.6) is left out.

| Source | Frames (holder / free) | Crops (pos / neg) | Split |
|---|---|---|---|
| Ball paths, 7 training scenes, keyframes | 102 / 48 | 102 / 2161 | train |
| ... frames between two clicks < 40 px apart (click interpolated) | 161 / 53 | 161 / 2965 | train |
| Single frames, train half (`ball3/user_split.json`) | 33 / 7 | 33 / 590 | train |
| Ball paths, 6 held-out scenes | 96 / 27 | 96 / 1392 | **test** |
| Single frames, benchmark test half | 31 / 9 | 31 / 599 | **test** |
| TeamTrack handball_side (MIT; one hall, fisheye panorama, ground-truth boxes and ball), every 20th frame (`build_tt_crops.py`) | 1642 / 324 | 1642 / 21306 | train (extra) |

Held-out scenes (whole 3-second scenes, never frames of a training scene): `eisenach_wetzlar_2_3189`
(it contains a benchmark test frame), `ch_spl2_2024_leimental_arbon_843`,
`leimental_frauenfeld_2_1919`, `muelheim_suedpfalz_1_4347`, `uznach_dietikon_s3_3574` and
`u20_sui_ger_0_4287` (a hall with no training data at all). Path scenes with only "no ball" marks
(`eisenach_wetzlar_2_265`, `uznach_dietikon_s0_1501`) are not used: a hidden ball may be in a hand.
Only 135 of the 7,707 negative crops contain the clicked ball at all, so "is the ball in my crop"
already separates most negatives.

The Roboflow handball sets (CC BY 4.0, ~3,700 still frames with ball boxes, many halls and
broadcasts) would be the most diverse extra data; `build_rf_crops.py` is written for them, but the
downloaded copy (`<scratch>/rf`) was deleted from the scratch disk while the crops were being built,
so they are not in these results.

## Method
`train.py`: ResNet18 (ImageNet), balanced batches (half holders), flip, time reversal, small
random crop (88-100 %), brightness, contrast, saturation, hue +-8 (the ball's colour matters, so no
full hue rotation). One-cycle LR 3e-4, AdamW, batch 32, fixed number of steps, no model selection
on the test data (CPU only, shared machine: 300 to 600 steps, 0.7 to 13 s per step depending on
the load).
- `--ch 9`: t-G, t, t+G stacked, first conv: centre frame = pretrained weights, neighbours 0;
  `--ch 3`: centre frame only.
- `--aux 1`: auxiliary ball heatmap (stride 8, small head on layer2, CenterNet focal loss) on every
  crop that contains the clicked ball, holder or not. It tells the net *where* to look; without it,
  the net memorises the training poses (train loss 0.03 after 300 steps, test AUC 0.68).
- `--extra DIR`: TeamTrack crops, half of every batch.
- `score.py`: scores the test crops by the classifier (p), the heatmap peak (hm) and their
  geometric mean (mix). `evaluate.py`: the tables below.

## Results (held-out data)
AUC: crop level, holder vs the other players of frames with a holder. top: the holder is the
top-scoring player of its frame. free FP: frames with a free ball whose top score is above 0.5.
fp@med: same, at the median top score of the holder frames (scale-free; the heatmap scores are not
calibrated). Chance for "top" is about 1/14; "biggest box is the holder" is the baseline.

| Variant (96x192) | Steps | AUC all | top all | top scenes | top bench | top@0.5 | free FP | fp@med |
|---|---|---|---|---|---|---|---|---|
| 9 ch | 300 | 0.68 | 0.28 | 0.30 | 0.19 | 0.16 | 0.22 | 0.50 |
| 3 ch | 300 | 0.71 | 0.27 | 0.30 | 0.16 | 0.18 | 0.28 | 0.44 |
| 9 ch + ball heatmap, p | 400 | 0.72 | 0.25 | 0.29 | 0.13 | 0.21 | 0.28 | 0.31 |
| 9 ch + ball heatmap, hm | 400 | 0.79 | 0.39 | 0.45 | 0.19 | 0.13 | 0.03 | 0.19 |
| 9 ch + ball heatmap, mix | 400 | 0.74 | 0.26 | 0.30 | 0.13 | 0.19 | 0.11 | 0.36 |
| 9 ch + heatmap + TeamTrack, p | 600 | 0.76 | 0.38 | 0.42 | 0.26 | 0.31 | 0.42 | 0.31 |
| 9 ch + heatmap + TeamTrack, hm | 600 | 0.80 | 0.36 | 0.44 | 0.13 | 0.19 | 0.06 | 0.36 |
| **9 ch + heatmap + TeamTrack, mix** | 600 | **0.78** | **0.43** | **0.48** | **0.26** | 0.29 | 0.19 | 0.22 |
| biggest box (baseline) | - | - | 0.11 | 0.12 | 0.06 | - | - | - |

"all" = 127 holder frames and 36 free-ball frames (96 + 27 from the held-out scenes, 31 + 9 from
the benchmark half).

128x256 run: see "128x256" below.

Per hall, best variant (mix), frames with a holder / free:

| Hall | set | hold / free | AUC | top | top@0.5 | free FP |
|---|---|---|---|---|---|---|
| leimental_arbon | scene | 14 / 15 | 0.95 | 0.93 | 0.79 | 0.20 |
| muelheim_suedpfalz | scene | 26 / 1 | 0.94 | 0.77 | 0.62 | 0.00 |
| u20_sui_ger (unseen hall) | scene | 7 / 1 | 0.74 | 0.43 | 0.43 | 0.00 |
| uznach_dietikon | scene | 15 / 2 | 0.86 | 0.33 | 0.07 | 0.00 |
| eisenach_wetzlar | scene | 16 / 4 | 0.71 | 0.19 | 0.12 | 0.50 |
| leimental_frauenfeld | scene | 18 / 4 | 0.57 | 0.11 | 0.06 | 0.00 |
| uznach_dietikon | bench | 10 / 4 | 0.85 | 0.30 | 0.00 | 0.25 |
| horgen_staefa | bench | 5 / 1 | 0.66 | 0.40 | 0.40 | 0.00 |
| leimental_arbon | bench | 5 / 2 | 0.75 | 0.40 | 0.20 | 0.50 |
| horgen_moehlin | bench | 5 / 2 | 0.69 | 0.20 | 0.00 | 0.00 |
| cottbus_seg | bench | 3 / 0 | 0.32 | 0.00 | 0.00 | - |
| eisenach_wetzlar | bench | 3 / 0 | 0.42 | 0.00 | 0.00 | - |

Caveat: a held-out scene is one 3-second situation (30 keyframes 0.1 s apart), so a per-hall row
is one or two holders seen many times; the per-hall numbers swing with that.

### Findings
- The binary label alone is not enough with ~135 independent holders: the net memorises poses.
  The auxiliary ball heatmap helps through its own peak (heatmap peak vs plain classifier: AUC
  0.79 vs 0.68, top 0.39 vs 0.28); the TeamTrack crops help the classifier head (top 0.25 -> 0.38)
  but not the heatmap peak; the mix of both heads of the TeamTrack model is the best ranking.
- 9 channels vs 3 channels: no measurable difference at this data size (0.68 vs 0.71 AUC, 0.28
  vs 0.27 top), the motion cue is not what limits it.
- "Nobody holds it" is the weak spot: at a threshold that accepts half of the holder frames,
  about one free-ball frame in five still gets a holder (fp@med 0.19 to 0.22 for the best scores).
  The heatmap peak looks safe at 0.5 only because its scores are low (it also accepts few holders).
- Where it works (Leimental-Arbon, Mülheim: big, sharp players, ball visible in the hands) it
  works well (top 0.77 to 0.93). It fails where the ball is small, blurred or hidden by the body
  and where the holder() label itself is shaky (ball passing over a player in flight, two players
  in one box, falling players).

## Plugging it in (sketch, once it is good enough)
Export: `export_onnx.py model.pt holder.onnx` gives input `x` N x 9 x H x W (RGB 0..255, frames
t-G, t, t+G of each player crop, crop as in `build_crops.py`), output `p` N (holder probability).
In `handball_vision.ballpossession` the per-frame holder would come from the ball path where a
ball peak is near a box (today's `holders()`), and from the classifier otherwise:

```python
def holders_with_classifier(ball, boxes, frames, clf, thr=0.6, margin=1.5):
    out = {}
    for f, bs in boxes.items():
        if f in ball:                            # tracked ball: geometry decides
            out[f] = holder(ball[f], bs)
            continue
        crops = [player_crop(frames, f, b) for b in bs]   # 3 frames, +25 % sides/top
        p = clf(crops)                                    # N probabilities
        i = int(p.argmax())
        second = sorted(p)[-2] if len(p) > 1 else 0.0
        out[f] = bs[i][0] if p[i] > thr and p[i] > margin * second else None
    return out
```
`possessions()` then smooths the runs as today (min hold 0.3 s, gaps up to 0.5 s bridged), which
also absorbs single-frame mistakes. Run it on the tracked boxes every 2nd or 3rd frame only
(ResNet18 at 96x192 is about 0.6 GFLOP per player).

## Next steps
1. More holders from more halls: re-download the Roboflow sets and run `build_rf_crops.py`
   (thousands of holders from many halls; still frames, so 3 channels or repeated frames), and
   label more ball paths in the weak halls (Frauenfeld, Eisenach, Cottbus). The held-out halls
   with good numbers are the ones with similar training halls.
2. A GPU run (Kaggle, as for the ball net): CPU steps here took up to 13 s on the shared machine,
   so the best model saw only 600 x 32 crops; longer training with the heatmap is the cheapest
   lever.
3. Cleaner labels: assign the holder with a stricter rule for training (ball in the upper body /
   hand region, not anywhere in the widened box) and drop frames where the ball is in two boxes.
4. Combine with the ball net: the classifier's score as a prior on ball peaks inside player boxes
   (and the other way round), instead of either alone.
5. Cross-validation over scenes for steadier numbers; one held-out split of 6 scenes is noisy.

## Files
`build_crops.py`, `build_tt_crops.py`, `build_rf_crops.py` (data), `train.py`, `score.py`,
`evaluate.py`, `export_onnx.py`. Crops, models and predictions:
`<scratch>/holder2/` (`data2/`, `ttdata/`, `r*/model.pt`, `r*/pred*.json`).

Reproduce (scratch = the session scratchpad):
```
.venv/bin/python ml/holder/build_crops.py <scratch>/labelseq <scratch>/labelpage <scratch>/ball3/user_split.json <scratch>/holder2/data2
.venv/bin/python ml/holder/build_tt_crops.py <scratch>/tt <scratch>/holder2/ttdata 20
<torchenv>/python ml/holder/train.py <scratch>/holder2/data2 <scratch>/holder2/r9a_tt --ch 9 --aux 1 --size 96 --steps 600 --extra <scratch>/holder2/ttdata
cd ml/holder && <torchenv>/python score.py <scratch>/holder2/data2 <scratch>/holder2/r9a_tt
.venv/bin/python ml/holder/evaluate.py <scratch>/holder2/data2 <scratch>/holder2/r9a_tt/pred_mix.json
```
