# Ball detector (work in progress)

Transfer learning for a handball ball detector that has to work across halls, cameras and ball
colours. Nothing here ships yet; the scripts are the reproducible trail of the experiments.

## Data
- **TeamTrack handball_side** (Kaggle `atomscott/teamtrack`, MIT licence): 63 clips of 30 s, a fixed
  fisheye panorama 3300 x 450, the ball annotated in every frame (also when held or hidden).
  `extract_teamtrack.py` cuts 192 x 192 tiles every 6th frame: about 9 300 with the ball, 18 600
  without.
- **Our clips**: random tiles as negatives (`extract_negatives.py`), automatic hard negatives (the
  net's peaks outside the court, `eval_on_court.py`), and labelled on-court peaks
  (`label_grid.py`, `save_labels.py`; 37 balls, about 230 non-balls so far).

## Model
`train_ballnet.py`: ResNet18 (ImageNet, torchvision, BSD) layers 1 to 2 plus a small decoder,
stride-4 heatmap, CenterNet focal loss. Augmentation rotates the hue freely (ball colours differ
per hall), scales 0.7 to 1.5, flips, motion blur. Exported to ONNX.

## Results so far (2026-11-04)
| Run | TeamTrack validation (found / false alarm at 0.3) | Our clips |
|---|---|---|
| TeamTrack only, 3000 steps | 44 % / 1.9 % | many false alarms: ceiling lights, spectators, overlays, camera operators |
| + hard negatives + 37 own balls, 1500 steps | 53 % / 2.4 % | static bright spots win (a screw on the Möhlin wall), Stäfa almost silent |

TeamTrack's 100 % is not reachable: the ball is annotated even when hidden in a hand.

## Next
1. Three consecutive frames as input (TrackNet principle): a static spot never moves, a ball does.
2. Temporal path search over the per-frame peaks (one ball, bounded speed, gaps bridged).
3. More own positives from many halls (the 15 full games), labelled in grids.
