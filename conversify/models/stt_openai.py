import asyncio
import io
import logging
from dataclasses import dataclass
from typing import Any

from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    stt,
)
from livekit.agents.utils import AudioBuffer

import openai

logger = logging.getLogger(__name__)


@dataclass
class OpenAIWhisperOptions:
    """Configuration options for OpenAIWhisperSTT."""
    language: str
    model: str


class OpenAIWhisperSTT(stt.STT):
    """STT implementation using OpenAI's Whisper API."""

    def __init__(
        self,
        config: dict[str, Any]
    ):
        """Initialize the OpenAIWhisperSTT instance.

        Args:
            config: Configuration dictionary
        """
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )

        stt_config = config['stt']['openai']

        self._opts = OpenAIWhisperOptions(
            language=stt_config['language'],
            model=stt_config['model']
        )

        self._client = openai.AsyncClient(api_key=stt_config['api_key'])

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None = None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """Implement speech recognition using OpenAI Whisper API.

        Args:
            buffer: Audio buffer
            language: Language to detect
            conn_options: Connection options

        Returns:
            Speech recognition event
        """
        try:
            logger.info("Received audio, transcribing to text using OpenAI Whisper API")

            wav_bytes = rtc.combine_audio_frames(buffer).to_wav_bytes()

            # The OpenAI API expects a file-like object, so we wrap the bytes in an io.BytesIO
            # It also needs a file name, so we provide a dummy one.
            wav_file = ("input.wav", wav_bytes, "audio/wav")

            transcription = await self._client.audio.transcriptions.create(
                model=self._opts.model,
                file=wav_file,
                language=language or self._opts.language,
            )

            full_text = transcription.text or ""

            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text=full_text, language=language or self._opts.language)],
            )
        except Exception as e:
            logger.error(f"Error in OpenAI Whisper speech recognition: {e}", exc_info=True)
            raise APIConnectionError() from e
