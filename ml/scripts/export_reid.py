"""Export FastReID BoT-R50 weights to the ONNX interface of handball_vision.reid.Embedder.

    python ml/scripts/export_reid.py msmt_bot_R50.pth reid.onnx

Needs torch and torchvision (not a project dependency). The checkpoint is loaded with
weights_only=True, so no code from the file runs. See ml/models/reid-fastreid.md for the licence
question before using the result in production.
"""

from __future__ import annotations

import sys

import torch
import torchvision


class BoT(torch.nn.Module):
    def __init__(self, checkpoint: str) -> None:
        super().__init__()
        sd = torch.load(checkpoint, map_location="cpu", weights_only=True)["model"]
        r = torchvision.models.resnet50(weights=None)
        r.layer4[0].conv2.stride = (1, 1)
        r.layer4[0].downsample[0].stride = (1, 1)
        r.fc = torch.nn.Identity()
        r.load_state_dict(
            {k[9:]: v for k, v in sd.items() if k.startswith("backbone.")}, strict=False
        )
        self.r = r
        self.bn = torch.nn.BatchNorm1d(2048)
        self.bn.load_state_dict({k[13:]: v for k, v in sd.items() if k.startswith("heads.bnneck.")})
        self.register_buffer("mean", sd["pixel_mean"].view(1, 3, 1, 1))
        self.register_buffer("std", sd["pixel_std"].view(1, 3, 1, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        f = self.bn(self.r((x - self.mean) / self.std))
        return torch.nn.functional.normalize(f, dim=1)


if __name__ == "__main__":
    model = BoT(sys.argv[1]).eval()
    torch.onnx.export(
        model,
        torch.rand(1, 3, 256, 128) * 255,
        sys.argv[2],
        input_names=["x"],
        output_names=["f"],
        dynamic_axes={"x": {0: "n"}, "f": {0: "n"}},
        opset_version=17,
    )
