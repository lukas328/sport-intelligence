import os

import uvicorn


def main() -> None:
    # one process per core (capped); each has its own DB pool (pool_size 10 + overflow 10)
    workers = int(os.environ.get("HB_WORKERS", str(min(4, os.cpu_count() or 1))))
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
