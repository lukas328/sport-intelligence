# PP-OCRv4 (det + rec) — shirt numbers

| | |
|---|---|
| Interface | `handball_vision.numbers.NumberReader` |
| Architecture | PP-OCRv4 mobile text detection (DB) and recognition (SVTR, CTC), ONNX |
| Files | `ch_PP-OCRv4_det_infer.onnx`, `ch_PP-OCRv4_rec_infer.onnx` from the `rapidocr_onnxruntime==1.4.4` wheel on PyPI (only the models are used) |
| SHA-256 | det `d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9`, rec `48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b` |
| Licence | PaddleOCR models Apache-2.0, RapidOCR package Apache-2.0 |
| Runtime | ONNX Runtime, about 27 ms per player crop on 1 CPU thread (detection at 320 px short side) |

## Use in the pipeline
Upper body (10 to 60 % of the box) of players at least 80 px tall, sharp and fully in the frame,
green channel, enlarged three times; only readings of one or two digits count. Per track the
confident readings (0.8 or more) are voted (`numbers.vote`), tracks are cut where the readings
switch from one number to another and joined where fragments share a number (ADR 027).

## Measured (NLB 2017 clip, 720p, 2026-11-04)
- About one crop in ten shows a readable number; of 28 confident single readings 23 were right.
- Reading on every detection frame: 1876 readings in 5 minutes, 14 tracks with a voted number
  (43, 14, 5, 21, 19, 11, 23 checked by eye), 22 % of the player time.
- Errors: blurred 43 read as 33, 14 as 24; the vote and the track split absorb most of them.
