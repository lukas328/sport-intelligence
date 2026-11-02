from __future__ import annotations

import sys

from redis import Redis
from rq import Queue, Worker

from handball_gpu_worker.config import GpuWorkerSettings


def main() -> None:
    settings = GpuWorkerSettings()
    conn = Redis.from_url(settings.redis_url)
    if len(sys.argv) > 1 and sys.argv[1] == "healthcheck":
        conn.ping()
        sys.exit(0)
    Worker([Queue(settings.gpu_queue, connection=conn)], connection=conn).work()


if __name__ == "__main__":
    main()
