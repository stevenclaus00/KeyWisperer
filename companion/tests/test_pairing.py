import stat

from keywhisperer import pairing


def test_token_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    t1 = pairing.load_or_create_token()
    t2 = pairing.load_or_create_token()
    assert t1 == t2 and len(t1) >= 16
    mode = stat.S_IMODE((tmp_path / ".config/keywhisperer/token").stat().st_mode)
    assert mode == 0o600


def test_uri_format():
    assert pairing.pairing_uri(8765, "abc", host="192.168.1.5") == "kw://192.168.1.5:8765?token=abc"


def test_lan_ip_returns_string():
    assert pairing.lan_ip().count(".") == 3


def test_print_pairing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    uri = pairing.print_pairing(8765)
    out = capsys.readouterr().out
    assert uri in out and uri.startswith("kw://")
