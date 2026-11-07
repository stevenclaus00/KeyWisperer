import io

import pytest

from keywhisperer.output import (
    ClipboardOutput, StdoutOutput, YdotoolOutput, build_output, check_environment,
)
from keywhisperer.output.base import chord_keycode_args, keycode


class FakeRunner:
    def __init__(self, clipboard: bytes | None = None):
        self.calls = []
        self.clipboard = clipboard

    def __call__(self, args, input=None, capture=False):
        self.calls.append((args, input))
        if args[0] == "wl-paste":
            if self.clipboard is None:
                from keywhisperer.output.base import OutputError
                raise OutputError("nothing copied")
            return self.clipboard
        return b""

    @property
    def argv(self):
        return [c[0] for c in self.calls]


def test_keycodes():
    assert keycode("ctrl") == 29 and keycode("Control") == 29
    assert keycode("v") == 47 and keycode("enter") == 28
    assert keycode("f1") == 59 and keycode("f10") == 68 and keycode("f11") == 87
    assert keycode("0") == 11 and keycode("1") == 2 and keycode("a") == 30 and keycode("m") == 50
    with pytest.raises(ValueError):
        keycode("hyper")


def test_chord_args():
    assert chord_keycode_args(["ctrl", "v"]) == ["29:1", "47:1", "47:0", "29:0"]
    assert chord_keycode_args(["enter"], 2) == ["28:1", "28:0", "28:1", "28:0"]


def test_ydotool_type_text():
    r = FakeRunner()
    YdotoolOutput(runner=r).type_text("hello -x")
    assert r.argv == [["ydotool", "type", "--key-delay", "12", "--", "hello -x"]]


def test_ydotool_press_keys_and_backspace():
    r = FakeRunner()
    out = YdotoolOutput(runner=r)
    out.press_keys(["shift", "enter"], repeat=2)
    out.backspace(3)
    assert r.argv[0] == ["ydotool", "key"] + ["42:1", "28:1", "28:0", "42:0"] * 2
    assert r.argv[1] == ["ydotool", "key"] + ["14:1", "14:0"] * 3


def test_backspace_chunks_and_zero():
    r = FakeRunner()
    out = YdotoolOutput(runner=r)
    out.backspace(0)
    assert r.calls == []
    out.backspace(150)
    assert [len(a) for a in r.argv] == [2 + 200, 2 + 100]


def test_names_syntax():
    r = FakeRunner()
    out = YdotoolOutput(runner=r, ydotool_syntax="names")
    out.press_keys(["ctrl", "shift", "v"])
    out.type_text("hi")
    assert r.argv == [["ydotool", "key", "ctrl+shift+v"], ["ydotool", "type", "--", "hi"]]


def test_bad_syntax():
    with pytest.raises(ValueError):
        YdotoolOutput(ydotool_syntax="x")


def test_key_delay():
    r = FakeRunner()
    YdotoolOutput(runner=r, key_delay_ms=20).press_keys(["tab"])
    assert r.argv == [["ydotool", "key", "--key-delay", "20", "15:1", "15:0"]]


def test_clipboard_basic():
    r, sleeps = FakeRunner(), []
    ClipboardOutput(runner=r, sleep=sleeps.append).type_text("héllo")
    assert r.calls == [
        (["wl-copy"], "héllo".encode()),
        (["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], None),
    ]
    assert sleeps == [0.05]


def test_clipboard_terminal_paste_keys():
    r = FakeRunner()
    ClipboardOutput(runner=r, paste_keys=["ctrl", "shift", "v"], sleep=lambda s: None).type_text("x")
    assert r.argv[1] == ["ydotool", "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]


def test_clipboard_restore():
    r, sleeps = FakeRunner(clipboard=b"old"), []
    ClipboardOutput(runner=r, restore_clipboard=True, sleep=sleeps.append).type_text("new")
    assert [c[0][0] for c in r.calls] == ["wl-paste", "wl-copy", "ydotool", "wl-copy"]
    assert r.calls[1][1] == b"new" and r.calls[3][1] == b"old"
    assert sleeps == [0.05, 0.3]


def test_clipboard_restore_nothing_to_restore():
    r = FakeRunner(clipboard=None)
    ClipboardOutput(runner=r, restore_clipboard=True, sleep=lambda s: None).type_text("new")
    assert [c[0][0] for c in r.calls] == ["wl-paste", "wl-copy", "ydotool"]


def test_clipboard_empty_text_noop():
    r = FakeRunner()
    ClipboardOutput(runner=r).type_text("")
    assert r.calls == []


def test_stdout():
    buf = io.StringIO()
    o = StdoutOutput(buf)
    o.type_text("hi")
    o.press_keys(["ctrl", "a"])
    o.press_keys(["shift", "enter"], 2)
    o.backspace(4)
    assert buf.getvalue().splitlines() == [
        "[type] 'hi'", "[keys] ctrl+a", "[keys] shift+enter x2", "[backspace] x4",
    ]


def test_build_output():
    assert isinstance(build_output("stdout", {}), StdoutOutput)
    assert isinstance(build_output("ydotool", {"ydotool_syntax": "names"}), YdotoolOutput)
    c = build_output("clipboard", {"paste_keys": ["ctrl", "shift", "v"], "restore_clipboard": True})
    assert isinstance(c, ClipboardOutput) and c.paste_keys == ["ctrl", "shift", "v"] and c.restore_clipboard
    with pytest.raises(ValueError):
        build_output("nope", {})


def test_check_environment_all_good():
    rep = check_environment(
        env={"XDG_SESSION_TYPE": "wayland"},
        which=lambda t: "/usr/bin/" + t,
        exists=lambda p: p in ("/run/user/1000/.ydotool_socket", "/dev/uinput"),
        uid=1000,
    )
    assert rep.hints == [] and rep.socket_path == "/run/user/1000/.ydotool_socket"
    assert "wayland" in rep.format()


def test_check_environment_problems():
    rep = check_environment(
        env={"XDG_SESSION_TYPE": "x11", "YDOTOOL_SOCKET": "/tmp/custom"},
        which=lambda t: "/usr/bin/ydotool" if t == "ydotool" else None,
        exists=lambda p: False,
        uid=1000,
    )
    text = " ".join(rep.hints)
    assert "not wayland" in text and "wl-clipboard" in text and "ydotoold" in text
    assert "socket not found" in text and "uinput" in text
    assert rep.tools["ydotool"] and not rep.tools["wl-copy"]
