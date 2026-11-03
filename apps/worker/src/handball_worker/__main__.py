from __future__ import annotations

import sys
import time
from pathlib import Path

from redis import Redis
from rq import Queue, Worker

from handball_worker.config import WorkerSettings
from handball_worker.ticks import ensure_scheduled


def healthcheck(settings: WorkerSettings) -> int:
    """Container healthcheck: Redis reachable and a worker registered."""
    conn = Redis.from_url(settings.redis_url)
    conn.ping()
    return 0 if Worker.all(connection=conn) else 1


def main() -> None:
    settings = WorkerSettings()
    if len(sys.argv) > 1 and sys.argv[1] == "healthcheck":
        sys.exit(healthcheck(settings))
    conn = Redis.from_url(settings.redis_url)
    Path(settings.heartbeat_file).write_text(str(time.time()))
    queues = [Queue(name, connection=conn) for name in settings.worker_queues]
    if "default" in settings.worker_queues:
        ensure_scheduled(conn)
    Worker(queues, connection=conn).work(with_scheduler=True)


if __name__ == "__main__":
    main()
