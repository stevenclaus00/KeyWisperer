import numpy as np

from keywhisperer.config import SegmenterConfig
from keywhisperer.segmenter import FRAME_BYTES, Segmenter, default_vad, energy_vad

SR = 16000


def silence(ms):
    return b"\x00" * (SR * ms // 1000 * 2)


def noise(ms, amp=8000, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(-amp, amp, SR * ms // 1000, dtype=np.int16).tobytes()


def seg(**kw):
    return Segmenter(SegmenterConfig(**kw), vad=energy_vad())


def test_single_utterance():
    s = seg()
    out = s.feed(silence(500) + noise(1000) + silence(1000))
    assert len(out) == 1
    # preroll (300) + speech (1000) + silence (700) ~ 2.0 s
    assert 1.8 * SR * 2 < len(out[0]) < 2.2 * SR * 2


def test_two_utterances_and_odd_chunk_sizes():
    s = seg()
    audio = silence(300) + noise(800) + silence(1000) + noise(600, seed=1) + silence(1000)
    out = []
    for i in range(0, len(audio), 333):  # not frame aligned
        out += s.feed(audio[i:i + 333])
    assert len(out) == 2


def test_short_blip_dropped():
    s = seg()
    assert s.feed(silence(500) + noise(100) + silence(1000)) == []


def test_force_split_at_max():
    s = seg(max_utterance_s=2)
    out = s.feed(noise(5000))
    assert len(out) == 2 and len(out[0]) == 2 * SR * 2


def test_flush_emits_pending():
    s = seg()
    assert s.feed(noise(1000)) == []
    assert len(s.flush()) == 1
    assert s.flush() == []


def test_preroll_included():
    s = seg(preroll_ms=300)
    out = s.feed(silence(1000) + noise(500) + silence(800))
    assert len(out[0]) >= (300 + 500 + 700) * SR * 2 // 1000 - FRAME_BYTES


def test_energy_vad_threshold():
    vad = energy_vad()
    assert not vad(silence(20)) and vad(noise(20))


def test_default_vad_runs_on_silence():
    assert default_vad()(silence(20)) is False
