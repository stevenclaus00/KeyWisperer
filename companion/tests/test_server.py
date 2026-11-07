import asyncio
import json

import pytest
import websockets

from keywhisperer.config import SegmenterConfig
from keywhisperer.contracts import PressKeys, SetListening, UndoLast
from keywhisperer.segmenter import Segmenter, energy_vad
from keywhisperer.server import AudioServer

import numpy as np

SR = 16000


def noise(ms):
    return np.random.default_rng(0).integers(-8000, 8000, SR * ms // 1000, dtype=np.int16).tobytes()


@pytest.fixture
async def srv():
    utts, actions = [], []
    server = AudioServer(
        "tok",
        make_segmenter=lambda: Segmenter(SegmenterConfig(), vad=energy_vad()),
        on_utterance=utts.append,
        on_actions=actions.extend,
        host="127.0.0.1", port=0,
    )
    await server.start()
    server.utts, server.actions = utts, actions
    yield server
    await server.stop()


def url(s, token="tok", path="/audio"):
    return f"ws://127.0.0.1:{s.port}{path}?token={token}"


async def test_bad_token_rejected(srv):
    async with websockets.connect(url(srv, "wrong")) as ws:
        with pytest.raises(websockets.ConnectionClosed) as e:
            await ws.recv()
        assert e.value.rcvd.code == 4001


async def test_bad_path_rejected(srv):
    async with websockets.connect(url(srv, path="/other")) as ws:
        with pytest.raises(websockets.ConnectionClosed) as e:
            await ws.recv()
        assert e.value.rcvd.code == 4001


async def test_status_on_connect_and_hello(srv):
    async with websockets.connect(url(srv)) as ws:
        assert json.loads(await ws.recv()) == {"type": "status", "listening": True, "connected": True}
        await ws.send(json.dumps({"type": "hello", "device": "Pixel"}))
        await asyncio.sleep(0.1)
        assert srv.device == "Pixel"


async def test_audio_reaches_segmenter(srv):
    audio = b"\x00" * 16000 + noise(1000) + b"\x00" * 32000
    async with websockets.connect(url(srv)) as ws:
        for i in range(0, len(audio), 1000):
            await ws.send(audio[i:i + 1000])
        await asyncio.sleep(0.3)
    assert len(srv.utts) == 1


async def test_controls_map_to_actions(srv):
    async with websockets.connect(url(srv)) as ws:
        for a in ("send", "undo", "pause", "resume"):
            await ws.send(json.dumps({"type": "control", "action": a}))
        await asyncio.sleep(0.2)
    assert srv.actions == [PressKeys(["enter"]), UndoLast(), SetListening(False), SetListening(True)]


async def test_unknown_control_gives_error(srv):
    async with websockets.connect(url(srv)) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "control", "action": "nope"}))
        assert json.loads(await ws.recv())["type"] == "error"


async def test_send_event_and_replacement(srv):
    async with websockets.connect(url(srv)) as first:
        await first.recv()
        async with websockets.connect(url(srv)) as second:
            await second.recv()
            await srv.send_event({"type": "utterance", "text": "hi"})
            assert json.loads(await second.recv())["text"] == "hi"
            with pytest.raises(websockets.ConnectionClosed):
                await asyncio.wait_for(first.recv(), 2)
