from __future__ import annotations

import sys
import time
from pathlib import Path

from rq import Worker

from handball_jobkit.redisconn import sync_redis
from handball_jobkit.rqworker import run_worker
from handball_worker.config import WorkerSettings
from handball_worker.ticks import ensure_scheduled


def healthcheck(settings: WorkerSettings) -> int:
    """Container healthcheck: Redis reachable and a worker registered."""
    conn = sync_redis(settings.redis_url)
    conn.ping()
    return 0 if Worker.all(connection=conn) else 1


def main() -> None:
    settings = WorkerSettings()
    if len(sys.argv) > 1 and sys.argv[1] == "healthcheck":
        sys.exit(healthcheck(settings))
    conn = sync_redis(settings.redis_url, blocking=True)
    Path(settings.heartbeat_file).write_text(str(time.time()))
    # the hourly tick lives in Redis only: check it on RQ's maintenance schedule, so it comes
    # back after a Redis restart instead of waiting for the next worker restart
    maintenance = [ensure_scheduled] if "default" in settings.worker_queues else []
    run_worker(conn, settings.worker_queues, with_scheduler=True, maintenance=maintenance)


if __name__ == "__main__":
    main()
