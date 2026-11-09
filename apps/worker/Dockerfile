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
COPY apps/worker apps/worker
RUN --mount=type=secret,id=extra_ca,required=false --mount=type=cache,target=/root/.cache/uv \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca PIP_CERT=/run/secrets/extra_ca; fi; uv sync --frozen --no-dev --package handball-worker --no-editable

FROM python:3.12-slim AS runtime
# Static ffmpeg/ffprobe (x264, aac, fMP4 HLS). Pinned version; smaller and fewer CVEs than distro ffmpeg.
COPY --from=mwader/static-ffmpeg:7.1 /ffmpeg /ffprobe /usr/local/bin/
# security updates of the base image (the scan fails on fixed HIGH/CRITICAL CVEs)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 app && mkdir -p /tmp/handball-work && chown app /tmp/handball-work
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD ["handball-worker", "healthcheck"]
CMD ["handball-worker"]
