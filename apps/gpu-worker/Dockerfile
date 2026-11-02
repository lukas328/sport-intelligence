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
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY apps/gpu-worker/pyproject.toml apps/gpu-worker/pyproject.toml
RUN mkdir -p apps/worker/src/handball_worker apps/gpu-worker/src/handball_gpu_worker apps/api/src/handball_api
COPY apps/gpu-worker apps/gpu-worker
RUN --mount=type=secret,id=extra_ca,required=false --mount=type=cache,target=/root/.cache/uv \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca PIP_CERT=/run/secrets/extra_ca; fi; uv sync --frozen --no-dev --package handball-gpu-worker --no-editable

# CPU fallback image. The CUDA image (Dockerfile.cuda) follows in M3 with onnxruntime-gpu + NVDEC.
FROM python:3.12-slim AS runtime
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD ["handball-gpu-worker", "healthcheck"]
CMD ["handball-gpu-worker"]
