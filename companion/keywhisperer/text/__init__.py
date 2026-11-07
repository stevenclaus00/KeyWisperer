"""Text processing layer: utterance -> actions."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from ..contracts import (
    Action,
    CommandSpec,
    FormatOptions,
    PressKeys,
    SetListening,
    TextProcessor,
    TypeText,
    UndoLast,
)
from .commands import CommandMatcher, default_commands, normalize
from .formatting import format_text, join, remove_fillers
from .processor import DEFAULT_HALLUCINATIONS, DefaultTextProcessor


def parse_action(spec: dict[str, Any]) -> Action:
    """Build an Action from a config dict, e.g. {"type": "keys", "keys": ["ctrl", "a"]}."""
    kind = spec.get("type")
    if kind == "text":
        return TypeText(str(spec["text"]))
    if kind == "keys":
        return PressKeys([str(k).lower() for k in spec["keys"]], int(spec.get("repeat", 1)))
    if kind == "undo":
        return UndoLast()
    if kind == "listening":
        return SetListening(bool(spec["value"]))
    raise ValueError(f"unknown action type: {kind!r} in {spec!r}")


def build_processor(config: dict[str, Any] | None = None) -> TextProcessor:
    """Create the default processor from a config dict.

    config = {"format": {...FormatOptions fields...},
              "commands": [{"phrases": [...], "actions": [{...}]}],
              "hallucinations": [...]}   # optional, replaces the default list
    User commands are added to the defaults and override matching phrases.
    """
    config = config or {}
    fmt = config.get("format") or {}
    valid = {f.name for f in fields(FormatOptions)}
    unknown = set(fmt) - valid
    if unknown:
        raise ValueError(f"unknown format option(s): {sorted(unknown)}")
    options = FormatOptions(**fmt)

    commands = default_commands()
    for entry in config.get("commands") or []:
        commands.append(
            CommandSpec(
                phrases=list(entry["phrases"]),
                actions=[parse_action(a) for a in entry.get("actions", [])],
            )
        )
    halluc = config.get("hallucinations", DEFAULT_HALLUCINATIONS)
    return DefaultTextProcessor(options, commands, halluc)


__all__ = [
    "CommandMatcher",
    "DEFAULT_HALLUCINATIONS",
    "DefaultTextProcessor",
    "build_processor",
    "default_commands",
    "format_text",
    "join",
    "normalize",
    "parse_action",
    "remove_fillers",
]
