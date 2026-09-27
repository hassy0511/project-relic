"""小さな自作シンセ。効果音と BGM を数値から作る（後で無料素材に差し替えられるよう、ID で管理する）。"""
from __future__ import annotations

import numpy as np

SR = 44100


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(SR * dur)) / SR


def osc(freq, dur: float, wave: str = 'sine', phase: float = 0.0) -> np.ndarray:
    """周波数は数値か、時間とともに変わる配列"""
    n = int(SR * dur)
    f = np.full(n, float(freq)) if np.isscalar(freq) else np.asarray(freq)[:n]
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if wave == 'sine':
        return np.sin(ph)
    if wave == 'square':
        return np.sign(np.sin(ph)) * 0.6
    if wave == 'saw':
        return 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    if wave == 'tri':
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1.0) - 1) - 1
    raise ValueError(wave)


def noise(dur: float, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-1, 1, int(SR * dur))


def env(dur: float, a: float = 0.005, d: float = 0.1, s: float = 0.0, r: float = 0.05) -> np.ndarray:
    """ADSR。s はサステインの音量（0〜1）"""
    n = int(SR * dur)
    out = np.zeros(n)
    ia, id_ = int(SR * a), int(SR * d)
    ir = int(SR * r)
    i = 0
    seg = min(ia, n)
    out[:seg] = np.linspace(0, 1, seg, endpoint=False)
    i = seg
    seg = min(id_, n - i)
    out[i:i + seg] = np.linspace(1, s, seg, endpoint=False)
    i += seg
    rest = n - i - ir
    if rest > 0:
        out[i:i + rest] = s
        i += rest
    if n - i > 0:
        out[i:] = np.linspace(out[i - 1] if i > 0 else s, 0, n - i)
    return out


def sweep(f0: float, f1: float, dur: float, curve: float = 1.0) -> np.ndarray:
    x = t_axis(dur) / dur
    return f0 + (f1 - f0) * x ** curve


def lowpass(x: np.ndarray, cutoff) -> np.ndarray:
    """1 次のローパス。cutoff は数値か配列"""
    n = len(x)
    c = np.full(n, float(cutoff)) if np.isscalar(cutoff) else np.asarray(cutoff)[:n]
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return x - lowpass(x, cutoff)


def delay(x: np.ndarray, time: float, feedback: float = 0.35, mix: float = 0.3) -> np.ndarray:
    d = int(SR * time)
    y = np.copy(x)
    for k in range(1, 5):
        g = feedback ** k * mix
        if d * k >= len(x) or g < 0.01:
            break
        y[d * k:] += x[:-d * k] * g
    return y


def fm(carrier: float, ratio: float, index, dur: float) -> np.ndarray:
    t = t_axis(dur)
    idx = index if np.isscalar(index) else np.asarray(index)[:len(t)]
    return np.sin(2 * np.pi * carrier * t + idx * np.sin(2 * np.pi * carrier * ratio * t))


def pad_to(x: np.ndarray, dur: float) -> np.ndarray:
    n = int(SR * dur)
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def normalize(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def note_freq(name: str) -> float:
    """'A4' → 440"""
    names = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3, 'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + (o - 4) * 12) / 12)
