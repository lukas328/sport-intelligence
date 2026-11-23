from __future__ import annotations

import sys

from handball_gpu_worker.config import GpuWorkerSettings
from handball_jobkit.redisconn import sync_redis
from handball_jobkit.rqworker import run_worker


def main() -> None:
    settings = GpuWorkerSettings()
    if len(sys.argv) > 1 and sys.argv[1] == "healthcheck":
        sync_redis(settings.redis_url).ping()
        sys.exit(0)
    # --burst: work the queued jobs and exit (the GPU job execution of the serverless setup)
    burst = "--burst" in sys.argv[1:]
    run_worker(sync_redis(settings.redis_url, blocking=True), [settings.gpu_queue], burst=burst)


if __name__ == "__main__":
    main()
