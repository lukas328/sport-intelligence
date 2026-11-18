"""Ball net runner: heatmap peaks, frame preparation and the ring buffer that feeds triplets."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper

from handball_vision import ballnet


def _tiny_net(path: Path, u8: bool = False) -> Path:
    """A stand-in for an exported ball net: mean over the 9 channels / 255, 4 x 4 average pool,
    so a bright spot in the centre frame becomes the heatmap peak. `u8`: with the uint8 input of
    `ml/ball/onnx_u8.py` (N,H,W,9 BGR; cast, colour order and transpose in the graph)."""
    x = helper.make_tensor_value_info("frames", TensorProto.FLOAT, ["n", 9, "h", "w"])
    y = helper.make_tensor_value_info("heatmap", TensorProto.FLOAT, ["n", 1, "h4", "w4"])
    scale = helper.make_tensor("s", TensorProto.FLOAT, [], [1 / 255])
    inits = [scale]
    pre = []
    if u8:
        x = helper.make_tensor_value_info("frames_u8", TensorProto.UINT8, ["n", "h", "w", 9])
        inits.append(helper.make_tensor("idx", TensorProto.INT64, [9], [2, 1, 0, 5, 4, 3, 8, 7, 6]))
        pre = [
            helper.make_node("Cast", ["frames_u8"], ["f"], to=TensorProto.FLOAT),
            helper.make_node("Gather", ["f", "idx"], ["g"], axis=3),
            helper.make_node("Transpose", ["g"], ["frames"], perm=[0, 3, 1, 2]),
        ]
    nodes = [
        *pre,
        helper.make_node("ReduceMean", ["frames"], ["m"], axes=[1], keepdims=1),
        helper.make_node("AveragePool", ["m"], ["p"], kernel_shape=[4, 4], strides=[4, 4]),
        helper.make_node("Mul", ["p", "s"], ["heatmap"]),
    ]
    graph = helper.make_graph(nodes, "tiny", [x], [y], initializer=inits)
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


def test_uint8_net_gives_the_same_candidates(tmp_path: Path) -> None:
    f32 = ballnet.BallNet([_tiny_net(tmp_path / "f.onnx")])
    u8 = ballnet.BallNet([_tiny_net(tmp_path / "u.onnx", u8=True)])
    mixed = ballnet.BallNet([_tiny_net(tmp_path / "a.onnx"), _tiny_net(tmp_path / "b.onnx", True)])
    assert u8.u8 == [True] and mixed.u8 == [False, True]
    rng = np.random.default_rng(0)
    trip = [rng.integers(0, 60, (720, 1280, 3), dtype=np.uint8) for _ in range(3)]
    trip[1][300:308, 640:648] = 255
    small = [cv2.resize(f, (640, 360)) for f in trip]
    for t in (trip, small):
        assert u8.run([t]) == f32.run([t])
        assert mixed.run([t]) == f32.run([t])


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
    bc.finish()
    # centre frames 2..17 (G = 2): neighbours t-2 and t+2
    assert sorted(bc.result) == list(range(2, 18))
    for t, cands in bc.result.items():
        assert cands == [(float(t), float(t - 2), float(t + 2))]
    assert fake.calls == [4, 4, 4, 4]


def test_every_second_frame() -> None:
    bc = ballnet.BallCandidates(_FakeNet(), fps=50, every=2, batch=3)  # type: ignore[arg-type]
    for i in range(20):
        bc.add(i, np.full((4, 4, 3), i, np.uint8))
    bc.finish()
    assert sorted(bc.result) == list(range(4, 17, 2))  # G = 3 at 50 fps


class _SlowNet(_FakeNet):
    def __init__(self, fail: bool = False) -> None:
        super().__init__()
        self.fail = fail
        self.threads: set[str] = set()

    def run(self, triplets: list[list[np.ndarray]]) -> list[list[tuple[float, float, float]]]:
        import threading
        import time

        self.threads.add(threading.current_thread().name)
        time.sleep(0.01)
        if self.fail:
            raise RuntimeError("net failed")
        return super().run(triplets)


def test_worker_thread_same_result_as_inline() -> None:
    out = []
    for threaded in (True, False):
        net = _SlowNet()
        bc = ballnet.BallCandidates(net, fps=25, batch=2, threaded=threaded)  # type: ignore[arg-type]
        for i in range(40):
            bc.add(i, np.full((4, 4, 3), i, np.uint8))
            assert len(bc.futures) <= ballnet.IN_FLIGHT
        bc.finish()
        assert bc.busy_s > 0
        out.append((bc.result, net.threads))
    assert out[0][0] == out[1][0]
    assert all(t.startswith("ballnet") for t in out[0][1])
    assert not any(t.startswith("ballnet") for t in out[1][1])


def test_worker_errors_reach_the_caller() -> None:
    import pytest

    bc = ballnet.BallCandidates(_SlowNet(fail=True), fps=25, batch=2)  # type: ignore[arg-type]
    for i in range(10):
        try:
            bc.add(i, np.full((4, 4, 3), i, np.uint8))
        except RuntimeError:
            break  # an earlier batch failed while adding: also fine
    with pytest.raises(RuntimeError, match="net failed"):
        bc.finish()
    assert bc.pool is None


def test_fixed_mmap_threshold_respects_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MALLOC_MMAP_THRESHOLD_", "4194304")
    assert ballnet.fixed_mmap_threshold() is False


def test_fixed_mmap_threshold_sets_it_on_glibc(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    if platform.system() != "Linux" or platform.libc_ver()[0] != "glibc":
        return
    monkeypatch.delenv("MALLOC_MMAP_THRESHOLD_", raising=False)
    assert ballnet.fixed_mmap_threshold() is True
