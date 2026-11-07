"""DefaultTextProcessor: utterance -> list of Actions."""

from __future__ import annotations

from ..contracts import Action, CommandSpec, FormatOptions, TypeText
from .commands import CommandMatcher, default_commands, normalize
from .formatting import format_text, join, remove_fillers

# HEURISTIC: Whisper tends to hallucinate these phrases on near-silent audio.
# Dropped only when they are the ENTIRE utterance (compared normalized).
# Costs: a real, standalone "thank you" is dropped too. Configurable via the
# "hallucinations" key of the text config; set it to [] to disable.
DEFAULT_HALLUCINATIONS = (
    "thank you",
    "thanks for watching",
    "thank you for watching",
    "thanks",
    "you",
    "bye",
    "bye bye",
)


class DefaultTextProcessor:
    """Implements the TextProcessor protocol."""

    def __init__(
        self,
        options: FormatOptions | None = None,
        commands: list[CommandSpec] | None = None,
        hallucinations: tuple[str, ...] | list[str] = DEFAULT_HALLUCINATIONS,
    ) -> None:
        self.options = options or FormatOptions()
        self.matcher = CommandMatcher(commands if commands is not None else default_commands())
        self.hallucinations = {normalize(h) for h in hallucinations}

    def _format(self, text: str) -> str:
        o = self.options
        return format_text(
            text,
            auto_capitalize=o.auto_capitalize,
            number_formatting=o.number_formatting,
            smart_quotes=o.smart_quotes,
            remove_fillers_=o.remove_fillers,
        )

    def process(self, utterance: str, previous_text: str) -> list[Action]:
        text = utterance.strip()
        if self.options.remove_fillers:
            text = remove_fillers(text)
        key = normalize(text)
        if not key or key in self.hallucinations:
            return []

        whole = self.matcher.match_whole(text)
        if whole is not None:
            return whole

        trailing = self.matcher.match_trailing(text)
        if trailing is not None:
            body = join(previous_text, self._format(trailing.body), self.options.auto_capitalize)
            return ([TypeText(body)] if body.strip() else []) + trailing.actions

        typed = join(previous_text, self._format(text), self.options.auto_capitalize)
        return [TypeText(typed)] if typed.strip() else []
