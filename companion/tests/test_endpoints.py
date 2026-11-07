import io
import json
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from keywhisperer.ai import (Endpoint, api_key_present, check_endpoint, make_client,
                             resolve_endpoint)
from keywhisperer.config import AiConfig, load_config
from keywhisperer.readback import image
from keywhisperer.readback.extract import NOT_FOUND_MESSAGE, VisionExtractor, clean_reply


# ── endpoint resolution ──
def test_default_is_openai():
    ep = resolve_endpoint(AiConfig())
    assert ep == Endpoint("", "OPENAI_API_KEY")
    assert "api.openai.com" in ep.shown_url


def test_falls_back_to_ai_section():
    ai = AiConfig(base_url="http://proxy:4000", api_key_env="PROXY_KEY")
    assert resolve_endpoint(ai) == Endpoint("http://proxy:4000", "PROXY_KEY")


def test_feature_override_wins():
    ai = AiConfig(base_url="http://proxy:4000", api_key_env="PROXY_KEY")
    ep = resolve_endpoint(ai, "http://gpu:8000/v1", "GPU_KEY")
    assert ep == Endpoint("http://gpu:8000/v1", "GPU_KEY")


def test_other_server_does_not_reuse_ai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    ep = resolve_endpoint(AiConfig(), "http://gpu:11435/v1")
    assert ep.api_key_env == "" and ep.key is None
    assert make_client(AiConfig(), "http://gpu:11435/v1").api_key == "not-needed"


def test_same_server_keeps_ai_key(monkeypatch):
    monkeypatch.setenv("K", "abc")
    ai = AiConfig(base_url="http://p/v1", api_key_env="K")
    assert make_client(ai, "http://p/v1").api_key == "abc"


def test_key_env_handling(monkeypatch):
    monkeypatch.delenv("GPU_KEY", raising=False)
    assert not api_key_present(AiConfig(), "http://gpu/v1", "GPU_KEY")
    monkeypatch.setenv("GPU_KEY", "k")
    assert api_key_present(AiConfig(), "http://gpu/v1", "GPU_KEY")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):  # official API needs a key
        make_client(AiConfig())


def test_two_clients_two_servers():
    ai = AiConfig()
    a = make_client(ai, "http://gpu:8000/v1")
    b = make_client(ai, "http://gpu:11435/v1", timeout=90)
    assert ":8000" in str(a.base_url) and ":11435" in str(b.base_url)
    assert b.timeout == 90


def test_config_per_feature_keys(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('[transcription]\nbase_url = "http://g:8000/v1"\napi_key_env = "T"\n'
                 '[readback]\nbase_url = "http://g:11435/v1"\ntimeout_s = 120\nmax_image_width = 800\n')
    cfg = load_config(p)
    assert cfg.transcription.base_url == "http://g:8000/v1" and cfg.transcription.api_key_env == "T"
    assert cfg.readback.base_url == "http://g:11435/v1" and cfg.readback.api_key_env == ""
    assert cfg.readback.timeout_s == 120 and cfg.readback.max_image_width == 800


def test_build_reader_uses_readback_endpoint():
    from keywhisperer.config import Config
    from keywhisperer.readback import build_reader

    cfg = Config()
    cfg.readback.base_url = "http://gpu:11435/v1"
    cfg.readback.timeout_s = 77
    with patch("keywhisperer.ai.make_client") as mc:
        build_reader(cfg, screenshotter=MagicMock())
    mc.assert_called_once_with(cfg.ai, "http://gpu:11435/v1", "", timeout=77)


# ── clean_reply ──
@pytest.mark.parametrize("raw, expected", [
    ("Hello there.", "Hello there."),
    ("The most recent reply is: Hello there.", "Hello there."),
    ("The most recent reply is:\n\nHello there.", "Hello there."),
    ("Here is the text of the latest assistant reply:\nHello there.", "Hello there."),
    ("Sure, here's the reply: Hello.", "Hello."),
    ('"Hello there."', "Hello there."),
    ("“Hello there.”", "Hello there."),
    ("```\nHello there.\n```", "Hello there."),
    ("```text\nHello there.\n```", "Hello there."),
    ("The latest reply: \"Hi\"", "Hi"),
    ("He said \"hi\" and left", "He said \"hi\" and left"),
])
def test_clean_reply(raw, expected):
    assert clean_reply(raw) == expected


class FakeClient:
    def __init__(self, content):
        self.sent = None
        self.chat = MagicMock()

        async def create(**kw):
            self.sent = kw
            return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])

        self.chat.completions.create = create


