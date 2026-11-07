"""Shared OpenAI-compatible client factory (OpenAI itself, or e.g. a LiteLLM proxy)."""

from __future__ import annotations

import os

from .config import AiConfig

DUMMY_KEY = "not-needed"  # some proxies (LiteLLM without auth) ignore the key


def api_key_present(ai: AiConfig) -> bool:
    return bool(os.environ.get(ai.api_key_env))


def make_client(ai: AiConfig):
    """Build an openai.AsyncOpenAI. base_url is passed only when set."""
    import openai

    kwargs: dict = {}
    key = os.environ.get(ai.api_key_env)
    if ai.base_url:
        kwargs["base_url"] = ai.base_url
        key = key or DUMMY_KEY
    if not key:
        raise ValueError(f"API key not found: set the {ai.api_key_env} environment variable")
    return openai.AsyncOpenAI(api_key=key, **kwargs)
