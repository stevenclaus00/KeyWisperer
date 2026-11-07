"""Shared OpenAI-compatible client factory (OpenAI itself, Ollama, speaches, LiteLLM...)."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from .config import AiConfig

DUMMY_KEY = "not-needed"  # local servers usually ignore the key
OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class Endpoint:
    base_url: str  # "" = official OpenAI API
    api_key_env: str  # NAME of the env var holding the key

    @property
    def key(self) -> str | None:
        return os.environ.get(self.api_key_env) or None

    @property
    def shown_url(self) -> str:
        return self.base_url or OPENAI_BASE_URL


def resolve_endpoint(ai: AiConfig, base_url: str = "", api_key_env: str = "") -> Endpoint:
    """Per-feature value -> [ai] value -> OpenAI default.

    If a feature points at a different server than [ai] and names no key env var of
    its own, we do NOT reuse [ai]'s key (that would send e.g. your OpenAI key to a
    local box); the dummy key is used instead.
    """
    url = base_url or ai.base_url
    if api_key_env:
        env = api_key_env
    elif base_url and base_url != ai.base_url:
        env = ""  # different server, no key configured
    else:
        env = ai.api_key_env
    return Endpoint(url, env)


def api_key_present(ai: AiConfig, base_url: str = "", api_key_env: str = "") -> bool:
    return resolve_endpoint(ai, base_url, api_key_env).key is not None


def make_client(ai: AiConfig, base_url: str = "", api_key_env: str = "", timeout: float | None = None):
    """Build an openai.AsyncOpenAI for one feature. base_url is passed only when set."""
    import openai

    ep = resolve_endpoint(ai, base_url, api_key_env)
    kwargs: dict = {}
    key = ep.key
    if ep.base_url:
        kwargs["base_url"] = ep.base_url
        key = key or DUMMY_KEY
    if not key:
        raise ValueError(f"API key not found: set the {ep.api_key_env} environment variable")
    if timeout is not None:
        kwargs["timeout"] = timeout
    return openai.AsyncOpenAI(api_key=key, **kwargs)


def list_models(ep: Endpoint, timeout: float = 3) -> list[str]:
    """GET <base_url>/models and return model ids. Raises OSError/ValueError on failure."""
    headers = {"Authorization": f"Bearer {ep.key}"} if ep.key else {}
    req = urllib.request.Request(ep.shown_url.rstrip("/") + "/models", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]


def check_endpoint(label: str, ep: Endpoint, model: str, timeout: float = 3) -> list[str]:
    """Doctor lines for one feature. Never raises and never prints the key."""
    key_state = "set" if ep.key else ("NOT set" if not ep.base_url else "not set (ok: dummy key for a custom base_url)")
    lines = [f"{label}: {ep.shown_url}  model={model}",
             f"  key env var {ep.api_key_env or '(none)'}: {key_state}"]
    try:
        models = list_models(ep, timeout)
    except Exception as e:  # urllib errors, bad JSON, timeouts... doctor must not crash
        lines.append(f"  reachable: NO ({type(e).__name__}: {e})")
        return lines
    lines.append("  reachable: yes")
    present = model in models or f"{model}:latest" in models
    if present:
        lines.append("  model: listed")
    else:
        lines.append(f"  model: NOT listed. For Ollama, run: ollama pull {model}")
    return lines
