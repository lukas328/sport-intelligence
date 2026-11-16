"""BallHR: a small HRNet-style 3-frame ball heatmap net (research, ml/).

Idea as in WASB (Tarashima et al., BMVC 2023, "Widely Applicable Strong Baseline for Sports Ball
Detection and Tracking"): keep a high-resolution branch through the whole net and exchange
information with lower-resolution branches at every stage, so a ball of 5 to 20 px is never
squeezed into a coarse feature map. Written from the paper's idea, no code or weights taken.

Input and output match BallNet3 (ml/ball/kaggle/train_r6.py) so the training and prelabel kernels
only swap the class: N,9,H,W RGB 0..255 (previous, centre, next frame) -> N,1,H/4,W/4 logits.
Branches at strides 4, 8 and 16 (channels 48, 96, 192); stage 1 one branch, stage 2 two branches
(2 modules), stage 3 three branches (3 modules); every module = 2 BasicBlocks per branch plus a
full fusion; the head concatenates all branches at stride 4.

This file is the single source: the Kaggle push scripts inline its text.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


def _bn(c):
    return nn.BatchNorm2d(c, momentum=0.05)


class _Basic(nn.Module):
    def __init__(s, c):
        super().__init__()
        s.c1 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        s.b1 = _bn(c)
        s.c2 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        s.b2 = _bn(c)

    def forward(s, x):
        y = F.relu(s.b1(s.c1(x)))
        return F.relu(x + s.b2(s.c2(y)))


class _Module(nn.Module):
    """One HR module: blocks per branch, then every branch receives the sum of all branches."""

    def __init__(s, chans):
        super().__init__()
        n = len(chans)
        s.blocks = nn.ModuleList(nn.Sequential(_Basic(c), _Basic(c)) for c in chans)
        s.fuse = nn.ModuleList()
        for i in range(n):  # target branch
            row = nn.ModuleList()
            for j in range(n):  # source branch
                if j == i:
                    row.append(nn.Identity())
                elif j > i:  # lower resolution -> 1x1 conv, upsampled in forward
                    row.append(nn.Sequential(nn.Conv2d(chans[j], chans[i], 1, bias=False), _bn(chans[i])))
                else:  # higher resolution -> strided 3x3 convs
                    steps = []
                    c = chans[j]
                    for k in range(i - j):
                        last = k == i - j - 1
                        out = chans[i] if last else c
                        steps += [nn.Conv2d(c, out, 3, 2, 1, bias=False), _bn(out)]
                        if not last:
                            steps.append(nn.ReLU())
                    row.append(nn.Sequential(*steps))
            s.fuse.append(row)

    def forward(s, xs):
        xs = [b(x) for b, x in zip(s.blocks, xs, strict=True)]
        out = []
        for i, row in enumerate(s.fuse):
            y = xs[i]
            for j, f in enumerate(row):
                if j == i:
                    continue
                z = f(xs[j])
                if j > i:
                    z = F.interpolate(z, size=xs[i].shape[-2:], mode="bilinear", align_corners=False)
                y = y + z
            out.append(F.relu(y))
        return out


class BallHR(nn.Module):
    def __init__(s, chans=(48, 96, 192)):
        super().__init__()
        c1, c2, c3 = chans
        s.stem = nn.Sequential(
            nn.Conv2d(9, 32, 3, 2, 1, bias=False), _bn(32), nn.ReLU(),
            nn.Conv2d(32, c1, 3, 2, 1, bias=False), _bn(c1), nn.ReLU(),
        )
        s.stage1 = nn.Sequential(_Basic(c1), _Basic(c1))
        s.down2 = nn.Sequential(nn.Conv2d(c1, c2, 3, 2, 1, bias=False), _bn(c2), nn.ReLU())
        s.stage2 = nn.ModuleList(_Module((c1, c2)) for _ in range(2))
        s.down3 = nn.Sequential(nn.Conv2d(c2, c3, 3, 2, 1, bias=False), _bn(c3), nn.ReLU())
        s.stage3 = nn.ModuleList(_Module((c1, c2, c3)) for _ in range(3))
        s.head = nn.Sequential(
            nn.Conv2d(c1 + c2 + c3, 64, 3, padding=1, bias=False), _bn(64), nn.ReLU(),
            nn.Conv2d(64, 1, 1),
        )
        nn.init.constant_(s.head[-1].bias, -4.0)  # start with a low ball prior (focal loss)
        s.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406] * 3).view(1, 9, 1, 1) * 255)
        s.register_buffer("std", torch.tensor([0.229, 0.224, 0.225] * 3).view(1, 9, 1, 1) * 255)

    def forward(s, x):  # N,9,H,W RGB 0..255 -> N,1,H/4,W/4 logits
        x = (x - s.mean) / s.std
        a = s.stage1(s.stem(x))
        xs = [a, s.down2(a)]
        for m in s.stage2:
            xs = m(xs)
        xs = [xs[0], xs[1], s.down3(xs[1])]
        for m in s.stage3:
            xs = m(xs)
        size = xs[0].shape[-2:]
        up = [xs[0]] + [F.interpolate(t, size=size, mode="bilinear", align_corners=False) for t in xs[1:]]
        return s.head(torch.cat(up, 1))
