"""OpenAI speech-to-text backend."""

from __future__ import annotations

import io
import wave

CONTEXT_CHARS = 200


def pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap 16-bit mono PCM in an in-memory WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


class OpenAITranscriber:
    """Uses the OpenAI audio API. Reads OPENAI_API_KEY from the environment."""

    def __init__(self, model: str = "whisper-1", language: str = "en",
                 vocabulary: list[str] | None = None, client=None):
        if client is None:
            import openai

            client = openai.AsyncOpenAI()
        self.client = client
        self.model = model
        self.language = language
        self.vocabulary = vocabulary or []

    def build_prompt(self, previous_text: str | None) -> str | None:
        """Vocabulary hint + tail of what was already typed (helps continuity)."""
        parts = []
        if self.vocabulary:
            parts.append(", ".join(self.vocabulary))
        if previous_text:
            parts.append(previous_text[-CONTEXT_CHARS:])
        return " ".join(parts) or None

    async def transcribe(self, pcm: bytes, sample_rate: int, prompt: str | None = None) -> str:
        kwargs = {}
        if self.language:
            kwargs["language"] = self.language
        full_prompt = self.build_prompt(prompt)
        if full_prompt:
            kwargs["prompt"] = full_prompt
        result = await self.client.audio.transcriptions.create(
            model=self.model,
            file=("utterance.wav", pcm_to_wav(pcm, sample_rate), "audio/wav"),
            **kwargs,
        )
        return (getattr(result, "text", "") or "").strip()
