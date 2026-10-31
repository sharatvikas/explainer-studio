"""Procedurally synthesized sound effects and background music — no licensing needed."""
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
rng = np.random.default_rng(7)


def _t(sec):
    return np.arange(int(SR * sec)) / SR


def _env(n, attack, release):
    a, r = int(SR * attack), int(SR * release)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.exp(-np.linspace(0, 6, r))
    return e


def _lowpass(x, cutoff):
    # one-pole lowpass; cutoff may be an array for sweeps
    if np.isscalar(cutoff):
        from scipy.signal import lfilter

        a = np.exp(-2 * np.pi * cutoff / SR)
        return lfilter([1 - a], [1, -a], x)
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / SR)
    y = np.zeros_like(x)
    prev = 0.0
    for i in range(len(x)):
        prev = (1 - a[i]) * x[i] + a[i] * prev
        y[i] = prev
    return y


def _norm(x, peak=0.8):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def whoosh():
    t = _t(0.55)
    noise = rng.standard_normal(len(t))
    sweep = 300 + 5000 * np.sin(np.pi * t / t[-1]) ** 2
    env = np.sin(np.pi * t / t[-1]) ** 2
    return _norm(_lowpass(noise, sweep) * env, 0.6)


def pop():
    t = _t(0.12)
    f = 900 * np.exp(-t * 25) + 300
    return _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40), 0.7)


def tick():
    t = _t(0.04)
    return _norm(rng.standard_normal(len(t)) * np.exp(-t * 300) + np.sin(2 * np.pi * 2500 * t) * np.exp(-t * 200), 0.5)


def ding():
    t = _t(1.6)
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in [(1318.5, 1, 3), (2637, 0.4, 5), (3955, 0.15, 8), (659.25, 0.3, 2.5)])
    return _norm(x * _env(len(t), 0.002, 1.4), 0.6)


def win():
    out = np.zeros(int(SR * 1.7))
    for k, f in enumerate([783.99, 1046.5, 1318.5]):
        t = _t(1.4 - 0.11 * k)
        n = sum(a * np.sin(2 * np.pi * f * m * t) for m, a in [(1, 1), (2, 0.35), (3, 0.12)]) * np.exp(-t * 3.2)
        out[int(SR * 0.11 * k) : int(SR * 0.11 * k) + len(n)] += n
    return _norm(out, 0.6)


def engine():
    """Soft car hum for the race (2.5 s, loopable-ish)."""
    t = _t(2.5)
    f = 70 + 25 * t / t[-1]
    saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
    x = _lowpass(saw + 0.3 * rng.standard_normal(len(t)), 600)
    return _norm(x * _env(len(t), 0.2, 0.6), 0.35)


def riser():
    t = _t(1.8)
    f = 200 * 2 ** (3 * t / t[-1])
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5 + _lowpass(rng.standard_normal(len(t)), 800 + 6000 * t / t[-1]) * 0.6
    return _norm(x * (t / t[-1]) ** 2 * _env(len(t), 0.01, 0.05), 0.5)


def swell():
    """Low cinematic hit for reveals."""
    t = _t(2.5)
    x = np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 110 * t) + 0.3 * _lowpass(rng.standard_normal(len(t)), 300)
    return _norm(x * np.exp(-t * 1.6) * _env(len(t), 0.01, 1.0), 0.8)


SOUNDS = dict(whoosh=whoosh, pop=pop, tick=tick, ding=ding, win=win, engine=engine, riser=riser, swell=swell)


def sfx_path(name: str) -> str:
    from .paths import data_dir

    out = data_dir() / "cache" / "sfx"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{name}.wav"
    if not p.exists():
        sf.write(p, SOUNDS[name](), SR)
    return str(p)


def music(seconds: float, path: str, bpm: float = 84):
    """Calm, curious ambient bed: Am–F–C–G pads + soft plucked arpeggio + sub."""
    n = int(SR * (seconds + 4))
    out = np.zeros(n)
    beat = 60 / bpm
    bar = 4 * beat
    chords = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]  # midi
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    pad_t = _t(bar * 1.15)
    pad_env = np.minimum(1, pad_t / 1.2) * np.minimum(1, (pad_t[-1] - pad_t) / 1.0 + 0.0)
    pluck_t = _t(beat * 2)
    k = 0
    pos = 0.0
    while pos < seconds + 2:
        ch = chords[k % 4]
        i0 = int(pos * SR)
        pad = sum(np.sin(2 * np.pi * hz(m) * pad_t + 0.3 * np.sin(2 * np.pi * 0.2 * pad_t)) + 0.4 * np.sin(2 * np.pi * hz(m + 12) * 1.003 * pad_t) for m in ch)
        seg = (pad * pad_env * 0.10)[: n - i0]
        out[i0 : i0 + len(seg)] += seg
        bass = np.sin(2 * np.pi * hz(ch[0] - 12) * pad_t) * pad_env * 0.12
        out[i0 : i0 + len(bass[: n - i0])] += bass[: n - i0]
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12]
        if k >= 2:  # let the bed breathe in before the arpeggio starts
            for j, m in enumerate(arp):
                s = int((pos + j * beat / 2) * SR)
                p = np.sin(2 * np.pi * hz(m) * pluck_t) * np.exp(-pluck_t * 5) * 0.05
                p += np.sin(2 * np.pi * hz(m) * 2 * pluck_t) * np.exp(-pluck_t * 9) * 0.015
                out[s : s + len(p[: n - s])] += p[: n - s]
        pos += bar
        k += 1
    # cheap reverb: a few decaying taps
    wet = np.zeros_like(out)
    for d, g in [(0.083, 0.35), (0.131, 0.28), (0.197, 0.22), (0.29, 0.16), (0.41, 0.1)]:
        s = int(d * SR)
        wet[s:] += out[:-s] * g
    out = _lowpass(out + wet, 3500)[: int(SR * seconds)]
    fade = max(1, min(int(SR * 3), len(out) // 3))
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    sf.write(path, np.stack([_norm(out, 0.5)] * 2, axis=1), SR)
