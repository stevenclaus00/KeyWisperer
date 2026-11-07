"""Output layer: types text / presses keys into the focused window."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Callable

from ..contracts import Output
from .base import OutputError, Runner, chord_keycode_args, keycode
from .clipboard import ClipboardOutput
from .stdout import StdoutOutput
from .ydotool import YdotoolOutput


def build_output(name: str, config: dict[str, Any] | None = None, runner: Runner | None = None) -> Output:
    """Create an output backend: "clipboard" (default), "ydotool" or "stdout"."""
    config = config or {}
    if name == "clipboard":
        return ClipboardOutput.from_config(config, runner=runner)
    if name == "ydotool":
        return YdotoolOutput.from_config(config, runner=runner)
    if name == "stdout":
        return StdoutOutput()
    raise ValueError(f"unknown output {name!r}; choose clipboard, ydotool or stdout")


@dataclass
class EnvironmentReport:
    session_type: str | None
    tools: dict[str, bool]
    socket_path: str | None  # first candidate that exists, if any
    hints: list[str] = field(default_factory=list)

    def format(self) -> str:
        lines = [f"XDG_SESSION_TYPE: {self.session_type or '(unset)'}"]
        lines += [f"{t}: {'found' if ok else 'MISSING'}" for t, ok in self.tools.items()]
        lines.append(f"ydotoold socket: {self.socket_path or 'not found'}")
        lines += [f"hint: {h}" for h in self.hints]
        return "\n".join(lines)


def check_environment(
    env: dict[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    exists: Callable[[str], bool] = os.path.exists,
    uid: int | None = None,
) -> EnvironmentReport:
    """Inspect the desktop setup and return hints for anything missing."""
    env = os.environ if env is None else env
    uid = os.getuid() if uid is None else uid
    session = env.get("XDG_SESSION_TYPE")
    tools = {t: which(t) is not None for t in ("ydotool", "ydotoold", "wl-copy", "wl-paste")}

    candidates = [env["YDOTOOL_SOCKET"]] if env.get("YDOTOOL_SOCKET") else []
    candidates += [f"/run/user/{uid}/.ydotool_socket", "/tmp/.ydotool_socket"]
    socket = next((c for c in candidates if exists(c)), None)

    hints: list[str] = []
    if session != "wayland":
        hints.append(
            f"session is {session or 'unknown'}, not wayland; these backends target "
            "GNOME Wayland (on X11, xdotool would also work)."
        )
    if not tools["ydotool"]:
        hints.append("install ydotool (sudo apt install ydotool) - see output/README.md.")
    if not tools["wl-copy"]:
        hints.append("install wl-clipboard (sudo apt install wl-clipboard) for the clipboard backend.")
    if tools["ydotool"] and not tools["ydotoold"]:
        hints.append("ydotoold daemon binary not on PATH; it must be running for ydotool to work.")
    if tools["ydotool"] and socket is None:
        hints.append(
            "ydotoold socket not found: start the daemon (systemctl --user start ydotoold) "
            "or set YDOTOOL_SOCKET to its socket path."
        )
    if not exists("/dev/uinput"):
        hints.append("/dev/uinput missing; try: sudo modprobe uinput")
    return EnvironmentReport(session, tools, socket, hints)


__all__ = [
    "ClipboardOutput",
    "EnvironmentReport",
    "OutputError",
    "StdoutOutput",
    "YdotoolOutput",
    "build_output",
    "check_environment",
    "chord_keycode_args",
    "keycode",
]
