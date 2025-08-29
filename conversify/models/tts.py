import logging
from dataclasses import dataclass, replace
from typing import Any, cast

import httpx
import openai
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    tts,
    utils,
)
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    NotGivenOr,
)
from livekit.agents.utils import is_given

from .utils import FindTime, TTSModels, TTSVoices

logger = logging.getLogger(__name__)

TTS_SAMPLE_RATE = 24000
TTS_CHANNELS = 1


@dataclass
class KokoroTTSOptions:
    model: TTSModels | str
    voice: TTSVoices | str
    speed: float


class KokoroTTS(tts.TTS):
    def __init__(
        self,
        config: dict[str, Any],
        client: openai.AsyncClient | None = None,
    ) -> None:
        tts_config = config["tts"]["kokoro"]

        model = tts_config["model"]
        voice = tts_config["voice"]
        speed = tts_config["speed"]
        api_key = tts_config["api_key"]
        base_url = tts_config["base_url"]

        logger.info(f"Using TTS API URL: {base_url}")

        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=TTS_SAMPLE_RATE,
            num_channels=TTS_CHANNELS,
        )

        logger.info(
            "KokoroTTS init: streaming=%s, sr=%s, ch=%s, model=%s, voice=%s, speed=%s, base_url=%s",
            self.capabilities.streaming,
            self.sample_rate,
            self.num_channels,
            model,
            voice,
            speed,
            base_url,
        )

        self._opts = KokoroTTSOptions(model=model, voice=voice, speed=speed)

        self._client = client or openai.AsyncClient(
            max_retries=0,
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=5.0, write=5.0, pool=5.0),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=50,
                    keepalive_expiry=120,
                ),
            ),
        )

    def update_options(
        self,
        *,
        model: NotGivenOr[TTSModels | str] = NOT_GIVEN,
        voice: NotGivenOr[TTSVoices | str] = NOT_GIVEN,
        speed: NotGivenOr[float] = NOT_GIVEN,
    ) -> None:
        if is_given(model):
            self._opts.model = model
        if is_given(voice):
            self._opts.voice = voice
        if is_given(speed):
            self._opts.speed = speed

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "KokoroTTSStream":
        # IMPORTANT for livekit.agents 1.2.x: pass only the expected keywords;
        # extra kwargs (like opts=, client=) will break ChunkedStream.__init__.
        return KokoroTTSStream(tts=self, input_text=text, conn_options=conn_options)


class KokoroTTSStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: KokoroTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        # copy options so per-stream mutations (if any) don't affect the TTS instance
        self._opts = replace(tts._opts)
        self._client = tts._client

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        request_id = utils.shortuuid()

        logger.info(
            "KokoroTTSStream start: req=%s model=%s voice=%s speed=%s",
            request_id,
            self._opts.model,
            self._opts.voice,
            self._opts.speed,
        )

        try:
            with FindTime("TTS_inferencing"):
                async with self._client.audio.speech.with_streaming_response.create(
                    input=self._input_text,
                    model=cast(Any, self._opts.model),
                    voice=cast(Any, self._opts.voice),
                    response_format="pcm",
                    speed=self._opts.speed,
                    timeout=httpx.Timeout(30, connect=self._conn_options.timeout),
                ) as stream:
                    # tell LiveKit about the stream we're about to push
                    output_emitter.initialize(
                        request_id=request_id,
                        sample_rate=self._tts.sample_rate,
                        num_channels=TTS_CHANNELS,
                        mime_type="audio/pcm",
                    )
                    async for data in stream.iter_bytes():
                        output_emitter.push(data)

            logger.info("KokoroTTSStream done: req=%s", request_id)

        except openai.APITimeoutError:
            raise APITimeoutError() from None
        except openai.APIStatusError as e:
            raise APIStatusError(
                e.message,
                status_code=e.status_code,
                request_id=e.request_id,
                body=e.body,
            ) from None
        except Exception:
            raise APIConnectionError() from None
