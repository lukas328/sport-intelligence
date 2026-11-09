# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never
# Optional extra CA (corporate TLS proxy): docker build --secret id=extra_ca,src=ca.crt
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca PIP_CERT=/run/secrets/extra_ca; fi; pip install --no-cache-dir uv==0.11.32
WORKDIR /app

FROM base AS build
COPY pyproject.toml uv.lock ./
COPY packages/court packages/court
COPY packages/vision packages/vision
COPY packages/jobkit packages/jobkit
COPY packages/metrics packages/metrics
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY apps/gpu-worker/pyproject.toml apps/gpu-worker/pyproject.toml
RUN mkdir -p apps/worker/src/handball_worker apps/gpu-worker/src/handball_gpu_worker apps/api/src/handball_api
COPY apps/api apps/api
RUN --mount=type=secret,id=extra_ca,required=false --mount=type=cache,target=/root/.cache/uv \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca PIP_CERT=/run/secrets/extra_ca; fi; uv sync --frozen --no-dev --package handball-api --no-editable

FROM python:3.12-slim AS runtime
# pdftotext (poppler-utils, GPL-2.0, called as a separate program) reads DHB press reports
# (services/official_report.py)
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/* && useradd --system --uid 10001 app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY apps/api/alembic.ini apps/api/alembic.ini
COPY apps/api/migrations apps/api/migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"
CMD ["handball-api"]
