"""Shared contract between the pipeline, text processing, and output layers.

Owned by the lead. Do not change signatures without coordinating; add new
Action types only by appending.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Union


# ── Actions: what one transcribed utterance turns into ──────────────────────


@dataclass(frozen=True)
class TypeText:
    """Type this text into the focused window (already formatted, including
    any leading space needed to join it to previously typed text)."""

    text: str


@dataclass(frozen=True)
class PressKeys:
    """Press a key chord, e.g. ["enter"], ["shift", "enter"], ["ctrl", "a"].

    Key names are lowercase: ctrl, shift, alt, super, enter, tab, backspace,
    delete, escape, space, up, down, left, right, home, end, pageup, pagedown,
    f1..f12, and single characters a-z, 0-9.
    """

    keys: list[str]
    repeat: int = 1


@dataclass(frozen=True)
class UndoLast:
    """Remove the most recently typed TypeText chunk ("scratch that")."""


@dataclass(frozen=True)
class SetListening:
    """Pause or resume acting on speech ("stop listening" / "start listening")."""

    listening: bool


Action = Union[TypeText, PressKeys, UndoLast, SetListening]


# ── Options ─────────────────────────────────────────────────────────────────


@dataclass
class FormatOptions:
    auto_capitalize: bool = True
    number_formatting: bool = True
    smart_quotes: bool = False
    # Remove filler words like "um", "uh" (simple rule-based pass; an AI
    # cleanup pass will be a separate, later stage).
    remove_fillers: bool = True


@dataclass
class CommandSpec:
    """A user-defined voice command.

    phrases: spoken triggers, matched case-insensitively, ignoring punctuation.
    actions: what to do when matched.
    """

    phrases: list[str]
    actions: list[Action] = field(default_factory=list)


# ── Interfaces ──────────────────────────────────────────────────────────────


class Transcriber(Protocol):
    async def transcribe(
        self, pcm: bytes, sample_rate: int, prompt: str | None = None
    ) -> str:
        """pcm: 16-bit little-endian mono PCM. Returns plain text ('' if none)."""
        ...


class Output(Protocol):
    def type_text(self, text: str) -> None: ...

    def press_keys(self, keys: list[str], repeat: int = 1) -> None: ...

    def backspace(self, count: int) -> None: ...


class TextProcessor(Protocol):
    def process(self, utterance: str, previous_text: str) -> list[Action]:
        """Turn one raw transcribed utterance into actions.

        previous_text: the text typed so far this session (for capitalization
        and joining spaces). Implemented in keywhisperer.text.
        """
        ...
