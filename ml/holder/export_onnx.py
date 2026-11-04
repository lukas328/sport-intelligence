"""Export a train.py model to ONNX: input "x" N x C x H x W float RGB 0..255 (C = 9: frames t-G, t,
t+G stacked; C = 3: centre frame), ImageNet normalisation inside; output "p" N holder probability.
Checks onnxruntime against torch on random input.

usage: export_onnx.py <model.pt> <out.onnx>
"""

import sys

import numpy as np
import torch
import torch.nn as nn
import torchvision

ck = torch.load(sys.argv[1], map_location="cpu")
ch, W, H = ck["ch"], ck["w"], ck["h"]
r = torchvision.models.resnet18()
if ch == 9:
    r.conv1 = nn.Conv2d(9, 64, 7, 2, 3, bias=False)
r.fc = nn.Linear(512, 1)
r.load_state_dict(ck["state"])
r.eval()


class Wrap(nn.Module):
    def __init__(self, net):
        super().__init__()
        self.net = net
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406] * (ch // 3)).view(1, ch, 1, 1) * 255)
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225] * (ch // 3)).view(1, ch, 1, 1) * 255)

    def forward(self, x):
        return torch.sigmoid(self.net((x - self.mean) / self.std)[:, 0])


m = Wrap(r).eval()
x = torch.rand(2, ch, H, W) * 255
torch.onnx.export(m, x, sys.argv[2], input_names=["x"], output_names=["p"], dynamic_axes={"x": {0: "n"}, "p": {0: "n"}}, opset_version=17)
import onnxruntime as ort

s = ort.InferenceSession(sys.argv[2], providers=["CPUExecutionProvider"])
d = np.abs(s.run(None, {"x": x.numpy()})[0] - m(x).detach().numpy()).max()
print(f"exported {sys.argv[2]}: input N x {ch} x {H} x {W}, max |onnx - torch| = {d:.2e}")
