"""Shared helpers for output backends: subprocess runner and ydotool keys."""

from __future__ import annotations

import subprocess
import tempfile
from typing import Callable

# A runner executes a command. (args, stdin bytes or None, capture stdout?)
# -> stdout bytes (empty unless capture=True). Tests inject a fake that records
# the args instead of executing anything.
Runner = Callable[..., bytes]


class OutputError(RuntimeError):
    """A helper command (ydotool, wl-copy, ...) failed or is missing."""


def default_runner(args: list[str], input: bytes | None = None, capture: bool = False) -> bytes:
    """Run a command, raising OutputError on failure.

    stderr goes to a temp file and stdout to DEVNULL unless `capture`, because
    wl-copy forks a background process that keeps inherited pipes open, which
    would make subprocess.run hang waiting for EOF.
    """
    with tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.run(
                args,
                input=input,
                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                stderr=err,
                timeout=10,
            )
        except FileNotFoundError as e:
            raise OutputError(f"{args[0]!r} not found on PATH") from e
        except subprocess.TimeoutExpired as e:
            raise OutputError(f"{args[0]!r} timed out") from e
        if proc.returncode != 0:
            err.seek(0)
            msg = err.read().decode(errors="replace").strip()
            raise OutputError(f"{' '.join(args[:2])} failed ({proc.returncode}): {msg}")
        return proc.stdout or b""


# Linux input event codes (linux/input-event-codes.h).
KEYCODES: dict[str, int] = {
    "escape": 1, "backspace": 14, "tab": 15, "enter": 28, "space": 57,
    "ctrl": 29, "shift": 42, "alt": 56, "super": 125,
    "delete": 111, "up": 103, "down": 108, "left": 105, "right": 106,
    "home": 102, "end": 107, "pageup": 104, "pagedown": 109,
    "f11": 87, "f12": 88,
}
KEYCODES.update({f"f{i}": 58 + i for i in range(1, 11)})  # F1=59 .. F10=68
for _i, _ch in enumerate("1234567890"):
    KEYCODES[_ch] = 2 + _i  # 1=2 .. 9=10, 0=11
for _row, _start in (("qwertyuiop", 16), ("asdfghjkl", 30), ("zxcvbnm", 44)):
    for _i, _ch in enumerate(_row):
        KEYCODES[_ch] = _start + _i

ALIASES = {
    "control": "ctrl", "return": "enter", "esc": "escape", "meta": "super",
    "win": "super", "windows": "super", "del": "delete",
    "pgup": "pageup", "pgdn": "pagedown",
}


def keycode(name: str) -> int:
    """Linux keycode for a key name from the contract (e.g. 'ctrl' -> 29)."""
    key = name.lower()
    key = ALIASES.get(key, key)
    try:
        return KEYCODES[key]
    except KeyError:
        raise ValueError(f"unknown key name: {name!r}") from None


def chord_keycode_args(keys: list[str], repeat: int = 1) -> list[str]:
    """['ctrl','v'] -> ['29:1','47:1','47:0','29:0']: press in order, release reversed."""
    codes = [keycode(k) for k in keys]
    one = [f"{c}:1" for c in codes] + [f"{c}:0" for c in reversed(codes)]
    return one * max(1, repeat)


class YdotoolKeys:
    """Sends key chords through ydotool. Base class for the real backends.

    syntax "keycodes" = ydotool 1.x (`ydotool key 29:1 47:1 47:0 29:0`);
    syntax "names"    = old 0.1.x   (`ydotool key ctrl+v`).
    """

    def __init__(
        self,
        runner: Runner | None = None,
        ydotool: str = "ydotool",
        ydotool_syntax: str = "keycodes",
        key_delay_ms: int | None = None,
    ) -> None:
        if ydotool_syntax not in ("keycodes", "names"):
            raise ValueError("ydotool_syntax must be 'keycodes' or 'names'")
        self.run = runner or default_runner
        self.ydotool = ydotool
        self.syntax = ydotool_syntax
        self.key_delay_ms = key_delay_ms

    def _key_cmd(self, tail: list[str]) -> list[str]:
        cmd = [self.ydotool, "key"]
        if self.key_delay_ms is not None and self.syntax == "keycodes":
            cmd += ["--key-delay", str(self.key_delay_ms)]
        return cmd + tail

    def press_keys(self, keys: list[str], repeat: int = 1) -> None:
        if self.syntax == "keycodes":
            self.run(self._key_cmd(chord_keycode_args(keys, repeat)))
        else:
            # TODO: verify 0.1.x accepts several chords in one call; we repeat
            # the chord as separate args, which is what its docs suggest.
            names = [ALIASES.get(k.lower(), k.lower()) for k in keys]
            self.run(self._key_cmd(["+".join(names)] * max(1, repeat)))

    def backspace(self, count: int) -> None:
        # Chunked so we never build an enormous argv.
        while count > 0:
            n = min(count, 100)
            self.press_keys(["backspace"], n)
            count -= n
