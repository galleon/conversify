# Use a standard Python base image
FROM python:3.11-slim

# Install Python and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install torch sglang

# Set the command to run the LLM server
CMD ["python3", "-m", "sglang.launch_server", "--model-path", "Qwen/Qwen2.5-VL-7B-Instruct-AWQ", "--chat-template=qwen2-vl", "--mem-fraction-static=0.6", "--tool-call-parser", "qwen25"]
