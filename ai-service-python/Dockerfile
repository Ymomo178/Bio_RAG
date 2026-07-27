# Python 3.12 镜像同时支持 CPU 和 NVIDIA GPU 推理。
ARG DOCKER_REGISTRY=docker.io
FROM ${DOCKER_REGISTRY}/library/python:3.12-slim

ARG TORCH_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/huggingface

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install "torch==${TORCH_VERSION}" --index-url "${TORCH_INDEX_URL}" \
    && python -m pip install ".[embedding,service]" \
    && mkdir -p /app/uploads /app/artifacts/uploads /models/huggingface

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["biorag-api"]
