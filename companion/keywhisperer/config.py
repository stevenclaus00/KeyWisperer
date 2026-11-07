"""Configuration: TOML file with dataclass defaults."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from .contracts import FormatOptions


def config_dir() -> Path:
    """~/.config/keywhisperer (HOME is read at call time)."""
    return Path.home() / ".config" / "keywhisperer"


def default_config_path() -> Path:
    return config_dir() / "config.toml"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8765


@dataclass
class TranscriptionConfig:
    provider: str = "openai"
    model: str = "whisper-1"
    language: str = "en"
    vocabulary: list[str] = field(default_factory=list)


@dataclass
class SegmenterConfig:
    silence_ms: int = 700
    max_utterance_s: int = 25
    min_speech_ms: int = 300
    preroll_ms: int = 300
    vad_aggressiveness: int = 2


@dataclass
class OutputConfig:
    backend: str = "clipboard"


@dataclass
class AiConfig:
    """Shared OpenAI-compatible endpoint used by every AI call."""

    base_url: str = ""  # "" = official OpenAI API; e.g. "http://localhost:4000" for LiteLLM
    api_key_env: str = "OPENAI_API_KEY"  # NAME of the env var holding the key


@dataclass
class ReadBackConfig:
    enabled: bool = True
    model: str = "gpt-4o-mini"  # any cheap vision model works
    max_chars: int = 4000
    screenshot_command: str = ""  # "" = xdg-desktop-portal; else a command writing PNG to stdout


@dataclass
class Config:
    ai: AiConfig = field(default_factory=AiConfig)
    readback: ReadBackConfig = field(default_factory=ReadBackConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    segmenter: SegmenterConfig = field(default_factory=SegmenterConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    format: FormatOptions = field(default_factory=FormatOptions)
    commands: list[dict[str, Any]] = field(default_factory=list)

    def processor_config(self) -> dict[str, Any]:
        """Dict handed to keywhisperer.text.build_processor."""
        return {"format": dataclasses.asdict(self.format), "commands": self.commands}


def _fill(obj: Any, values: dict[str, Any], section: str) -> None:
    """Copy known keys from values onto the dataclass; reject unknown ones."""
    known = {f.name for f in dataclasses.fields(obj)}
    for key, value in values.items():
        if key not in known:
            raise ValueError(f"Unknown config key [{section}] {key}")
        setattr(obj, key, value)


def load_config(path: str | Path | None = None) -> Config:
    """Load config from path (or the default location). Missing file -> defaults."""
    cfg = Config()
    p = Path(path) if path else default_config_path()
    if not p.exists():
        if path:
            raise FileNotFoundError(f"Config file not found: {p}")
        return cfg
    with open(p, "rb") as f:
        data = tomllib.load(f)
    for section in ("ai", "readback", "server", "transcription", "segmenter", "output", "format"):
        if section in data:
            _fill(getattr(cfg, section), data[section], section)
    cfg.commands = list(data.get("commands", []))
    return cfg
