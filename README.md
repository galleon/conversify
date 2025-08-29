# Conversify 🗣️ ✨

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Conversify is a real‑time, low‑latency, voice- and vision-enabled AI assistant built on LiveKit. This project demonstrates highly responsive conversational AI workflows, leveraging locally hosted models.

## Demo Video

[![Watch the demo](assets/thumbnail.jpg)](https://youtu.be/Biva5VGV5Pg)


## ✨ Key Features

- ⚡ **Low Latency**: End-to-end response time under 600 ms.
- 🗣️ **Real‑time Voice**: Natural conversation using local STT and TTS services.
- 🧠 **Local LLM Integration**: Compatible with any OpenAI‑style API (e.g., SGLang, vLLM, Ollama).
- 👀 **Basic Vision**: Processes video frames with multimodal LLM prompts.
- 💾 **Conversational Memory**: Persists context across user sessions.
- 🔧 **Configurable**: All settings managed via `config/config.yaml`.

---

## ⚙️ Prerequisites

- **OS**: Linux or WSL on Windows (tested)
- **Python**: 3.11+
- **Services**:
  - LiveKit Server Cloud (sign up at https://cloud.livekit.io)
  - An LLM inference server with OpenAI-compatible API (e.g., SGLang, vLLM, Ollama)
  - Kokoro FastAPI TTS server (https://github.com/remsky/Kokoro-FastAPI)

---

## 🛠️ Installation

1. **Clone the repository**

    ```bash
    git clone https://github.com/taresh18/conversify.git
    cd conversify
    ```

2. **Create a virtual environment**

    ```bash
    uv venv
    source .venv/bin/activate    # Linux/macOS
    # .venv\Scripts\activate   # Windows
    ```

3. **Install dependencies**

    ```bash
    uv pip install -e .
    python -m conversify.main download-files 
    ```

4. **Configure environment variables**

    ```bash
    cp .env.example .env.local
    nano .env.local  # Add your LiveKit and other credentials
    ```

5. **Update `config.toml`**

    ```bash
    cp config.example.toml config.toml
    nano config.toml  # Customize for your setup
    ```

    - Set LLM API endpoint and model names
    - Configure STT backend (faster-whisper or OpenAI Whisper) and parameters
    - Configure TTS server URLs and parameters
    - Adjust vision and memory settings as needed

6. **Install optional STT backend (if using OpenAI Whisper)**

    ```bash
    uv pip install -e ".[openai-whisper]"
    ```

---

## 🏃 Running the Application

Ensure all external services are running before starting Conversify.

1. **Start the LLM server** (example using provided script)

    ```bash
    chmod +x ./scripts/run_llm.sh
    ./scripts/run_llm.sh &
    ```

2. **Start the Kokoro TTS server**

    ```bash
    chmod +x ./scripts/run_kokoro.sh
    ./scripts/run_kokoro.sh &
    ```

3. **Launch Conversify**

    ```bash
    chmod +x ./scripts/run_app.sh
    ./scripts/run_app.sh
    ```

4. **Interact via LiveKit Agents Playground**

    - Navigate to https://agents-playground.livekit.io
    - Select your LiveKit project and room
    - Join and begin conversation

---

## 🐳 Running with Docker

This project includes a Docker setup to run the entire application stack in containers. This is the recommended way to run the application.

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with drivers (for GPU mode)
- A `.env.local` file with your LiveKit credentials (see [Installation](#-installation))

### Running in CPU Mode

This mode is suitable for machines without a dedicated NVIDIA GPU, such as a MacBook.

```bash
docker-compose -f docker-compose.cpu.yml up --build
```

### Running in GPU Mode

This mode provides the best performance by leveraging an NVIDIA GPU for the AI models.

```bash
docker-compose -f docker-compose.gpu.yml up --build
```

---

## ⚙️ Configuration

All runtime settings are in `config.toml` (see `config.example.toml` for a comprehensive example with comments). Key options include:

- **STT**: backend selection (`faster-whisper` or `openai`), model selection and parameters
- **LLM**: endpoint URLs and model names
- **TTS**: voice options and server settings
- **Vision**: enable/disable frame analysis and thresholds
- **Memory**: persistence and retrieval parameters
- **Logging**: level and file path (`app.log`)

### STT Backend Options

The application supports two Whisper backends:

- **faster-whisper** (default): Optimized for speed and lower memory usage
- **openai**: Original OpenAI Whisper implementation

Configure in `config.toml`:
```toml
[stt.whisper]
backend = "faster-whisper"  # or "openai"
model = "large-v3"
language = "en"
# ... other options
```

Secrets and credentials reside in `.env.local`, following the template in `.env.example`.

---

## 🏗️ Project Structure

```plaintext
conversify/
├── conversify/
│   ├── core/               # Orchestration and agent logic
│   ├── models/             # STT, TTS, and LLM model integrations
│   ├── prompts/            # LLM system prompts
│   └── utils/              # Logger and shared utilities
├── scripts/
│   ├── run_llm.sh
│   ├── run_kokoro.sh
│   └── run_app.sh
├── config.toml             # All application settings
├── .env.example            # Template for environment variables
├── .env.local              # Local secrets (ignored)
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## 📚 References

- LiveKit Agents: https://github.com/livekit/agents
- Faster Whisper: https://github.com/SYSTRAN/faster-whisper
- Kokoro FastAPI: https://github.com/remsky/Kokoro-FastAPI
- Memoripy: https://github.com/caspianmoon/memoripy

---

## 📜 License

This project is released under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

