"""Utterance -> transcript -> actions -> output, strictly in spoken order."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable

from .contracts import (
    Action, Output, PressKeys, ReadBack, SetListening, TextProcessor, Transcriber, TypeText, UndoLast,
)

log = logging.getLogger(__name__)
SAMPLE_RATE = 16000
PROMPT_CONTEXT_CHARS = 200

Event = dict[str, Any]


class Pipeline:
    """Queue of utterances processed one at a time by a single worker."""

    def __init__(self, transcriber: Transcriber, processor: TextProcessor, output: Output,
                 on_event: Callable[[Event], Any] | None = None,
                 reader: Callable[[], Awaitable[str]] | None = None):
        self.transcriber = transcriber
        self.processor = processor
        self.output = output
        self.on_event = on_event
        self.reader = reader  # async () -> text to speak; None = read-back unavailable
        self._readbacks: set[asyncio.Task] = set()
        self.listening = True
        self.chunks: list[str] = []  # typed since the last "enter"
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._worker: asyncio.Task | None = None

    @property
    def previous_text(self) -> str:
        return "".join(self.chunks)

    # lifecycle
    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Finish queued utterances, then stop the worker."""
        if self._worker:
            await self._queue.put(None)
            await self._worker
            self._worker = None
        if self._readbacks:
            await asyncio.gather(*self._readbacks, return_exceptions=True)

    def submit(self, pcm: bytes) -> None:
        """Queue one utterance for transcription."""
        self._queue.put_nowait(pcm)

    async def join(self) -> None:
        """Wait until everything queued so far has been handled."""
        await self._queue.join()

    # internals
    async def _emit(self, event: Event) -> None:
        if self.on_event is None:
            return
        try:
            res = self.on_event(event)
            if inspect.isawaitable(res):
                await res
        except Exception:
            log.exception("on_event handler failed")

    async def _run(self) -> None:
        while True:
            pcm = await self._queue.get()
            try:
                if pcm is None:
                    return
                await self._handle(pcm)
            except Exception as e:  # never kill the worker
                log.exception("utterance failed")
                await self._emit({"type": "error", "message": str(e) or type(e).__name__})
            finally:
                self._queue.task_done()

    async def _handle(self, pcm: bytes) -> None:
        prompt = self.previous_text[-PROMPT_CONTEXT_CHARS:] or None
        text = (await self.transcriber.transcribe(pcm, SAMPLE_RATE, prompt)).strip()
        if not text:
            return
        await self._emit({"type": "utterance", "text": text})
        actions = self.processor.process(text, self.previous_text)
        if not self.listening:
            actions = [a for a in actions if isinstance(a, SetListening) and a.listening]
        await self.apply_actions(actions)

    async def apply_actions(self, actions: list[Action]) -> None:
        """Execute actions on the output (also used for phone control buttons)."""
        for a in actions:
            if isinstance(a, TypeText):
                self.output.type_text(a.text)
                self.chunks.append(a.text)
                await self._emit({"type": "typed", "text": a.text})
            elif isinstance(a, PressKeys):
                self.output.press_keys(a.keys, a.repeat)
                if a.keys == ["enter"]:
                    self.chunks.clear()  # sent message: start fresh
            elif isinstance(a, UndoLast):
                if self.chunks:
                    self.output.backspace(len(self.chunks.pop()))
            elif isinstance(a, SetListening):
                if a.listening != self.listening:
                    self.listening = a.listening
                    await self._emit(self.status_event())
            elif isinstance(a, ReadBack):
                # Separate task so slow screenshot/vision calls never block dictation.
                task = asyncio.create_task(self._read_back())
                self._readbacks.add(task)
                task.add_done_callback(self._readbacks.discard)

    async def _read_back(self) -> None:
        if self.reader is None:
            await self._emit({"type": "error", "message": "read-back is not configured"})
            return
        await self._emit({"type": "status_message", "text": "Reading back…"})
        try:
            text = await self.reader()
        except Exception as e:
            log.exception("read-back failed")
            await self._emit({"type": "error", "message": f"read-back failed: {str(e) or type(e).__name__}"})
            return
        await self._emit({"type": "speak", "text": text})

    def status_event(self) -> Event:
        return {"type": "status", "listening": self.listening, "connected": True}
