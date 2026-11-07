"""Voice command matching.

Rule: a command fires only when the WHOLE utterance equals a command phrase
(after normalizing case/punctuation/whitespace). Exception: "trailing"
phrases (the send commands) may also end an utterance.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from ..contracts import Action, CommandSpec, PressKeys, SetListening, UndoLast

ENTER = PressKeys(["enter"])
# Phrases that may also appear at the END of an utterance.
DEFAULT_TRAILING = ("send it", "send message")  # bare "send" only fires as a whole utterance


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace. Apostrophes kept."""
    text = re.sub(r"[^\w\s']", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def default_commands() -> list[CommandSpec]:
    """Built-in voice commands."""

    def keys(*names: str, repeat: int = 1) -> list[Action]:
        return [PressKeys(list(names), repeat)]

    return [
        CommandSpec(["send it", "send", "send message"], keys("enter")),
        CommandSpec(["new line"], keys("shift", "enter")),
        CommandSpec(["new paragraph"], keys("shift", "enter", repeat=2)),
        CommandSpec(["scratch that", "delete that"], [UndoLast()]),
        CommandSpec(["select all"], keys("ctrl", "a")),
        CommandSpec(["copy that"], keys("ctrl", "c")),
        CommandSpec(["paste", "paste that"], keys("ctrl", "v")),
        CommandSpec(["undo"], keys("ctrl", "z")),
        CommandSpec(["press enter"], keys("enter")),
        CommandSpec(["press tab"], keys("tab")),
        CommandSpec(["press escape"], keys("escape")),
        CommandSpec(["backspace"], keys("backspace")),
        CommandSpec(["stop listening"], [SetListening(False)]),
        CommandSpec(["start listening"], [SetListening(True)]),
    ]


@dataclass
class TrailingMatch:
    body: str  # the utterance text before the trailing command
    actions: list[Action]


class CommandMatcher:
    """Looks up commands; later specs override earlier ones per phrase."""

    def __init__(
        self,
        commands: list[CommandSpec],
        trailing: tuple[str, ...] = DEFAULT_TRAILING,
    ) -> None:
        self._by_phrase: dict[str, list[Action]] = {}
        for spec in commands:
            for phrase in spec.phrases:
                key = normalize(phrase)
                if key:
                    self._by_phrase[key] = list(spec.actions)
        trailing_keys = sorted(
            (normalize(p) for p in trailing if normalize(p) in self._by_phrase),
            key=len,
            reverse=True,
        )
        self._trailing = trailing_keys
        if trailing_keys:
            alts = "|".join(r"\s+".join(map(re.escape, p.split())) for p in trailing_keys)
            self._trailing_re: re.Pattern[str] | None = re.compile(
                rf"(?<![\w'])({alts})(?![\w'])[^\w]*$", re.IGNORECASE
            )
        else:
            self._trailing_re = None

    def match_whole(self, utterance: str) -> list[Action] | None:
        """Actions if the entire utterance is a command phrase, else None."""
        actions = self._by_phrase.get(normalize(utterance))
        return copy.deepcopy(actions) if actions is not None else None

    def match_trailing(self, utterance: str) -> TrailingMatch | None:
        """If the utterance ends with a trailing phrase and has other text before it."""
        if self._trailing_re is None:
            return None
        m = self._trailing_re.search(utterance)
        if not m:
            return None
        body = utterance[: m.start()].rstrip().rstrip(",;:-–—").rstrip()
        if not normalize(body):
            return None
        actions = self._by_phrase[normalize(m.group(1))]
        return TrailingMatch(body, copy.deepcopy(actions))
