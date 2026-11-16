"""BallHRP: an ImageNet-pretrained HRNet-W18 (timm) as a 3-frame ball heatmap net (research, ml/).

Counterpart of BallHR (ballhr.py, same HRNet idea, own code, from scratch): here the backbone is
timm's hrnet_w18 with its ImageNet weights, so the two runs on the same data tell what pretraining
adds. Input and output as BallNet3: N,9,H,W RGB 0..255 (previous, centre, next) -> N,1,H/4,W/4.

The pretrained first conv takes 3 channels; it is widened to 9: the centre frame gets the
pretrained weights, the neighbours start at zero (as for the earlier 3-frame nets), so the start
is exactly the pretrained single-frame net. The head concatenates the four branches (strides 4 to
32, 18 + 36 + 72 + 144 channels) at stride 4.

This file is the single source: the Kaggle push scripts inline its text.
"""

import timm
import torch
import torch.nn as nn
import torch.nn.functional as F


class BallHRP(nn.Module):
    def __init__(s, pretrained=True, name="hrnet_w18"):
        super().__init__()
        s.bb = timm.create_model(name, pretrained=pretrained, features_only=True, feature_location="",
                                 out_indices=(1, 2, 3, 4))
        c1 = s.bb.conv1
        w = c1.weight.detach()
        new = nn.Conv2d(9, w.shape[0], c1.kernel_size, c1.stride, c1.padding, bias=False)
        with torch.no_grad():
            new.weight.zero_()
            new.weight[:, 3:6] = w
        s.bb.conv1 = new
        ch = sum(s.bb.feature_info.channels())
        s.head = nn.Sequential(nn.Conv2d(ch, 64, 3, padding=1, bias=False), nn.BatchNorm2d(64), nn.ReLU(),
                               nn.Conv2d(64, 1, 1))
        nn.init.constant_(s.head[-1].bias, -4.0)
        cfg = s.bb.pretrained_cfg if hasattr(s.bb, "pretrained_cfg") else {}
        mean = cfg.get("mean", (0.485, 0.456, 0.406)); std = cfg.get("std", (0.229, 0.224, 0.225))
        s.register_buffer("mean", torch.tensor(list(mean) * 3).view(1, 9, 1, 1) * 255)
        s.register_buffer("std", torch.tensor(list(std) * 3).view(1, 9, 1, 1) * 255)

    def forward(s, x):  # N,9,H,W RGB 0..255 -> N,1,H/4,W/4 logits
        xs = s.bb((x - s.mean) / s.std)
        size = xs[0].shape[-2:]
        up = [xs[0]] + [F.interpolate(t, size=size, mode="bilinear", align_corners=False) for t in xs[1:]]
        return s.head(torch.cat(up, 1))
