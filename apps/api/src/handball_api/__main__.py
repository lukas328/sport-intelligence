import uvicorn


def main() -> None:
    uvicorn.run(
        "handball_api.main:create_app",
        factory=True,
        host="0.0.0.0",  # noqa: S104 (container)
        port=8000,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
