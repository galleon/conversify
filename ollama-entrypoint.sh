#!/bin/sh
set -eu  # no pipefail in /bin/sh

: "${OLLAMA_HOST:=0.0.0.0}"
: "${OLLAMA_AUTOPULL:=}"
: "${OLLAMA_NO_MMAP:=}"
READINESS_TIMEOUT="${READINESS_TIMEOUT:-120}"

echo "Starting Ollama server on ${OLLAMA_HOST}..."
ollama serve &
SERVE_PID=$!

trap 'kill -TERM "$SERVE_PID" 2>/dev/null || true; wait "$SERVE_PID" || true' INT TERM EXIT

echo "Waiting for Ollama server to be ready..."
i=0
while ! ollama list >/dev/null 2>&1; do
  i=$((i+1))
  [ "$i" -ge "$READINESS_TIMEOUT" ] && { echo "Timeout waiting for Ollama"; exit 1; }
  sleep 1
done
echo "Ollama is ready."

MODELS="${OLLAMA_AUTOPULL:-nomic-embed-text qwen2.5vl}"
echo "Ensuring models: $MODELS"

# Cache tags once; if it fails, create empty file so we try pulls
if ! ollama list >/tmp/ollama_tags 2>/dev/null; then : > /tmp/ollama_tags; fi

for m in $MODELS; do
  if grep -q "^$m[[:space:]]" /tmp/ollama_tags; then
    echo "Model already present: $m"
  else
    echo "Pulling $m..."
    ollama pull "$m" || echo "Failed to pull $m"
  fi
done

wait "$SERVE_PID"
