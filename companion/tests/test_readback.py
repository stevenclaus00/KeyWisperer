import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from dbus_next import Message, MessageType, Variant

from keywhisperer.ai import make_client
from keywhisperer.config import AiConfig, ReadBackConfig, load_config
from keywhisperer.contracts import ReadBack, TypeText
from keywhisperer.pipeline import Pipeline
from keywhisperer.readback import build_reader
from keywhisperer.readback import screenshot as shot
from keywhisperer.readback.extract import NOT_FOUND_MESSAGE, VisionExtractor
from keywhisperer.text import build_processor
from keywhisperer.server import CONTROL_ACTIONS


# ── config / client ──
def test_config_sections(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('[ai]\nbase_url = "http://x:4000"\napi_key_env = "K"\n[readback]\nmax_chars = 10\n')
    cfg = load_config(p)
    assert cfg.ai.base_url == "http://x:4000" and cfg.ai.api_key_env == "K"
    assert cfg.readback.max_chars == 10 and cfg.readback.model == "gpt-4o-mini" and cfg.readback.enabled
    from keywhisperer.config import Config
    d = Config()
    assert d.ai.base_url == "" and d.ai.api_key_env == "OPENAI_API_KEY" and d.readback.screenshot_command == ""


def test_make_client(monkeypatch):
    monkeypatch.setenv("MY_KEY", "sk-abc")
    c = make_client(AiConfig(api_key_env="MY_KEY"))
    assert c.api_key == "sk-abc" and "api.openai.com" in str(c.base_url)
    c = make_client(AiConfig(base_url="http://localhost:4000", api_key_env="MY_KEY"))
    assert str(c.base_url).startswith("http://localhost:4000")
    monkeypatch.delenv("MY_KEY")
    assert make_client(AiConfig(base_url="http://localhost:4000", api_key_env="MY_KEY")).api_key
    with pytest.raises(ValueError):
        make_client(AiConfig(api_key_env="MY_KEY"))


# ── commands / server ──
@pytest.mark.parametrize("phrase", ["read it back", "Read that back.", "read back"])
def test_phrases(phrase):
    assert build_processor({}).process(phrase, "") == [ReadBack()]


def test_not_whole_utterance():
    assert build_processor({}).process("please read it back to me", "") != [ReadBack()]


def test_user_action_dict():
    acts = build_processor({"commands": [{"phrases": ["recap"], "actions": [{"type": "readback"}]}]}).process("recap", "")
    assert acts == [ReadBack()]


def test_server_control_map():
    assert CONTROL_ACTIONS["readback"]() == ReadBack()


# ── pipeline ──
class NullTranscriber:
    async def transcribe(self, *a, **k): return ""


class NullProcessor:
    def process(self, u, p): return []


class Out:
    def __init__(self): self.calls = []
    def type_text(self, t): self.calls.append(t)
    def press_keys(self, *a): pass
    def backspace(self, n): pass


async def test_readback_emits_speak_without_blocking():
    events, gate = [], asyncio.Event()

    async def reader():
        await gate.wait()
        return "hello there"

    out = Out()
    p = Pipeline(NullTranscriber(), NullProcessor(), out, events.append, reader=reader)
    await p.apply_actions([ReadBack(), TypeText("typed meanwhile")])
    assert out.calls == ["typed meanwhile"]  # dictation not blocked
    await asyncio.sleep(0)
    assert {"type": "status_message", "text": "Reading back…"} in events
    assert not any(e["type"] == "speak" for e in events)
    gate.set()
    await p.stop()
    assert {"type": "speak", "text": "hello there"} in events


async def test_readback_error_and_missing_reader():
    events = []

    async def bad():
        raise RuntimeError("no screen")

    p = Pipeline(NullTranscriber(), NullProcessor(), Out(), events.append, reader=bad)
    await p.apply_actions([ReadBack()])
    await p.stop()
    assert any(e["type"] == "error" and "no screen" in e["message"] for e in events)

    events.clear()
    p = Pipeline(NullTranscriber(), NullProcessor(), Out(), events.append)
    await p.apply_actions([ReadBack()])
    await p.stop()
    assert [e["type"] for e in events] == ["error"]


# ── extractor ──
def fake_client(content):
    c = MagicMock()
    c.chat.completions.create = AsyncMock(
        return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))]))
    return c


