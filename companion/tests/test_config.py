import pytest

from keywhisperer.config import load_config


def test_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config()
    assert cfg.server.port == 8765 and cfg.segmenter.silence_ms == 700
    assert cfg.output.backend == "clipboard" and cfg.format.auto_capitalize


def test_override_and_commands(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('[server]\nport = 9000\n[transcription]\nvocabulary = ["Foo"]\n'
                 '[format]\nsmart_quotes = true\n[[commands]]\nphrases = ["x"]\n')
    cfg = load_config(p)
    assert cfg.server.port == 9000 and cfg.server.host == "0.0.0.0"
    assert cfg.transcription.vocabulary == ["Foo"]
    assert cfg.format.smart_quotes is True
    assert cfg.commands == [{"phrases": ["x"]}]
    assert cfg.processor_config()["format"]["smart_quotes"] is True


def test_unknown_key_rejected(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("[server]\nbogus = 1\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_example_config_loads():
    from pathlib import Path
    load_config(Path(__file__).parent.parent / "config.example.toml")
