import pytest

from handball_gpu_worker.backends import GpuBackend, GpuJobSpec, get_backend, register_backend
from handball_gpu_worker.backends.base import LocalBackend, resolve_entrypoint
from handball_gpu_worker.jobs import run_stage


def test_local_backend_runs_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    b = get_backend("local")
    assert isinstance(b, GpuBackend)
    r = b.run(GpuJobSpec("test", "handball_gpu_worker.jobs:echo", {"a": 1}))
    assert r.output == {"echo": {"a": 1}}
    assert r.device == "cpu"
    assert r.cost_chf == 0.0


def test_local_backend_cost_on_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    r = LocalBackend(hourly_cost_chf=3600.0).run(GpuJobSpec("t", "handball_gpu_worker.jobs:echo"))
    assert r.device == "cuda"
    assert r.cost_chf == pytest.approx(r.gpu_seconds, abs=1e-5)


@pytest.mark.parametrize("name", ["runpod", "modal", "k8s"])
def test_planned_backends_are_explicit(name: str) -> None:
    b = get_backend(name)
    assert b.device() == "remote"
    with pytest.raises(NotImplementedError):
        b.run(GpuJobSpec("t", "x:y"))


def test_unknown_backend() -> None:
    with pytest.raises(ValueError, match="unknown GPU backend"):
        get_backend("nope")


def test_register_backend() -> None:
    register_backend("fake", lambda cost: LocalBackend(cost))
    assert get_backend("fake").name == "local"


def test_invalid_entrypoint() -> None:
    with pytest.raises(ValueError, match="invalid entrypoint"):
        resolve_entrypoint("nocolon")


def test_run_stage_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HB_GPU_BACKEND", "local")
    out = run_stage("s", "handball_gpu_worker.jobs:echo", {"k": "v"}, match_id="m1")
    assert out["backend"] == "local"
    assert out["output"] == {"echo": {"k": "v"}}