async def test_extractor_request_and_truncation():
    c = fake_client("  abcdefghij  ")
    text = await VisionExtractor(c, "vis-model", max_chars=5).extract(b"PNGDATA")
    assert text == "abcde"
    kw = c.chat.completions.create.call_args.kwargs
    assert kw["model"] == "vis-model"
    parts = kw["messages"][0]["content"]
    url = next(p["image_url"]["url"] for p in parts if p["type"] == "image_url")
    assert url == "data:image/png;base64," + base64.b64encode(b"PNGDATA").decode()
    assert "NO_REPLY_FOUND" in next(p["text"] for p in parts if p["type"] == "text")


@pytest.mark.parametrize("content", ["NO_REPLY_FOUND", " NO_REPLY_FOUND.\n", "", None])
async def test_extractor_no_reply(content):
    assert await VisionExtractor(fake_client(content), "m").extract(b"x") == NOT_FOUND_MESSAGE


async def test_build_reader():
    from keywhisperer.config import Config

    async def snap(): return b"png"
    ex = MagicMock(); ex.extract = AsyncMock(return_value="reply")
    assert await build_reader(Config(), screenshotter=snap, extractor=ex)() == "reply"
    ex.extract.assert_awaited_once_with(b"png")


# ── screenshot ──
def test_request_path():
    assert shot.request_path(":1.84", "tok") == "/org/freedesktop/portal/desktop/request/1_84/tok"


def test_uri_to_path_and_read(tmp_path):
    f = tmp_path / "a b.png"
    f.write_bytes(b"PNG")
    uri = "file://" + str(f).replace(" ", "%20")
    assert shot.uri_to_path(uri) == str(f)
    assert shot.read_and_delete(uri) == b"PNG" and not f.exists()
    with pytest.raises(shot.ScreenshotError):
        shot.uri_to_path("http://x/y.png")


class FakeBus:
    """Mimics the dbus-next bus: replies to calls and delivers the Response signal."""

    def __init__(self, uri=None, code=0):
        self.unique_name, self.uri, self.code = ":1.7", uri, code
        self.handlers, self.calls, self.disconnected = [], [], False

    def add_message_handler(self, h): self.handlers.append(h)
    def disconnect(self): self.disconnected = True

    async def call(self, msg):
        self.calls.append(msg.member)
        if msg.member == "Screenshot" and self.uri is not None:
            token = msg.body[1]["handle_token"].value
            signal = Message.new_signal(shot.request_path(self.unique_name, token), shot.REQUEST_IFACE,
                                        "Response", "ua{sv}",
                                        [self.code, {"uri": Variant("s", self.uri)}])
            asyncio.get_running_loop().call_soon(lambda: [h(signal) for h in self.handlers])
        return SimpleNamespace(message_type=MessageType.METHOD_RETURN, body=[])


async def test_portal_screenshot(tmp_path):
    f = tmp_path / "s.png"
    f.write_bytes(b"IMG")
    bus = FakeBus("file://" + str(f))
    assert await shot.portal_screenshot(connect=AsyncMock(return_value=bus)) == b"IMG"
    assert bus.calls == ["AddMatch", "Screenshot"] and bus.disconnected and not f.exists()


async def test_portal_denied_and_timeout():
    with pytest.raises(shot.ScreenshotError, match="cancelled"):
        await shot.portal_screenshot(connect=AsyncMock(return_value=FakeBus("file:///x", code=1)))
    with pytest.raises(shot.ScreenshotError, match="timed out"):
        await shot.portal_screenshot(timeout=0.05, connect=AsyncMock(return_value=FakeBus(None)))


async def test_command_screenshot():
    assert await shot.command_screenshot("printf PNG") == b"PNG"
    with pytest.raises(shot.ScreenshotError):
        await shot.command_screenshot("false")
    s = shot.build_screenshotter(ReadBackConfig(screenshot_command="printf X"))
    assert await s() == b"X"
