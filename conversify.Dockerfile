FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install uv
RUN uv pip install -e .

CMD ["python", "-m", "conversify.main", "start"]
