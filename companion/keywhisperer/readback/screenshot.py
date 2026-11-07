"""Take a desktop screenshot and return PNG bytes.

Default: the xdg-desktop-portal Screenshot API over D-Bus (works on GNOME
Wayland, where grabbing the screen directly is not allowed). GNOME may show a
one-time permission prompt the first time; approve it and it is remembered.

Alternative: set [readback] screenshot_command to any command that writes a PNG
to stdout (e.g. "grim -" on wlroots compositors).

TODO: the portal code could not be run in the development sandbox (no desktop).
Verify it on a real GNOME session with `keywhisperer readback-test`.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import uuid
from typing import Awaitable, Callable
from urllib.parse import unquote, urlparse

from ..config import ReadBackConfig

Screenshotter = Callable[[], Awaitable[bytes]]

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENSHOT_IFACE = "org.freedesktop.portal.Screenshot"
REQUEST_IFACE = "org.freedesktop.portal.Request"
TIMEOUT_S = 10


class ScreenshotError(RuntimeError):
    pass


def request_path(unique_name: str, token: str) -> str:
    """Object path the portal will use for our Request (per the portal docs).

    ":1.84" + token "abc" -> /org/freedesktop/portal/desktop/request/1_84/abc
    """
    sender = unique_name.lstrip(":").replace(".", "_")
    return f"{PORTAL_PATH}/request/{sender}/{token}"


def uri_to_path(uri: str) -> str:
    """file:///tmp/a%20b.png -> /tmp/a b.png"""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ScreenshotError(f"unexpected screenshot uri: {uri!r}")
    return unquote(parsed.path)


def read_and_delete(uri: str) -> bytes:
    """Read the PNG the portal wrote, then remove the temp file."""
    path = uri_to_path(uri)
    try:
        with open(path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


async def _connect_session_bus():
    from dbus_next.aio import MessageBus

    return await MessageBus().connect()


async def portal_screenshot(timeout: float = TIMEOUT_S, connect=_connect_session_bus) -> bytes:
    """Screenshot via xdg-desktop-portal. `connect` is injectable for tests."""
    from dbus_next import Message, MessageType, Variant

    bus = await connect()
    try:
        token = "kw" + uuid.uuid4().hex
        path = request_path(bus.unique_name, token)
        loop = asyncio.get_running_loop()
        result: asyncio.Future = loop.create_future()

        def on_message(msg):
            # Response signal body: (uint response, dict results)
            if (msg.message_type == MessageType.SIGNAL and msg.path == path
                    and msg.interface == REQUEST_IFACE and msg.member == "Response"
                    and not result.done()):
                result.set_result(msg.body)
            return False

        # Subscribe BEFORE calling the method so we cannot miss the signal.
        bus.add_message_handler(on_message)
        reply = await bus.call(Message(
            destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus", member="AddMatch", signature="s",
            body=[f"type='signal',interface='{REQUEST_IFACE}',member='Response',path='{path}'"],
        ))
        if reply.message_type == MessageType.ERROR:
            raise ScreenshotError(f"AddMatch failed: {reply.body}")

        reply = await bus.call(Message(
            destination=PORTAL_BUS, path=PORTAL_PATH, interface=SCREENSHOT_IFACE,
            member="Screenshot", signature="sa{sv}",
            body=["", {"interactive": Variant("b", False), "handle_token": Variant("s", token)}],
        ))
        if reply.message_type == MessageType.ERROR:
            raise ScreenshotError(f"portal Screenshot failed: {reply.body}")

        try:
            code, results = await asyncio.wait_for(result, timeout)
        except asyncio.TimeoutError:
            raise ScreenshotError(
                f"screenshot timed out after {timeout:g}s (is a permission prompt waiting?)") from None
        if code != 0:
            raise ScreenshotError("screenshot was cancelled or denied")
        uri = results["uri"]
        uri = getattr(uri, "value", uri)  # Variant -> str
        return read_and_delete(uri)
    finally:
        bus.disconnect()


async def command_screenshot(command: str, timeout: float = TIMEOUT_S) -> bytes:
    """Run a command that prints a PNG on stdout (e.g. "grim -")."""
    proc = await asyncio.create_subprocess_exec(
        *shlex.split(command), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise ScreenshotError(f"screenshot command timed out: {command}") from None
    if proc.returncode != 0 or not out:
        raise ScreenshotError(f"screenshot command failed ({proc.returncode}): "
                              f"{err.decode(errors='replace').strip()}")
    return out


def build_screenshotter(cfg: ReadBackConfig) -> Screenshotter:
    if cfg.screenshot_command:
        return lambda: command_screenshot(cfg.screenshot_command)
    return portal_screenshot
