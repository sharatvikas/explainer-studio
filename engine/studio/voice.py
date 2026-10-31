"""Voice-driven timing for Manim scenes, using the free local Kokoro TTS.

    class MyScene(VoiceScene):
        def construct(self):
            with self.say("The car is faster on the road.") as t:
                self.play(Create(road), run_time=t.duration)

Every `say` block lasts at least as long as its narration; animations inside
it can use `t.duration` / `t.left()` to fill the sentence. Each line is
recorded in `self.timeline` (written to <media>/timeline/<Scene>.json) so
post-production can make subtitles, chapters and music ducking.

Set STUDIO_FAKE_TTS=1 to get silent placeholder audio (0.35 s per word) with
no model download — used by tests and by `studio check`.
"""
import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf
from manim import MovingCameraScene, config

from .paths import data_dir, models_dir
from .speech import spoken

GAP = 0.25  # breath between sentences
FAKE_SECONDS_PER_WORD = 0.35

_kokoro = None


def _write_atomic(path: Path, samples, sr) -> None:
    tmp = path.with_name(path.stem + ".tmp.wav")
    sf.write(tmp, samples, sr)
    os.replace(tmp, path)  # a killed run never leaves a truncated clip in the cache


def _fake(text: str, path: Path) -> None:
    sr = 24000
    _write_atomic(path, np.zeros(int(sr * FAKE_SECONDS_PER_WORD * max(1, len(text.split())))), sr)


def tts(text: str, voice: str = "am_michael", speed: float = 1.0) -> tuple[Path, float]:
    """Synthesize `text` (cached by content + voice) and return (wav path, seconds)."""
    global _kokoro
    fake = bool(os.environ.get("STUDIO_FAKE_TTS"))
    cache = data_dir() / "cache" / ("tts-fake" if fake else "tts")
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{voice}|{speed}|{text}".encode()).hexdigest()[:16]
    path = cache / f"{key}.wav"
    if not path.exists():
        if fake:
            _fake(text, path)
        else:
            if _kokoro is None:
                from kokoro_onnx import Kokoro

                m = models_dir()
                _kokoro = Kokoro(str(m / "kokoro-v1.0.onnx"), str(m / "voices-v1.0.bin"))
            lang = "en-gb" if voice.startswith("b") else "en-us"
            samples, sr = _kokoro.create(spoken(text), voice=voice, speed=speed, lang=lang)
            # trim TTS leading/trailing silence so sentences chain tightly
            nz = np.where(np.abs(samples) > 0.01)[0]
            if len(nz):
                samples = samples[max(0, nz[0] - int(0.03 * sr)) : nz[-1] + int(0.08 * sr)]
            _write_atomic(path, samples, sr)
    info = sf.info(path)
    return path, info.frames / info.samplerate


class VoiceScene(MovingCameraScene):
    voice_name = "am_michael"
    speech_speed = 1.0

    def setup(self):
        super().setup()
        self.timeline = {"voice": [], "chapters": [], "sfx": []}

    @property
    def now(self) -> float:
        return self.renderer.time

    def chapter(self, title: str):
        self.timeline["chapters"].append({"t": self.now, "title": title})

    @contextmanager
    def say(self, text: str, gap: float = GAP, caption: str | None = None):
        wav, dur = tts(text, self.voice_name, self.speech_speed)
        start = self.now
        self.add_sound(str(wav))
        self.timeline["voice"].append({"t": start, "dur": dur, "text": text, "caption": caption or text, "wav": str(wav)})
        t = SimpleNamespace(duration=dur, start=start, left=lambda: max(0.0, start + dur - self.now))
        yield t
        remaining = start + dur - self.now
        if remaining > 0.02:
            self.wait(remaining)
        if gap:
            self.wait(gap)

    def narrate(self, text: str, *anims, lag: float = 0.0, frac: float = 1.0, **kw):
        """Speak `text` while playing `anims` across `frac` of the sentence."""
        with self.say(text) as t:
            if lag:
                self.wait(lag)
            if anims:
                self.play(*anims, run_time=max(0.3, t.duration * frac - lag), **kw)

    def sfx(self, name: str, gain: float = -8):
        from .sfx import sfx_path

        self.add_sound(sfx_path(name), gain=gain)
        self.timeline["sfx"].append({"t": self.now, "name": name})

    def tear_down(self):
        super().tear_down()
        out = Path(config.media_dir) / "timeline"
        out.mkdir(parents=True, exist_ok=True)
        self.timeline["duration"] = self.now
        (out / f"{type(self).__name__}.json").write_text(json.dumps(self.timeline, indent=1), encoding="utf-8")


def caption_chunks(text: str, max_words: int = 4) -> list[tuple[str, float]]:
    """Split a sentence into short caption chunks with each chunk's share of the duration."""
    words = text.split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.,;:?!—]$", w):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    weights = [len(c) + 3 for c in chunks]
    total = sum(weights)
    return [(c, w / total) for c, w in zip(chunks, weights)]
