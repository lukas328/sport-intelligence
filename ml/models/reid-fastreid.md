# Person re-identification (FastReID BoT-R50) — recognising players after one number reading

| | |
|---|---|
| Interface | `handball_vision.reid.Embedder` (any ONNX model: N x 3 x 256 x 128 RGB 0..255 in, L2-normalised vectors out) |
| Architecture | ResNet50 (last stride 1) + BNNeck, 2048-d vectors |
| Source weights | `msmt_bot_R50.pth`, release v0.1.1 of JDAI-CV/fast-reid on GitHub (code and weights Apache-2.0) |
| Export | `ml/scripts/export_reid.py` (PyTorch, loads with `weights_only=True`), output `reid.onnx` (94 MB) |
| Runtime | ONNX Runtime, about 170 ms per crop on 4 CPU cores; meant for the CUDA worker |

## Licence: open question (not shipped)
The weights are Apache-2.0, but they were trained on MSMT17, whose terms allow non-commercial
research only. Before production use this needs a legal answer, or a model trained on data we may
use (Q-ML-5 in `docs/OPEN_QUESTIONS.md`). The worker therefore runs re-identification only when a
`reid.onnx` is installed; no image contains one.

## Measured (NLB 2017 clip, 2026-11-04)
Numbers hidden on 15-second pieces of the 12 numbered players' tracks: 65 % of the pieces assigned,
70 to 75 % of those right, with the per-match projection (PCA + LDA trained on the numbered
tracks). Without the projection 47 %; colour statistics alone 19 %. On the whole clip the numbered
player time grows from 1716 s to 2375 s; a junk track with a wrong number still attracts others.