async def test_extractor_cleans_and_keeps_no_reply():
    ext = VisionExtractor(FakeClient("The most recent reply is: \"Hi!\""), "m")
    assert await ext.extract(b"png") == "Hi!"
    ext = VisionExtractor(FakeClient("The most recent reply is: NO_REPLY_FOUND"), "m")
    assert await ext.extract(b"png") == NOT_FOUND_MESSAGE
    ext = VisionExtractor(FakeClient("The most recent reply is:"), "m")
    assert await ext.extract(b"png") == NOT_FOUND_MESSAGE


# ── downscale ──
def _png(w, h):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_downscale_shrinks_wide_image():
    pytest.importorskip("PIL")
    from PIL import Image
    out = image.downscale_png(_png(3200, 1800), 1600)
    assert Image.open(io.BytesIO(out)).size == (1600, 900)


def test_downscale_leaves_small_or_disabled():
    pytest.importorskip("PIL")
    small = _png(800, 600)
    assert image.downscale_png(small, 1600) == small
    assert image.downscale_png(small, 0) == small


def test_downscale_skips_without_pillow(monkeypatch, caplog):
    monkeypatch.setitem(sys.modules, "PIL", None)  # makes `from PIL import Image` raise ImportError
    monkeypatch.setattr(image, "_warned", False)
    with caplog.at_level(logging.INFO, logger="keywhisperer"):
        assert image.downscale_png(b"not-a-png", 100) == b"not-a-png"
        assert image.downscale_png(b"not-a-png", 100) == b"not-a-png"
    assert sum("Pillow" in r.message for r in caplog.records) == 1  # logged once


async def test_extractor_downscales_before_sending():
    pytest.importorskip("PIL")
    client = FakeClient("hi")
    await VisionExtractor(client, "m", max_image_width=100).extract(_png(400, 200))
    url = client.sent["messages"][0]["content"][1]["image_url"]["url"]
    import base64
    from PIL import Image
    sent = base64.b64decode(url.split(",", 1)[1])
    assert Image.open(io.BytesIO(sent)).width == 100


# ── doctor reachability ──
def _urlopen_returning(payload):
    resp = MagicMock()
    resp.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
    return MagicMock(return_value=resp)


EP = Endpoint("http://gpu:11435/v1", "GPU_KEY")


def test_check_reachable_model_present(monkeypatch):
    monkeypatch.setenv("GPU_KEY", "sk-supersecret")
    opener = _urlopen_returning({"data": [{"id": "qwen2.5vl:7b"}]})
    with patch("urllib.request.urlopen", opener):
        out = "\n".join(check_endpoint("Read-back", EP, "qwen2.5vl:7b"))
    assert "reachable: yes" in out and "model: listed" in out and "key env var GPU_KEY: set" in out
    assert "sk-supersecret" not in out
    req = opener.call_args[0][0]
    assert req.full_url == "http://gpu:11435/v1/models" and opener.call_args[1]["timeout"] == 3


def test_check_reachable_model_missing(monkeypatch):
    monkeypatch.delenv("GPU_KEY", raising=False)
    with patch("urllib.request.urlopen", _urlopen_returning({"data": [{"id": "other"}]})):
        out = "\n".join(check_endpoint("Read-back", EP, "qwen2.5vl:7b"))
    assert "NOT listed" in out and "ollama pull qwen2.5vl:7b" in out
    assert "dummy key" in out


def test_check_unreachable_does_not_crash(monkeypatch):
    monkeypatch.setenv("GPU_KEY", "sk-supersecret")
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        out = "\n".join(check_endpoint("Transcription", EP, "m"))
    assert "reachable: NO" in out and "connection refused" in out
    assert "sk-supersecret" not in out


def test_doctor_prints_both_endpoints(capsys, monkeypatch):
    from keywhisperer import cli
    from keywhisperer.config import Config
    monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecret")
    cfg = Config()
    cfg.transcription.base_url = "http://gpu:8000/v1"
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        cli.doctor(cfg)
    out = capsys.readouterr().out
    assert "Transcription: http://gpu:8000/v1" in out and "Read-back:" in out
    assert "sk-supersecret" not in out
