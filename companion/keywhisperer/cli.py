"""Command line entry point: keywhisperer run | pair | test-wav."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import wave

from .config import Config, load_config
from .pairing import print_pairing
from .pipeline import Pipeline
from .segmenter import SAMPLE_RATE, Segmenter
from .server import AudioServer
from .transcribe import build_transcriber


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="keywhisperer", description="Phone-as-mic dictation companion")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="start the server and type what you say")
    run.add_argument("--config", help="path to config.toml")
    run.add_argument("--output", choices=["clipboard", "ydotool", "stdout"],
                     help="output backend (overrides config)")
    pair = sub.add_parser("pair", help="print the pairing URI and QR code")
    pair.add_argument("--config")
    tw = sub.add_parser("test-wav", help="transcribe a 16 kHz mono WAV and print actions (no typing)")
    tw.add_argument("file")
    tw.add_argument("--config")
    return p


async def run_server(cfg: Config, backend: str) -> None:
    from .output import build_output
    from .pairing import load_or_create_token
    from .text import build_processor

    server_box: list[AudioServer] = []

    async def on_event(event: dict) -> None:
        if event["type"] in ("utterance", "typed", "error"):
            logging.getLogger("keywhisperer").info("%s: %s", event["type"], event.get("text") or event.get("message"))
        await server_box[0].send_event(event)

    pipeline = Pipeline(build_transcriber(cfg.transcription), build_processor(cfg.processor_config()),
                        build_output(backend, {}), on_event)
    server = AudioServer(
        load_or_create_token(),
        make_segmenter=lambda: Segmenter(cfg.segmenter),
        on_utterance=pipeline.submit,
        on_actions=pipeline.apply_actions,
        get_status=pipeline.status_event,
        host=cfg.server.host, port=cfg.server.port,
    )
    server_box.append(server)
    pipeline.start()
    await server.start()
    print_pairing(server.port)
    print(f"\nListening on {cfg.server.host}:{server.port} (output: {backend}). Ctrl+C to stop.")
    try:
        await asyncio.Future()
    finally:
        await server.stop()
        await pipeline.stop()


async def test_wav(cfg: Config, path: str) -> None:
    from .text import build_processor

    with wave.open(path, "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            sys.exit("WAV must be 16 kHz, mono, 16-bit")
        pcm = w.readframes(w.getnframes())
    seg = Segmenter(cfg.segmenter)
    utterances = seg.feed(pcm + b"\x00" * (SAMPLE_RATE * 2)) + seg.flush()  # pad 1 s silence
    transcriber = build_transcriber(cfg.transcription)
    processor = build_processor(cfg.processor_config())
    previous = ""
    print(f"{len(utterances)} utterance(s) found")
    for i, utt in enumerate(utterances, 1):
        text = await transcriber.transcribe(utt, SAMPLE_RATE, previous[-200:] or None)
        print(f"[{i}] transcript: {text!r}")
        for action in processor.process(text, previous):
            print(f"    {action}")
            if type(action).__name__ == "TypeText":
                previous += action.text


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(args.config)
    try:
        if args.cmd == "pair":
            print_pairing(cfg.server.port)
        elif args.cmd == "run":
            asyncio.run(run_server(cfg, args.output or cfg.output.backend))
        elif args.cmd == "test-wav":
            asyncio.run(test_wav(cfg, args.file))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
