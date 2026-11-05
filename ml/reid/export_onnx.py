"""Export a trained model (train.py) to ONNX with the handball_vision.reid.Embedder interface:
N x 3 x 256 x 128 RGB float 0..255 in (resize and normalisation inside), L2-normalised 256-d
vectors out. The exported graph averages the vectors of the crop and its mirror image (as
evaluate.py does).

    python ml/reid/export_onnx.py model.pt reid_handball_r18.onnx
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
from common import build_model  # noqa: E402


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    ck = torch.load(src, map_location="cpu", weights_only=True)
    m = build_model(size=tuple(ck["size"]), pretrained=False)
    m.load_state_dict(ck["state"])
    m.eval()

    class Flip(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.m = m

        def forward(self, x):  # type: ignore[no-untyped-def]
            v = self.m(x) + self.m(torch.flip(x, dims=[3]))
            return torch.nn.functional.normalize(v, dim=1)

    m = Flip().eval()
    x = torch.rand(2, 3, 256, 128) * 255
    torch.onnx.export(
        m,
        (x,),
        str(dst),
        input_names=["input"],
        output_names=["embedding"],
        dynamic_axes={"input": {0: "n"}, "embedding": {0: "n"}},
        opset_version=17,
    )
    import onnxruntime as ort

    s = ort.InferenceSession(str(dst), providers=["CPUExecutionProvider"])
    got = s.run(None, {"input": x.numpy()})[0]
    with torch.no_grad():
        want = m(x).numpy()
    print(dst, "shape", got.shape, "max diff", float(np.abs(got - want).max()))


if __name__ == "__main__":
    main()
