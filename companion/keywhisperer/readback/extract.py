"""Ask a vision model for the latest AI reply visible in a screenshot."""

from __future__ import annotations

import base64

PROMPT = (
    "This is a screenshot of a desktop. Find the AI chat conversation in the foreground "
    "window and return ONLY the text of the most recent assistant/AI reply, as plain text "
    "suitable for reading aloud. Skip code blocks (say 'code block omitted'), skip UI chrome "
    "and buttons. If there is no chat reply visible, return exactly: NO_REPLY_FOUND."
)
NO_REPLY = "NO_REPLY_FOUND"
NOT_FOUND_MESSAGE = "I couldn't find a reply on screen."


class VisionExtractor:
    def __init__(self, client, model: str, max_chars: int = 4000):
        self.client = client
        self.model = model
        self.max_chars = max_chars

    async def extract(self, png: bytes) -> str:
        """Return the text to speak for this screenshot."""
        data_url = "data:image/png;base64," + base64.b64encode(png).decode()
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]}],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text or NO_REPLY in text:
            return NOT_FOUND_MESSAGE
        return text[: self.max_chars]
