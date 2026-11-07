"""Ask a vision model for the latest AI reply visible in a screenshot."""

from __future__ import annotations

import base64
import re

from .image import downscale_png

PROMPT = (
    "This is a screenshot of a desktop. Find the AI chat conversation in the foreground "
    "window and return ONLY the text of the most recent assistant/AI reply, as plain text "
    "suitable for reading aloud. Skip code blocks (say 'code block omitted'), skip UI chrome "
    "and buttons. If there is no chat reply visible, return exactly: NO_REPLY_FOUND."
)
NO_REPLY = "NO_REPLY_FOUND"
NOT_FOUND_MESSAGE = "I couldn't find a reply on screen."

_PREAMBLE = re.compile(
    r"^\s*(?:sure[,!.]?\s*|okay[,!.]?\s*)?"
    r"(?:here(?:'s| is)|the (?:most recent|latest|last)[\w\s/]*?(?:reply|response|message)(?: is| says)?)"
    r"[^:\n]*:\s*",
    re.IGNORECASE,
)
_QUOTES = "\"'\u201c\u201d\u2018\u2019`"


def clean_reply(text: str) -> str:
    """Strip preambles ("The most recent reply is:"), markdown fences and wrapping quotes."""
    text = text.strip()
    fence = re.match(r"^```[\w-]*\n(.*?)\n?```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    text = _PREAMBLE.sub("", text, count=1).strip()
    if len(text) >= 2 and text[0] in _QUOTES and text[-1] in _QUOTES:
        text = text[1:-1].strip()
    return text


class VisionExtractor:
    def __init__(self, client, model: str, max_chars: int = 4000, max_image_width: int = 0):
        self.client = client
        self.model = model
        self.max_chars = max_chars
        self.max_image_width = max_image_width

    async def extract(self, png: bytes) -> str:
        """Return the text to speak for this screenshot."""
        png = downscale_png(png, self.max_image_width)
        data_url = "data:image/png;base64," + base64.b64encode(png).decode()
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]}],
        )
        raw = (resp.choices[0].message.content or "").strip()
        if not raw or NO_REPLY in raw:
            return NOT_FOUND_MESSAGE
        text = clean_reply(raw)
        return text[: self.max_chars] if text else NOT_FOUND_MESSAGE
