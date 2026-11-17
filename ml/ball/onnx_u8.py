"""Give an exported ball net (`export_onnx.py`) a uint8 input with the preprocessing inside the graph
(job 14 in ml/gpu/JOBS.md, docs/plans/produkt-analyse-integration.md, GPU profile T4).

The exported nets take N,9,H,W float32 RGB 0..255; the product builds that on the CPU (BGR to RGB,
channels first, float32: about 21 ms per frame on the T4 machine, and four times the bytes to copy
to the GPU). The new graph takes N,H,W,9 uint8: the three decoded BGR frames t-G, t, t+G joined
along the channel axis (one `np.concatenate`), and does the channel order, the transpose and the
cast itself: Gather (BGR to RGB per frame), Transpose, Cast, then the original net. Works on the
fp32 and the fp16 files (the fp16 file keeps float32 inputs). Output unchanged.

    python ml/ball/onnx_u8.py ball_hrp1_fp16.onnx ball_hrp1_fp16_u8.onnx [--check]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

BGR_TO_RGB = [2, 1, 0, 5, 4, 3, 8, 7, 6]
U8_INPUT = "frames_u8"


def to_u8(src: Path, dst: Path) -> None:
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    model = onnx.load(str(src))
    g = model.graph
    old = g.input[0]
    name = old.name
    if name == U8_INPUT:
        raise ValueError(f"{src} has a uint8 input already")
    # the original input becomes an inner tensor fed by the new preprocessing nodes
    g.initializer.append(numpy_helper.from_array(np.array(BGR_TO_RGB, np.int64), "u8_rgb_idx"))
    pre = [
        helper.make_node("Gather", [U8_INPUT, "u8_rgb_idx"], ["u8_rgb"], axis=3),
        helper.make_node("Transpose", ["u8_rgb"], ["u8_chw"], perm=[0, 3, 1, 2]),
        helper.make_node("Cast", ["u8_chw"], [name], to=TensorProto.FLOAT),
    ]
    nodes = pre + list(g.node)
    del g.node[:]
    g.node.extend(nodes)
    new_in = helper.make_tensor_value_info(U8_INPUT, TensorProto.UINT8, ["n", "h", "w", 9])
    g.input.remove(old)
    g.input.insert(0, new_in)
    onnx.checker.check_model(model)
    onnx.save(model, str(dst))


def u8_frames(frames: list[np.ndarray]) -> np.ndarray:
    """Three BGR frames (already at net size) -> H,W,9 uint8, the input of the u8 graph."""
    return np.concatenate(frames, axis=2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--check", action="store_true", help="same output as the float input")
    a = ap.parse_args()
    to_u8(a.src, a.dst)
    print("wrote", a.dst)
    if a.check:
        import onnxruntime as ort

        rng = np.random.default_rng(0)
        frames = [rng.integers(0, 256, (256, 320, 3), dtype=np.uint8) for _ in range(3)]
        x_u8 = u8_frames(frames)[None]
        rgb = [f[:, :, ::-1] for f in frames]
        x_f = np.concatenate(rgb, 2).transpose(2, 0, 1)[None].astype(np.float32)
        ref = ort.InferenceSession(str(a.src), providers=["CPUExecutionProvider"])
        new = ort.InferenceSession(str(a.dst), providers=["CPUExecutionProvider"])
        r = ref.run(None, {ref.get_inputs()[0].name: x_f})[0]
        n = new.run(None, {U8_INPUT: x_u8})[0]
        print("max abs diff", float(np.abs(r - n).max()))


if __name__ == "__main__":
    main()
