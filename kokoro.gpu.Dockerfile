FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    pip install uv && \
    rm -rf /var/lib/apt/lists/*

# Clone the Kokoro-FastAPI repository
RUN git clone https://github.com/remsky/Kokoro-FastAPI.git /app
WORKDIR /app

# Set environment variables from the run script
ENV USE_GPU=true
ENV USE_ONNX=false
ENV PYTHONPATH=/app:/app/api
ENV MODEL_DIR=src/models
ENV VOICES_DIR=src/voices/v1_0
ENV WEB_PLAYER_PATH=/app/web

# Install dependencies
RUN uv pip install --system -e ".[gpu]"

# Download the model
RUN uv run --no-sync python docker/scripts/download_model.py --output api/src/models/v1_0

# Expose the port
EXPOSE 8880

# Run the server
CMD ["uv", "run", "--no-sync", "uvicorn", "api.src.main:app", "--host", "0.0.0.0", "--port", "8880"]
