"""WebSocket server the phone streams audio to. See README for the protocol."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs, urlparse

import websockets

from .contracts import Action, PressKeys, ReadBack, SetListening, UndoLast
from .segmenter import Segmenter

log = logging.getLogger(__name__)

CLOSE_BAD_TOKEN = 4001

CONTROL_ACTIONS: dict[str, Callable[[], Action]] = {
    "send": lambda: PressKeys(["enter"]),
    "undo": lambda: UndoLast(),
    "pause": lambda: SetListening(False),
    "resume": lambda: SetListening(True),
    "readback": lambda: ReadBack(),
}


class AudioServer:
    """Accepts one phone at a time on /audio?token=...

    on_utterance(pcm): called for each finished utterance.
    on_actions(actions): called for phone control buttons (send/undo/pause/resume).
    get_status(): returns the status event to send on connect.
    """

    def __init__(self, token: str, make_segmenter: Callable[[], Segmenter],
                 on_utterance: Callable[[bytes], Any],
                 on_actions: Callable[[list[Action]], Awaitable[None] | None],
                 get_status: Callable[[], dict] | None = None,
                 host: str = "0.0.0.0", port: int = 8765):
        self.token = token
        self.make_segmenter = make_segmenter
        self.on_utterance = on_utterance
        self.on_actions = on_actions
        self.get_status = get_status or (lambda: {"type": "status", "listening": True, "connected": True})
        self.host, self.port = host, port
        self.device: str | None = None
        self._client = None
        self._server = None

    async def start(self) -> None:
        self._server = await websockets.serve(self._handler, self.host, self.port)
        # Pick up the real port when port=0 was requested.
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def send_event(self, event: dict) -> None:
        """Send a JSON event to the connected phone (no-op if none)."""
        client = self._client
        if client is None:
            return
        try:
            await client.send(json.dumps(event))
        except websockets.ConnectionClosed:
            pass

    def _path_ok(self, path: str) -> bool:
        url = urlparse(path)
        token = parse_qs(url.query).get("token", [""])[0]
        return url.path == "/audio" and token == self.token

    async def _handler(self, ws) -> None:
        path = ws.request.path if hasattr(ws, "request") else ws.path
        if not self._path_ok(path):
            await ws.close(CLOSE_BAD_TOKEN, "bad token")
            return
        old = self._client
        self._client = ws
        if old is not None:
            await old.close(1000, "replaced by new connection")
        segmenter = self.make_segmenter()
        log.info("phone connected")
        await self.send_event(self.get_status())
        try:
            async for msg in ws:
                if isinstance(msg, (bytes, bytearray)):
                    for utt in segmenter.feed(bytes(msg)):
                        self.on_utterance(utt)
                else:
                    await self._on_text(msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            if self._client is ws:
                self._client = None
                for utt in segmenter.flush():
                    self.on_utterance(utt)
            log.info("phone disconnected")

    async def _on_text(self, raw: str) -> None:
        try:
            data = json.loads(raw)
            kind = data.get("type")
        except (ValueError, AttributeError):
            await self.send_event({"type": "error", "message": "invalid JSON message"})
            return
        if kind == "hello":
            self.device = data.get("device")
            log.info("device: %s", self.device)
        elif kind == "control":
            factory = CONTROL_ACTIONS.get(data.get("action"))
            if factory is None:
                await self.send_event({"type": "error", "message": f"unknown control action: {data.get('action')!r}"})
                return
            res = self.on_actions([factory()])
            if asyncio.iscoroutine(res):
                await res
        else:
            await self.send_event({"type": "error", "message": f"unknown message type: {kind!r}"})
