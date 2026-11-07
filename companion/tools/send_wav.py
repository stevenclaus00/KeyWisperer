#!/usr/bin/env python3
"""Dev client: stream a 16 kHz mono WAV to the companion in real time.

Usage: python tools/send_wav.py FILE.wav [--host 127.0.0.1] [--port 8765] [--token T]
The token defaults to the one in ~/.config/keywhisperer/token.
"""

import argparse
import asyncio
import json
import wave
from pathlib import Path

import websockets

FRAME_MS = 20


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token")
    ap.add_argument("--tail", type=float, default=1.5, help="seconds of trailing silence to send")
    args = ap.parse_args()

    token = args.token or (Path.home() / ".config/keywhisperer/token").read_text().strip()
    with wave.open(args.file, "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2), \
            "WAV must be 16 kHz mono 16-bit"
        pcm = w.readframes(w.getnframes())
    pcm += b"\x00" * int(16000 * 2 * args.tail)

    step = 16000 * FRAME_MS // 1000 * 2
    async with websockets.connect(f"ws://{args.host}:{args.port}/audio?token={token}") as ws:
        await ws.send(json.dumps({"type": "hello", "device": "send_wav"}))

        async def printer() -> None:
            async for msg in ws:
                print("<-", msg)

        task = asyncio.create_task(printer())
        for i in range(0, len(pcm), step):
            await ws.send(pcm[i:i + step])
            await asyncio.sleep(FRAME_MS / 1000)
        await asyncio.sleep(5)  # wait for transcription results
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
