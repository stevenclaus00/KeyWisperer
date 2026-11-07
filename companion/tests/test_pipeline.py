import asyncio

from keywhisperer.contracts import PressKeys, SetListening, TypeText, UndoLast
from keywhisperer.pipeline import Pipeline


class FakeTranscriber:
    def __init__(self, delays=None):
        self.prompts = []
        self.delays = delays or {}

    async def transcribe(self, pcm, sample_rate, prompt=None):
        self.prompts.append(prompt)
        await asyncio.sleep(self.delays.get(pcm, 0))
        if pcm == b"boom":
            raise RuntimeError("api down")
        return pcm.decode()


class FakeProcessor:
    """Types the text; special phrases map to other actions."""

    def __init__(self):
        self.previous = []

    def process(self, utterance, previous_text):
        self.previous.append(previous_text)
        return {
            "scratch": [UndoLast()],
            "send": [PressKeys(["enter"])],
            "stop": [SetListening(False)],
            "start": [SetListening(True)],
        }.get(utterance, [TypeText(utterance)])


class FakeOutput:
    def __init__(self):
        self.calls = []

    def type_text(self, text): self.calls.append(("type", text))
    def press_keys(self, keys, repeat=1): self.calls.append(("keys", keys, repeat))
    def backspace(self, count): self.calls.append(("bs", count))


async def make(**kw):
    events, out, proc = [], FakeOutput(), FakeProcessor()
    tr = FakeTranscriber(**kw)
    p = Pipeline(tr, proc, out, events.append)
    p.start()
    return p, out, proc, tr, events


async def run(p, *utts):
    for u in utts:
        p.submit(u)
    await p.join()
    await p.stop()


async def test_order_preserved_despite_delays():
    p, out, *_ = await make(delays={b"a": 0.05, b"b": 0.0})
    await run(p, b"a", b"b")
    assert [c[1] for c in out.calls] == ["a", "b"]


async def test_events_and_previous_text():
    p, out, proc, tr, events = await make()
    await run(p, b"hello", b" world")
    assert [e["type"] for e in events] == ["utterance", "typed", "utterance", "typed"]
    assert proc.previous == ["", "hello"]
    assert tr.prompts == [None, "hello"]


async def test_undo_and_enter_reset():
    p, out, proc, *_ = await make()
    await run(p, b"hello", b"scratch", b"abc", b"send", b"next")
    assert out.calls == [("type", "hello"), ("bs", 5), ("type", "abc"),
                         ("keys", ["enter"], 1), ("type", "next")]
    assert proc.previous[-1] == ""


async def test_undo_with_nothing_is_noop():
    p, out, *_ = await make()
    await run(p, b"scratch")
    assert out.calls == []


async def test_listening_toggle():
    p, out, _, _, events = await make()
    await run(p, b"one", b"stop", b"ignored", b"start", b"two")
    assert [c[1] for c in out.calls] == ["one", "two"]
    statuses = [e["listening"] for e in events if e["type"] == "status"]
    assert statuses == [False, True]


async def test_transcription_error_does_not_crash():
    p, out, _, _, events = await make()
    await run(p, b"boom", b"ok")
    assert any(e["type"] == "error" and "api down" in e["message"] for e in events)
    assert out.calls == [("type", "ok")]


async def test_apply_actions_direct():
    p, out, *_ = await make()
    await p.apply_actions([TypeText("x"), UndoLast()])
    await p.stop()
    assert out.calls == [("type", "x"), ("bs", 1)]
