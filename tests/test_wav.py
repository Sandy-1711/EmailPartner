from __future__ import annotations

import io
import wave

from app.infrastructure.llm.providers.gemini import _pcm_to_wav


def test_pcm_to_wav_produces_valid_container():
    frames = 240  # 10ms of 24kHz mono 16-bit audio
    pcm = b"\x01\x02" * frames

    wav_bytes = _pcm_to_wav(pcm)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 24000
        assert wav.getnframes() == frames
        assert wav.readframes(frames) == pcm
