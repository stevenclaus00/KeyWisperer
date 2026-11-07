"""Read-back: screenshot -> vision model -> text for the phone to speak."""

from __future__ import annotations

from typing import Awaitable, Callable

from ..config import Config
from .extract import VisionExtractor
from .screenshot import Screenshotter, build_screenshotter


def build_reader(cfg: Config, screenshotter: Screenshotter | None = None,
                 extractor: VisionExtractor | None = None) -> Callable[[], Awaitable[str]]:
    """Return an async function that screenshots the desktop and returns the latest reply."""
    if extractor is None:
        from ..ai import make_client

        extractor = VisionExtractor(make_client(cfg.ai), cfg.readback.model, cfg.readback.max_chars)
    shot = screenshotter or build_screenshotter(cfg.readback)

    async def reader() -> str:
        return await extractor.extract(await shot())

    return reader


__all__ = ["build_reader", "VisionExtractor", "build_screenshotter"]
