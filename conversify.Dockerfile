FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    build-essential \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (standalone) and expose it on PATH
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir uv

WORKDIR /app
COPY . /app

RUN uv pip install --system -e .
# Use the system Python that uv just populated; no new .venv:
ENV HF_HOME=/opt/hf-cache \
    HUGGINGFACE_HUB_CACHE=/opt/hf-cache \
    KNOWLEDGE_API_HOST=0.0.0.0 \
    KNOWLEDGE_API_PORT=8080

# Create storage directories
RUN mkdir -p /opt/hf-cache /app/storage/knowledge /app/logs

# Download model files
RUN python -m conversify.main download-files || true

CMD ["python", "-m", "conversify.main"]
