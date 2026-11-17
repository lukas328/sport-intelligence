"""Ball net runner: heatmap peaks, frame preparation and the ring buffer that feeds triplets."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper

from handball_vision import ballnet


def _tiny_net(path: Path) -> Path:
    """A stand-in for an exported ball net: mean over the 9 channels / 255, 4 x 4 average pool,
    so a bright spot in the centre frame becomes the heatmap peak."""
    x = helper.make_tensor_value_info("frames", TensorProto.FLOAT, ["n", 9, "h", "w"])
    y = helper.make_tensor_value_info("heatmap", TensorProto.FLOAT, ["n", 1, "h4", "w4"])
    scale = helper.make_tensor("s", TensorProto.FLOAT, [], [1 / 255])
    nodes = [
        helper.make_node("ReduceMean", ["frames"], ["m"], axes=[1], keepdims=1),
        helper.make_node("AveragePool", ["m"], ["p"], kernel_shape=[4, 4], strides=[4, 4]),
        helper.make_node("Mul", ["p", "s"], ["heatmap"]),
    ]
    graph = helper.make_graph(nodes, "tiny", [x], [y], initializer=[scale])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    onnx.save(model, str(path))
    return path


def _frame(spot: tuple[int, int] | None = None, w: int = 1280, h: int = 720) -> np.ndarray:
    f = np.zeros((h, w, 3), np.uint8)
    if spot is not None:
        x, y = spot
        f[y - 4 : y + 4, x - 4 : x + 4] = 255
    return f


def test_peaks_blank_neighbourhood() -> None:
    hm = np.zeros((10, 20), np.float32)
    hm[2, 3] = 0.9
    hm[2, 4] = 0.8  # same blob: suppressed
    hm[8, 15] = 0.5
    p = ballnet.peaks(hm, k=2)
    assert p[0] == (14.0, 10.0, 0.9)
    assert p[1] == (62.0, 34.0, 0.5)


def test_frame_gap() -> None:
    assert ballnet.frame_gap(25) == 2
    assert ballnet.frame_gap(30) == 2
    assert ballnet.frame_gap(50) == 3


def test_net_finds_spot_in_frame_pixels(tmp_path: Path) -> None:
    net = ballnet.BallNet([_tiny_net(tmp_path / "a.onnx")])
    trip = [_frame(), _frame((640, 300)), _frame()]
    out = net.run([trip, [_frame(), _frame((100, 600)), _frame()]])
    assert len(out) == 2
    assert abs(out[0][0][0] - 640) <= 4 and abs(out[0][0][1] - 300) <= 4
    assert abs(out[1][0][0] - 100) <= 4 and abs(out[1][0][1] - 600) <= 4
    # input of another width: candidates still in that frame's pixels
    small = [_frame(w=640, h=360), _frame((320, 150), w=640, h=360), _frame(w=640, h=360)]
    q = net.run([small])[0][0]
    assert abs(q[0] - 320) <= 3 and abs(q[1] - 150) <= 3


def test_two_nets_are_merged(tmp_path: Path) -> None:
    net = ballnet.BallNet([_tiny_net(tmp_path / "a.onnx"), _tiny_net(tmp_path / "b.onnx")])
    single = ballnet.BallNet([_tiny_net(tmp_path / "c.onnx")])
    trip = [_frame(), _frame((640, 300)), _frame()]
    assert net.model == "a+b"
    assert net.run([trip])[0][0] == single.run([trip])[0][0]


class _FakeNet:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def run(self, triplets: list[list[np.ndarray]]) -> list[list[tuple[float, float, float]]]:
        self.calls.append(len(triplets))
        # the centre frame's marker value tells which frame it was
        return [
            [(float(t[1][0, 0, 0]), float(t[0][0, 0, 0]), float(t[2][0, 0, 0]))] for t in triplets
        ]


def test_ring_buffer_triplets_and_batches() -> None:
    fake = _FakeNet()
    bc = ballnet.BallCandidates(fake, fps=25, every=1, batch=4)  # type: ignore[arg-type]
    for i in range(20):
        f = np.full((4, 4, 3), i, np.uint8)
        bc.add(i, f)
    bc.flush()
    # centre frames 2..17 (G = 2): neighbours t-2 and t+2
    assert sorted(bc.result) == list(range(2, 18))
    for t, cands in bc.result.items():
        assert cands == [(float(t), float(t - 2), float(t + 2))]
    assert fake.calls == [4, 4, 4, 4]


def test_every_second_frame() -> None:
    bc = ballnet.BallCandidates(_FakeNet(), fps=50, every=2, batch=3)  # type: ignore[arg-type]
    for i in range(20):
        bc.add(i, np.full((4, 4, 3), i, np.uint8))
    bc.flush()
    assert sorted(bc.result) == list(range(4, 17, 2))  # G = 3 at 50 fps
