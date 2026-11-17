import math
import os
from pathlib import Path

import uvicorn

CGROUP_V2 = Path("/sys/fs/cgroup/cpu.max")
CGROUP_V1_QUOTA = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
CGROUP_V1_PERIOD = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")


def cpu_quota(
    v2: Path = CGROUP_V2, v1_quota: Path = CGROUP_V1_QUOTA, v1_period: Path = CGROUP_V1_PERIOD
) -> float | None:
    """The cores the container may use (cgroup CPU limit), None without a limit. A container
    sees the host's cores in os.cpu_count(), not its own share."""
    try:
        quota, period = v2.read_text().split()[:2]
        return None if quota == "max" else int(quota) / int(period)
    except (OSError, ValueError):
        pass
    try:
        q = int(v1_quota.read_text())
        return None if q <= 0 else q / int(v1_period.read_text())
    except (OSError, ValueError):
        return None


def default_workers(quota: float | None, cores: int) -> int:
    """One process per core the container may use, at least two where the host has two (one
    may block on CPU work while the other answers), at most four. Every process has its own
    database pool, so the count also sets how many connections the API may open."""
    limit = math.ceil(quota) if quota else cores
    return max(1, min(4, max(limit, 2), cores))


def main() -> None:
    workers = int(os.environ.get("HB_WORKERS") or default_workers(cpu_quota(), os.cpu_count() or 1))
    uvicorn.run(
        "handball_api.main:create_app",
        factory=True,
        host="0.0.0.0",  # noqa: S104 (container)
        port=8000,
        proxy_headers=True,
        server_header=False,  # no version banner (ASVS V14)
        workers=workers,
    )


if __name__ == "__main__":
    main()
