"""Default backend: put text on the Wayland clipboard, then send the paste chord."""

from __future__ import annotations

import time
from typing import Any, Callable

from .base import OutputError, Runner, YdotoolKeys


class ClipboardOutput(YdotoolKeys):
    """wl-copy + ydotool paste chord. Handles any Unicode text and any layout."""

    def __init__(
        self,
        paste_keys: list[str] | None = None,
        copy_delay: float = 0.05,
        restore_clipboard: bool = False,
        restore_delay: float = 0.3,
        sleep: Callable[[float], None] = time.sleep,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.paste_keys = paste_keys or ["ctrl", "v"]
        self.copy_delay = copy_delay
        self.restore_clipboard = restore_clipboard
        self.restore_delay = restore_delay
        self.sleep = sleep

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        runner: Runner | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> "ClipboardOutput":
        return cls(
            paste_keys=config.get("paste_keys"),
            copy_delay=config.get("copy_delay", 0.05),
            restore_clipboard=config.get("restore_clipboard", False),
            restore_delay=config.get("restore_delay", 0.3),
            sleep=sleep,
            runner=runner,
            ydotool=config.get("ydotool", "ydotool"),
            ydotool_syntax=config.get("ydotool_syntax", "keycodes"),
            key_delay_ms=config.get("key_delay_ms"),
        )

    def _read_clipboard(self) -> bytes | None:
        """Current text clipboard, or None if empty / not text."""
        try:
            return self.run(["wl-paste", "--no-newline", "--type", "text"], capture=True)
        except OutputError:
            return None

    def type_text(self, text: str) -> None:
        if not text:
            return
        previous = self._read_clipboard() if self.restore_clipboard else None
        self.run(["wl-copy"], input=text.encode("utf-8"))
        self.sleep(self.copy_delay)
        self.press_keys(self.paste_keys)
        # If the old clipboard was not text (or empty) we leave ours in place
        # rather than clearing something we cannot restore.
        if previous is not None:
            self.sleep(self.restore_delay)
            self.run(["wl-copy"], input=previous)
