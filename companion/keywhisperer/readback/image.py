"""Optional screenshot downscaling (local vision models are slow on big images)."""

from __future__ import annotations

import io
import logging

log = logging.getLogger("keywhisperer")
_warned = False


def downscale_png(png: bytes, max_width: int) -> bytes:
    """Shrink a PNG to at most max_width pixels wide. Needs Pillow; otherwise returns it unchanged."""
    global _warned
    if max_width <= 0:
        return png
    try:
        from PIL import Image
    except ImportError:
        if not _warned:
            _warned = True
            log.info("Pillow not installed: not downscaling screenshots (pip install -e '.[images]')")
        return png
    img = Image.open(io.BytesIO(png))
    if img.width <= max_width:
        return png
    height = max(1, round(img.height * max_width / img.width))
    out = io.BytesIO()
    img.resize((max_width, height), Image.LANCZOS).save(out, format="PNG")
    return out.getvalue()
