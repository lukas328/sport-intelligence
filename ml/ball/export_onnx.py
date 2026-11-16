"""Export the 3-frame ball nets hr1 (BallHR) and hrp1 (BallHRP) to ONNX for the product
(docs/plans/produkt-analyse-integration.md step 2). Runs once, in its own environment with torch,
timm and onnx; the product only loads the .onnx file with ONNX Runtime.

The exported graph takes N,9,H,W float32 RGB 0..255 (frames t-G, t, t+G stacked as channels; H and
W multiples of 32, the product uses 704 x 1280: the 720 px proxy cropped at the bottom like the
prelabel kernels) and returns N,1,H/4,W/4 ball probabilities (sigmoid already applied). Batch, H
and W are dynamic. `--fp16` also writes a half-precision copy (inputs and outputs stay float32).

LICENCE NOTE (test phase only): both nets were trained with DeepSport data (non-commercial,
ml/ball/LINEAGE.md section 2, D5). The exported files must be replaced by nets trained without
DeepSport before a real go-live (docs/plans/tracking-strategie.md section 9, step 6).

    python ml/ball/export_onnx.py ball_hr1.pt hr out/ball_hr1.onnx [--fp16] [--check FRAME.png]
"""

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class WithSigmoid(torch.nn.Module):
    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x):
        return torch.sigmoid(self.net(x))


def load(kind: str, weights: Path) -> torch.nn.Module:
    if kind == "hr":
        from ballhr import BallHR

        net = BallHR()
    else:
        from ballhrp import BallHRP

        net = BallHRP(pretrained=False)
    # foreign checkpoint: tensors only, never pickled code
    state = torch.load(weights, map_location="cpu", weights_only=True)
    if isinstance(state, dict) and "model" in state and isinstance(state["model"], dict):
        state = state["model"]
    net.load_state_dict(state)
    return WithSigmoid(net).eval()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("weights", type=Path)
    ap.add_argument("kind", choices=["hr", "hrp"])
    ap.add_argument("out", type=Path)
    ap.add_argument("--fp16", action="store_true")
    ap.add_argument("--opset", type=int, default=17)
    a = ap.parse_args()

    net = load(a.kind, a.weights)
    x = torch.rand(2, 9, 704, 1280) * 255
    a.out.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        net,
        (x,),
        str(a.out),
        input_names=["frames"],
        output_names=["heatmap"],
        dynamic_axes={"frames": {0: "n", 2: "h", 3: "w"}, "heatmap": {0: "n", 2: "h4", 3: "w4"}},
        opset_version=a.opset,
        dynamo=False,
    )
    import onnxruntime as ort

    with torch.no_grad():
        ref = net(x).numpy()
    sess = ort.InferenceSession(str(a.out), providers=["CPUExecutionProvider"])
    got = sess.run(None, {"frames": x.numpy()})[0]
    print(a.out.name, "max abs diff vs torch", float(np.abs(got - ref).max()))
    outs = [a.out]
    if a.fp16:
        import onnx
        from onnxconverter_common import float16

        half = float16.convert_float_to_float16(onnx.load(str(a.out)), keep_io_types=True)
        hp = a.out.with_name(a.out.stem + "_fp16.onnx")
        onnx.save(half, str(hp))
        got16 = ort.InferenceSession(str(hp), providers=["CPUExecutionProvider"]).run(
            None, {"frames": x.numpy()}
        )[0]
        print(hp.name, "max abs diff vs torch", float(np.abs(got16 - ref).max()))
        outs.append(hp)
    for p in outs:
        print(p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
