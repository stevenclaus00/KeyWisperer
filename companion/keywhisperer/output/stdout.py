"""Backend that only prints what it would do (for testing without typing)."""

from __future__ import annotations

import sys
from typing import TextIO


class StdoutOutput:
    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream

    def _print(self, line: str) -> None:
        print(line, file=self.stream or sys.stdout, flush=True)

    def type_text(self, text: str) -> None:
        self._print(f"[type] {text!r}")

    def press_keys(self, keys: list[str], repeat: int = 1) -> None:
        suffix = f" x{repeat}" if repeat != 1 else ""
        self._print(f"[keys] {'+'.join(keys)}{suffix}")

    def backspace(self, count: int) -> None:
        self._print(f"[backspace] x{count}")
