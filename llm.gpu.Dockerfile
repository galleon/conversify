# Use a CUDA-enabled base image
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# Install Python and other dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install torch sglang

# Set the command to run the LLM server
CMD ["python3", "-m", "sglang.launch_server", "--model-path", "Qwen/Qwen2.5-VL-7B-Instruct-AWQ", "--chat-template=qwen2-vl", "--mem-fraction-static=0.6", "--tool-call-parser", "qwen25"]
