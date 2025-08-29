import io
import wave
from types import SimpleNamespace

import numpy as np
import pytest

import conversify.models.stt as mod
from conversify.models.stt import WhisperSTT


@pytest.mark.asyncio
async def test_whisperstt_transcribe_returns_text_on_mac(monkeypatch):
    monkeypatch.setattr(mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(mod.platform, "machine", lambda: "arm64")

    class FakeSegment:
        def __init__(self, text: str):
            self.text = text

    class FakeWhisperModel:
        def __init__(
            self,
            model_size_or_path,
            device,
            compute_type,
            download_root,
            cpu_threads,
            num_workers,
        ):
            # store for inspection if needed
            self.model_size_or_path = model_size_or_path
            self.device = device
            self.compute_type = compute_type
            self.download_root = download_root
            self.cpu_threads = cpu_threads
            self.num_workers = num_workers

        def transcribe(self, audio, **kwargs):
            # Return a single segment "hello world"
            return [FakeSegment("hello world")], SimpleNamespace(
                duration=0.2, language=kwargs.get("language")
            )

    monkeypatch.setattr(mod, "WhisperModel", FakeWhisperModel)

    def make_wav_bytes(sr=16000, seconds=0.2):
        t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
        sig = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        pcm = np.clip(sig * 32767, -32768, 32767).astype(np.int16)

        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        return bio.getvalue()

    class FakeCombinedFrames:
        def to_wav_bytes(self):
            return make_wav_bytes()

    monkeypatch.setattr(
        mod.rtc, "combine_audio_frames", lambda _buffer: FakeCombinedFrames()
    )

    config = {
        "stt": {
            "whisper": {
                "language": "en",
                "model": "small",
                "backend": "faster-whisper",
                "device": None,
                "compute_type": None,
                "model_cache_directory": None,
                "warmup_audio": None,
            }
        }
    }

    stt_inst = WhisperSTT(config)

    # Sanity check: with our patched platform, it should prefer "metal"
    assert stt_inst._default_device(None) == "metal"

    from livekit.agents import APIConnectOptions

    event = await stt_inst._recognize_impl(
        buffer=None,
        language="en",
        conn_options=APIConnectOptions(),
    )

    assert event.type == mod.stt.SpeechEventType.FINAL_TRANSCRIPT
    assert event.alternatives[0].text == "hello world"
    assert event.alternatives[0].language == "en"
