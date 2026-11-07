"""Split a continuous 16 kHz PCM stream into utterances at pauses."""

from __future__ import annotations

import collections
from typing import Callable

import numpy as np

from .config import SegmenterConfig

SAMPLE_RATE = 16000
FRAME_MS = 20
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * 2  # 640

VadFn = Callable[[bytes], bool]


def energy_vad(rms_threshold: float = 500.0) -> VadFn:
    """Fallback VAD: a frame is speech if its RMS exceeds the threshold."""

    def is_speech(frame: bytes) -> bool:
        samples = np.frombuffer(frame, dtype="<i2").astype(np.float64)
        return bool(samples.size and np.sqrt(np.mean(samples**2)) > rms_threshold)

    return is_speech


def default_vad(aggressiveness: int = 2) -> VadFn:
    """webrtcvad if importable, otherwise the energy VAD."""
    try:
        import webrtcvad

        vad = webrtcvad.Vad(aggressiveness)
        return lambda frame: vad.is_speech(frame, SAMPLE_RATE)
    except Exception:  # ImportError or a broken binary wheel
        return energy_vad()


class Segmenter:
    """feed(pcm) -> finished utterances (raw PCM bytes). Synchronous and testable."""

    def __init__(self, config: SegmenterConfig | None = None, vad: VadFn | None = None):
        self.cfg = config or SegmenterConfig()
        self.vad = vad or default_vad(self.cfg.vad_aggressiveness)
        self._buf = b""
        self._preroll: collections.deque[bytes] = collections.deque(
            maxlen=max(1, self.cfg.preroll_ms // FRAME_MS)
        )
        self._reset_utterance()

    def _reset_utterance(self) -> None:
        self._frames: list[bytes] = []
        self._active = False
        self._speech_frames = 0
        self._silence_frames = 0

    def feed(self, pcm: bytes) -> list[bytes]:
        """Add audio of any length; return any utterances completed by it."""
        self._buf += pcm
        out: list[bytes] = []
        while len(self._buf) >= FRAME_BYTES:
            frame, self._buf = self._buf[:FRAME_BYTES], self._buf[FRAME_BYTES:]
            utt = self._on_frame(frame)
            if utt:
                out.append(utt)
        return out

    def flush(self) -> list[bytes]:
        """End of stream: emit any utterance in progress."""
        utt = self._finish()
        self._buf = b""
        return [utt] if utt else []

    def _on_frame(self, frame: bytes) -> bytes | None:
        speech = self.vad(frame)
        if not self._active:
            if speech:
                self._active = True
                self._frames = list(self._preroll) + [frame]
                self._preroll.clear()
                self._speech_frames = 1
                self._silence_frames = 0
            else:
                self._preroll.append(frame)
            return None

        self._frames.append(frame)
        if speech:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1

        too_long = len(self._frames) * FRAME_MS >= self.cfg.max_utterance_s * 1000
        if self._silence_frames * FRAME_MS >= self.cfg.silence_ms or too_long:
            return self._finish()
        return None

    def _finish(self) -> bytes | None:
        """Close the current utterance; None if absent or too little speech."""
        if not self._active:
            return None
        enough = self._speech_frames * FRAME_MS >= self.cfg.min_speech_ms
        data = b"".join(self._frames)
        self._reset_utterance()
        return data if enough else None
