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
COPY apps/gpu-worker apps/gpu-worker
RUN --mount=type=secret,id=extra_ca,required=false --mount=type=cache,target=/root/.cache/uv \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca PIP_CERT=/run/secrets/extra_ca; fi; uv sync --frozen --no-dev --package handball-gpu-worker --no-editable

# Model weights (ADR 003/025): pinned release and checksum, never in the repository
FROM base AS models
ARG YOLOX_URL=https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx
ARG YOLOX_SHA256=c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    mkdir -p /models && python -c "import os,urllib.request,ssl; ctx=ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE')); open('/models/yolox_s.onnx','wb').write(urllib.request.urlopen('${YOLOX_URL}', context=ctx).read())" \
    && echo "${YOLOX_SHA256}  /models/yolox_s.onnx" | sha256sum -c -
# Shirt numbers (ADR 027): PP-OCRv4 text models (PaddleOCR, Apache-2.0) from the pinned
# rapidocr_onnxruntime wheel on PyPI (Apache-2.0); only the two model files are kept
ARG RAPIDOCR_VERSION=1.4.4
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    python -m pip download --no-deps --no-cache-dir -d /tmp/wheel "rapidocr_onnxruntime==${RAPIDOCR_VERSION}" \
    && python -c "import zipfile,glob; z=zipfile.ZipFile(glob.glob('/tmp/wheel/*.whl')[0]); [open('/models/'+n.split('/')[-1],'wb').write(z.read(n)) for n in z.namelist() if n.endswith(('_PP-OCRv4_det_infer.onnx','_PP-OCRv4_rec_infer.onnx'))]" \
    && rm -rf /tmp/wheel \
    && echo "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9  /models/ch_PP-OCRv4_det_infer.onnx" | sha256sum -c - \
    && echo "48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b  /models/ch_PP-OCRv4_rec_infer.onnx" | sha256sum -c -

# CPU fallback image. The CUDA image (Dockerfile.cuda) follows in M3 with onnxruntime-gpu + NVDEC.
FROM python:3.12-slim AS runtime
# Tesseract (Apache-2.0) reads score and match clock from broadcast overlays (scoreboard.py)
# security updates of the base image first (the scan fails on fixed HIGH/CRITICAL CVEs)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* && useradd --system --uid 10001 app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=models /models /models
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD ["handball-gpu-worker", "healthcheck"]
CMD ["handball-gpu-worker"]
