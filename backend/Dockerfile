# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the virtualenv.
#
# Split from the runtime stage so compilers and build headers never ship in the
# final image - they are a large attack surface for something the app never
# needs once the wheels are built.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# build-essential is needed by a few wheels that have no manylinux build for
# this platform; it is discarded with this stage.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Torch FIRST, and from PyTorch's CPU index.
#
# This is the single most important line in the file. `pip install torch` from
# PyPI pulls the CUDA build: ~2.5GB of GPU libraries for a machine that has no
# GPU. The CPU wheel is ~200MB. Installing it first means sentence-transformers
# then sees the requirement already satisfied and does not pull the CUDA one.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements.txt .
RUN pip install -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 2: bake the embedding model into the image.
#
# Downloading all-MiniLM-L6-v2 at startup would make every cold start wait on
# Hugging Face, and a deploy would fail outright if HF were down. Baking it in
# trades ~90MB of image size for a deterministic, offline-capable boot.
# ---------------------------------------------------------------------------
FROM builder AS model

ENV PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf

RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
print('model cached')"


# ---------------------------------------------------------------------------
# Stage 3: the runtime image.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf \
    # Offline mode: the model is already in the image, so any attempt to reach
    # Hugging Face at runtime is a bug we want to fail loudly rather than a
    # silent 90MB download on a user's first request.
    HF_HUB_OFFLINE=1 \
    PORT=8000

# curl is for the healthcheck below; nothing else is added.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user. If the app is ever exploited, the attacker lands as
# an unprivileged account that cannot write to the image.
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=model /opt/hf /opt/hf

WORKDIR /app
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./data ./data

# The temp upload directory must be writable by appuser; every other path is
# read-only to the running process.
RUN mkdir -p /app/data/temp && chown -R appuser:appuser /app/data/temp

USER appuser

EXPOSE 8000

# Hits the real endpoint, so the check fails if the app is up but broken.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# Exec form wrapping an explicit shell. The shell is needed so ${PORT} is
# expanded - Render and most PaaS hosts inject the port they want the app to
# listen on, and it is not always 8000. Writing it as a JSON array keeps the
# process as PID 1's direct child so SIGTERM reaches uvicorn and shutdown is
# graceful, which bare shell form does not guarantee.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
