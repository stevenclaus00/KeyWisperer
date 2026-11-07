import io
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from keywhisperer.config import TranscriptionConfig
from keywhisperer.transcribe import build_transcriber
from keywhisperer.transcribe.openai_backend import OpenAITranscriber, pcm_to_wav


def fake_client(text=" hello world "):
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(return_value=SimpleNamespace(text=text))
    return client


def test_wav_header():
    pcm = b"\x01\x00" * 1600
    w = wave.open(io.BytesIO(pcm_to_wav(pcm, 16000)))
    assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 1600)


async def test_transcribe_call():
    client = fake_client()
    t = OpenAITranscriber("whisper-1", "en", ["Kubernetes", "Foo"], client=client)
    out = await t.transcribe(b"\x00\x00" * 160, 16000, prompt="x" * 500)
    assert out == "hello world"
    kw = client.audio.transcriptions.create.call_args.kwargs
    assert kw["model"] == "whisper-1" and kw["language"] == "en"
    name, data, mime = kw["file"]
    assert (name, mime) == ("utterance.wav", "audio/wav") and data[:4] == b"RIFF"
    assert kw["prompt"] == "Kubernetes, Foo " + "x" * 200


async def test_no_prompt_when_empty():
    client = fake_client()
    await OpenAITranscriber(client=client).transcribe(b"\x00\x00", 16000)
    assert "prompt" not in client.audio.transcriptions.create.call_args.kwargs


def test_build_transcriber(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    assert isinstance(build_transcriber(TranscriptionConfig()), OpenAITranscriber)
