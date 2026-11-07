"""Backend that types with `ydotool type` (US layout, ASCII only)."""

from __future__ import annotations

from typing import Any

from .base import Runner, YdotoolKeys


class YdotoolOutput(YdotoolKeys):
    """Types text directly via ydotool. Mishandles non-ASCII and non-US layouts;
    prefer ClipboardOutput unless you only dictate plain US-English ASCII."""

    def __init__(self, type_delay_ms: int = 12, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.type_delay_ms = type_delay_ms

    @classmethod
    def from_config(cls, config: dict[str, Any], runner: Runner | None = None) -> "YdotoolOutput":
        return cls(
            runner=runner,
            ydotool=config.get("ydotool", "ydotool"),
            ydotool_syntax=config.get("ydotool_syntax", "keycodes"),
            key_delay_ms=config.get("key_delay_ms"),
            type_delay_ms=config.get("type_delay_ms", 12),
        )

    def type_text(self, text: str) -> None:
        if not text:
            return
        cmd = [self.ydotool, "type"]
        if self.syntax == "keycodes":  # --key-delay on `type` is a 1.x option
            cmd += ["--key-delay", str(self.type_delay_ms)]
        self.run(cmd + ["--", text])
