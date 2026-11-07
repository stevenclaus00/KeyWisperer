"""Speech-to-text providers. To add one: create a module and register it below."""

from __future__ import annotations

from ..config import AiConfig, TranscriptionConfig
from .base import Transcriber


def build_transcriber(config: TranscriptionConfig, ai: AiConfig | None = None) -> Transcriber:
    """Create the transcriber named by config.provider."""
    if config.provider == "openai":
        from ..ai import make_client
        from .openai_backend import OpenAITranscriber

        return OpenAITranscriber(config.model, config.language, config.vocabulary,
                                 client=make_client(ai or AiConfig()))
    raise ValueError(f"Unknown transcription provider: {config.provider!r}")


__all__ = ["Transcriber", "build_transcriber"]
