FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Ensure uv uses the container's interpreter to create the venv
    UV_PYTHON=/usr/local/bin/python

# System deps for native builds + Rust + git
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential gcc g++ make \
        python3-dev pkg-config \
        cargo rustc \
        git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Get source
WORKDIR /app
RUN git clone https://github.com/remsky/Kokoro-FastAPI.git /app

# Create venv with uv (tied to container python)
RUN uv venv /opt/venv

# Bind future commands to the project venv
ENV PATH="/opt/venv/bin:${PATH}" \
    UV_PYTHON=/opt/venv/bin/python

# (Optional) upgrade base build tools for better wheel resolution
RUN uv pip install -U pip setuptools wheel

# Install project into the venv
RUN uv pip install -e .

# Download the model using the SAME venv/interpreter (no new .venv)
RUN /opt/venv/bin/python docker/scripts/download_model.py --output api/src/models/v1_0


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:${PATH}"

# Runtime-only packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
        libstdc++6 \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Bring in the app and the prepared venv
COPY --from=builder /app /app
COPY --from=builder /opt/venv /opt/venv

# App env
ENV USE_GPU=false \
    USE_ONNX=false \
    PYTHONPATH=/app:/app/api \
    MODEL_DIR=src/models \
    VOICES_DIR=src/voices/v1_0 \
    WEB_PLAYER_PATH=/app/web

WORKDIR /app
EXPOSE 8880

# Run uvicorn directly from the venv (no uv run, no extra envs)
CMD ["uvicorn", "api.src.main:app", "--host", "0.0.0.0", "--port", "8880"]
