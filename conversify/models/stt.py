import dataclasses
import logging
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
import soundfile as sf

from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    stt,
)
from livekit.agents.types import NotGivenOr, NOT_GIVEN
from livekit.agents.utils import AudioBuffer

from .utils import WhisperModels, find_time
import platform
import io

# Import both whisper implementations
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None

try:
    import whisper  # type: ignore
    OPENAI_WHISPER_AVAILABLE = True
except ImportError:
    OPENAI_WHISPER_AVAILABLE = False
    whisper = None

logger = logging.getLogger(__name__)

@dataclass
class WhisperOptions:
    """Configuration options for WhisperSTT."""
    language: str
    model: WhisperModels | str
    backend: str = "faster-whisper"  # "faster-whisper" or "openai"
    device: str | None = None
    compute_type: str | None = None
    model_cache_directory: str | None = None
    warmup_audio: str | None = None
    cpu_threads: int | None = None
    num_workers: int | None = None
    beam_size: int = 1
    best_of: int = 1
    word_timestamps: bool = False
    vad_filter: bool = False
    vad_min_silence_ms: int = 500
    condition_on_previous_text: bool = True
    initial_prompt: str | None = None


class WhisperSTT(stt.STT):
    """STT implementation using Whisper model."""

    def __init__(
        self,
        config: dict[str, Any]
    ):
        """Initialize the WhisperSTT instance.

        Args:
            config: Configuration dictionary (from config.yaml)
        """
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )

        stt_config = config['stt']['whisper']

        language = stt_config['language']
        model = stt_config['model']
        backend = stt_config.get('backend', 'faster-whisper')
        device = stt_config['device']
        compute_type = stt_config['compute_type']
        model_cache_directory = stt_config['model_cache_directory']
        warmup_audio = stt_config['warmup_audio']

        self._opts = WhisperOptions(
            language=language,
            model=model,
            backend=backend,
            device=device,
            compute_type=compute_type,
            model_cache_directory=model_cache_directory,
            warmup_audio=warmup_audio
        )

        # Validate backend availability
        if self._opts.backend == "faster-whisper" and not FASTER_WHISPER_AVAILABLE:
            raise ImportError("faster-whisper is not available. Install it with: pip install faster-whisper")
        elif self._opts.backend == "openai" and not OPENAI_WHISPER_AVAILABLE:
            raise ImportError("openai-whisper is not available. Install it with: pip install openai-whisper")
        elif self._opts.backend not in ["faster-whisper", "openai"]:
            raise ValueError(f"Unsupported backend: {self._opts.backend}. Use 'faster-whisper' or 'openai'")

        self._model = None
        self._initialize_model()

        # Warmup the model with a sample audio if available
        if warmup_audio and os.path.exists(warmup_audio):
            self._warmup(warmup_audio)

    def _default_device(self, device_cfg: str | None = None) -> str:
        if device_cfg:
            return device_cfg
        # Correct Apple Silicon detection
        try:
            sys_name = platform.system()      # "Darwin" on macOS
            arch = platform.machine()         # "arm64" on Apple Silicon
        except Exception:
            return "cpu"
        if sys_name == "Darwin" and arch in ("arm64", "aarch64"):
            return "metal"
        return "cpu"

    def _default_compute(self, compute_cfg: str | None, device: str) -> str:
        if compute_cfg:
            return compute_cfg
        if device == "metal":
            return "int8_float16"
        return "int8"

    def _initialize_model(self):
        """Initialize the Whisper model."""
        logger.info(f"Initializing Whisper model with backend: {self._opts.backend}")

        if self._opts.backend == "faster-whisper":
            self._initialize_faster_whisper()
        elif self._opts.backend == "openai":
            self._initialize_openai_whisper()
        else:
            raise ValueError(f"Unsupported backend: {self._opts.backend}")

        logger.info("Whisper model loaded successfully")

    def _initialize_faster_whisper(self):
        """Initialize faster-whisper model."""
        if WhisperModel is None:
            raise ImportError("faster-whisper is not available")

        device = self._default_device(self._opts.device)
        compute_type = self._default_compute(self._opts.compute_type, device)

        logger.info(f"Using device: {device}, with compute: {compute_type}")

        # Ensure cache directories exist
        model_cache_dir = (
            os.path.expanduser(self._opts.model_cache_directory)
            if self._opts.model_cache_directory else None
        )

        if model_cache_dir:
            os.makedirs(model_cache_dir, exist_ok=True)
            logger.info(f"Using model cache directory: {model_cache_dir}")

        self._model = WhisperModel(
            model_size_or_path=str(self._opts.model),
            device=device,
            compute_type=compute_type,
            download_root=model_cache_dir,
            cpu_threads=self._opts.cpu_threads or 0,
            num_workers=self._opts.num_workers or 1,
        )

    def _initialize_openai_whisper(self):
        """Initialize OpenAI whisper model."""
        if whisper is None:
            raise ImportError("openai-whisper is not available")

        # For OpenAI whisper, device handling is simpler
        device = self._default_device(self._opts.device)
        if device == "metal":
            device = "cuda"  # OpenAI whisper doesn't support Metal directly

        logger.info(f"Using device: {device}")

        # Ensure cache directories exist
        model_cache_dir = (
            os.path.expanduser(self._opts.model_cache_directory)
            if self._opts.model_cache_directory else None
        )

        if model_cache_dir:
            os.makedirs(model_cache_dir, exist_ok=True)
            logger.info(f"Using model cache directory: {model_cache_dir}")
            # Set the cache directory for OpenAI whisper
            os.environ["WHISPER_CACHE_DIR"] = model_cache_dir

        self._model = whisper.load_model(str(self._opts.model), device=device)

    def _warmup(self, warmup_audio_path: str) -> None:
        """Performs a warmup transcription.

        Args:
            warmup_audio_path: Path to audio file for warmup
        """
        logger.info(f"Starting STT engine warmup using {warmup_audio_path}...")
        try:
            with find_time('STT_warmup'):
                audio, _ = sf.read(warmup_audio_path, dtype="float32")
                if audio.ndim > 1:
                    audio = np.mean(audio, axis=1)

                if self._opts.backend == "faster-whisper":
                    if self._model is None:
                        raise RuntimeError("Faster-whisper model not initialized")
                    segments, _ = self._model.transcribe(
                        audio,
                        language=self._opts.language,
                        beam_size=self._opts.beam_size,
                    )
                    text = " ".join(s.text for s in segments)
                else:  # openai
                    if self._model is None:
                        raise RuntimeError("OpenAI whisper model not initialized")
                    result = self._model.transcribe(
                        audio,
                        language=self._opts.language,
                        beam_size=self._opts.beam_size,
                        best_of=self._opts.best_of,
                    )
                    text = result.get("text", "") if isinstance(result, dict) else ""

            logger.info(f"STT engine warmed up. Text: {text}")
        except Exception as e:
            logger.error(f"Failed to warm up STT engine: {e}")

    def update_options(
        self,
        *,
        model: WhisperModels | str | None = None,
        language: str | None = None,
        model_cache_directory: str | None = None,
    ) -> None:
        """Update STT options.

        Args:
            model: Whisper model to use
            language: Language to detect
            model_cache_directory: Directory to store downloaded models
        """
        reinitialize = False

        if model:
            self._opts.model = model
            reinitialize = True

        if model_cache_directory:
            self._opts.model_cache_directory = model_cache_directory
            reinitialize = True

        if language:
            self._opts.language = language

        if reinitialize:
            self._initialize_model()

    def _sanitize_options(self, *, language: str | None = None) -> WhisperOptions:
        """Create a copy of options with optional overrides.

        Args:
            language: Language override

        Returns:
            Copy of options with overrides applied
        """
        options = dataclasses.replace(self._opts)
        if language:
            options.language = language
        return options

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """Implement speech recognition.

        Args:
            buffer: Audio buffer
            language: Language to detect
            conn_options: Connection options

        Returns:
            Speech recognition event
        """
        # Convert NotGivenOr to str | None for internal use
        lang: str | None = None
        if language is not NOT_GIVEN:
            lang = str(language) if language is not None else None
        try:
            logger.info("Received audio, transcribing to text")
            options = self._sanitize_options(language=lang)
            wav_bytes = rtc.combine_audio_frames(buffer).to_wav_bytes()

            # Parse WAV from bytes (don't np.frombuffer raw!)
            audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
            if audio.ndim > 1:               # downmix to mono
                audio = np.mean(audio, axis=1)

            with find_time('STT_inference'):
                if self._opts.backend == "faster-whisper":
                    if self._model is None:
                        raise RuntimeError("Faster-whisper model not initialized")
                    segments, info = self._model.transcribe(
                        audio,
                        language=options.language,
                        beam_size=self._opts.beam_size,
                        best_of=self._opts.best_of,
                        condition_on_previous_text=self._opts.condition_on_previous_text,
                        vad_filter=self._opts.vad_filter,
                        vad_parameters={"min_silence_duration_ms": self._opts.vad_min_silence_ms},
                        word_timestamps=self._opts.word_timestamps,
                        initial_prompt=self._opts.initial_prompt,
                    )
                    full_text = " ".join(s.text.strip() for s in segments)
                else:  # openai
                    if self._model is None:
                        raise RuntimeError("OpenAI whisper model not initialized")
                    result = self._model.transcribe(
                        audio,
                        language=options.language,
                        beam_size=self._opts.beam_size,
                        best_of=self._opts.best_of,
                        condition_on_previous_text=self._opts.condition_on_previous_text,
                        word_timestamps=self._opts.word_timestamps,
                        initial_prompt=self._opts.initial_prompt,
                    )
                    full_text = result.get("text", "").strip() if isinstance(result, dict) else ""
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text=full_text or "", language=options.language)],
            )
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}", exc_info=True)
            raise APIConnectionError() from e
