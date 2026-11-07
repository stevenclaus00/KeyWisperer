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

        rb = cfg.readback
        client = make_client(cfg.ai, rb.base_url, rb.api_key_env, timeout=rb.timeout_s)
        extractor = VisionExtractor(client, rb.model, rb.max_chars, rb.max_image_width)
    shot = screenshotter or build_screenshotter(cfg.readback)

    async def reader() -> str:
        return await extractor.extract(await shot())

    return reader


__all__ = ["build_reader", "VisionExtractor", "build_screenshotter"]
