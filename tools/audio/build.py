"""効果音と BGM を書き出す（public/assets/audio/*.ogg）。

  npm run audio
ID は content/audio.yaml と、ゲーム内の sfx の ID に対応する。
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
VENV_PY = os.path.join(REPO, '.venv-blender', 'bin', 'python')

try:
    import numpy as np
    import soundfile as sf
except ImportError:
    if os.path.exists(VENV_PY) and sys.executable != VENV_PY:
        os.execv(VENV_PY, [VENV_PY, *sys.argv])
    raise

sys.path.insert(0, HERE)
from synth import (SR, delay, env, fm, highpass, lowpass, noise, normalize, note_freq, osc, pad_to,  # noqa: E402
                   sweep, t_axis)

OUT = os.path.join(REPO, 'public', 'assets', 'audio')


def save(name: str, x: np.ndarray, peak: float = 0.8) -> None:
    os.makedirs(OUT, exist_ok=True)
    x = normalize(x, peak)
    sf.write(os.path.join(OUT, f'{name}.ogg'), x.astype(np.float32), SR, format='OGG', subtype='VORBIS')


# ---------------------------------------------------------------- 効果音

def sfx() -> dict[str, np.ndarray]:
    s: dict[str, np.ndarray] = {}
    d = 0.14
    s['shot'] = (osc(sweep(1400, 380, d, 0.6), d, 'square') * env(d, 0.001, 0.12) * 0.6
                 + highpass(noise(d, 1), 2000) * env(d, 0.001, 0.03) * 0.4)
    d = 0.45
    s['shot_charge'] = (osc(sweep(900, 120, d, 0.5), d, 'saw') * env(d, 0.002, 0.4) * 0.7
                        + lowpass(noise(d, 2), 3000) * env(d, 0.001, 0.2) * 0.5)
    d = 0.2
    s['slash'] = highpass(noise(d, 3), 1500) * env(d, 0.01, 0.17) * np.sin(np.linspace(0, np.pi, int(SR * d)))
    d = 0.4
    s['slash_charge'] = (highpass(noise(d, 4), 800) * env(d, 0.02, 0.35)
                         + osc(sweep(200, 900, d), d, 'saw') * env(d, 0.02, 0.35) * 0.3)
    d = 0.12
    s['hit'] = (lowpass(noise(d, 5), 2500) * env(d, 0.001, 0.1) + osc(180, d, 'square') * env(d, 0.001, 0.05) * 0.5)
    d = 0.22
    s['hit_weak'] = (lowpass(noise(d, 6), 5000) * env(d, 0.001, 0.12)
                     + osc(sweep(1200, 1800, d), d, 'tri') * env(d, 0.001, 0.2) * 0.6)
    d = 0.9
    s['explode'] = (lowpass(noise(d, 7), sweep(4000, 200, d)) * env(d, 0.002, 0.8)
                    + osc(sweep(120, 40, d), d, 'sine') * env(d, 0.002, 0.6) * 0.8)
    d = 0.18
    s['jump'] = osc(sweep(300, 600, d), d, 'tri') * env(d, 0.002, 0.16) * 0.5
    d = 0.12
    s['land'] = lowpass(noise(d, 8), 600) * env(d, 0.001, 0.1)
    d = 0.25
    s['dash'] = highpass(noise(d, 9), 600) * env(d, 0.005, 0.22) + osc(sweep(200, 90, d), d, 'saw') * env(d, 0.005, 0.2) * 0.2
    d = 0.5
    s['drill'] = (osc(90 + 20 * np.sin(2 * np.pi * 35 * t_axis(d)), d, 'saw') * env(d, 0.02, 0.1, 0.8, 0.1)
                  + highpass(noise(d, 10), 3000) * 0.3 * env(d, 0.02, 0.1, 0.8, 0.1))
    d = 0.35
    s['alert'] = (osc(880, d, 'square') * env(d, 0.001, 0.1) * 0.4
                  + pad_to(np.concatenate([np.zeros(int(SR * 0.1)), osc(1320, 0.25, 'square') * env(0.25, 0.001, 0.2) * 0.4]), d))
    d = 0.6
    s['charge'] = osc(sweep(80, 260, d, 2), d, 'saw') * env(d, 0.01, 0.1, 0.9, 0.1) * 0.6
    d = 0.5
    s['crash'] = lowpass(noise(d, 11), 1500) * env(d, 0.001, 0.45) + osc(60, d, 'sine') * env(d, 0.001, 0.4)
    d = 0.8
    arp = np.concatenate([osc(note_freq(n), 0.12, 'tri') * env(0.12, 0.002, 0.11) for n in ['C5', 'E5', 'G5', 'C6']])
    s['chest'] = delay(pad_to(arp, d), 0.09, 0.3, 0.4)
    d = 1.0
    arp = np.concatenate([osc(note_freq(n), 0.1, 'square') * env(0.1, 0.002, 0.09) * 0.5 for n in ['G5', 'C6', 'E6', 'G6']])
    s['item'] = delay(pad_to(arp, d), 0.12, 0.35, 0.4)
    d = 0.1
    s['pickup'] = osc(sweep(1500, 2200, d), d, 'tri') * env(d, 0.001, 0.09) * 0.5
    d = 1.4
    s['save'] = delay(pad_to(sum(osc(note_freq(n), 1.0, 'sine') * env(1.0, 0.05, 0.9) for n in ['C5', 'G5', 'E6']), d), 0.2, 0.4, 0.4)
    d = 0.6
    s['heal'] = osc(sweep(500, 1000, d), d, 'sine') * env(d, 0.01, 0.55) * 0.6
    d = 1.0
    s['wall_break'] = (lowpass(noise(d, 12), sweep(3000, 300, d)) * env(d, 0.001, 0.9)
                       + osc(sweep(90, 35, d), d, 'sine') * env(d, 0.001, 0.8))
    d = 0.08
    s['ui_move'] = osc(1200, d, 'tri') * env(d, 0.001, 0.07) * 0.4
    d = 0.2
    s['ui_ok'] = osc(sweep(900, 1400, d), d, 'tri') * env(d, 0.001, 0.18) * 0.5
    d = 0.05
    s['blip'] = osc(700, d, 'square') * env(d, 0.001, 0.045) * 0.3
    return s


# ---------------------------------------------------------------- BGM

def bgm_trial() -> np.ndarray:
    """試験場の BGM。明るい冒険の予感。112 BPM、8 小節 × 2 のループ"""
    bpm = 112
    beat = 60 / bpm
    bars = 16
    total = bars * 4 * beat
    n = int(SR * total)
    out = np.zeros(n)

    def put(x: np.ndarray, at_beat: float, gain: float = 1.0) -> None:
        i = int(SR * at_beat * beat)
        j = min(n, i + len(x))
        out[i:j] += x[: j - i] * gain

    chords = [['A2', 'C4', 'E4'], ['F2', 'A3', 'C4'], ['C3', 'E4', 'G4'], ['G2', 'B3', 'D4']] * 4
    for bar, ch in enumerate(chords):
        b0 = bar * 4
        root = note_freq(ch[0])
        # ベース（8 分）
        for k in range(8):
            f = root * (2 if k % 4 == 3 else 1)
            put(lowpass(osc(f, beat * 0.45, 'saw'), 900) * env(beat * 0.45, 0.005, 0.2, 0.5, 0.05), b0 + k * 0.5, 0.5)
        # パッド
        pad = sum(osc(note_freq(x) * (1.003 if i else 1), beat * 4, 'saw') for i, x in enumerate(ch[1:]))
        put(lowpass(pad, 1200) * env(beat * 4, 0.2, 0.5, 0.6, 0.4), b0, 0.12)
        # アルペジオ（16 分）
        arp = [ch[1], ch[2], ch[1][:-1] + str(int(ch[1][-1]) + 1), ch[2]]
        for k in range(16):
            f = note_freq(arp[k % 4])
            put(osc(f, beat * 0.22, 'tri') * env(beat * 0.22, 0.002, 0.15), b0 + k * 0.25, 0.12)
        # ドラム
        for k in range(4):
            kick = osc(sweep(140, 45, 0.18), 0.18, 'sine') * env(0.18, 0.001, 0.17)
            put(kick, b0 + k, 0.7 if k % 2 == 0 else 0.35)
            if k % 2 == 1:
                put(highpass(noise(0.16, bar * 4 + k), 1200) * env(0.16, 0.001, 0.14), b0 + k, 0.35)
            put(highpass(noise(0.04, 99 + k), 7000) * env(0.04, 0.001, 0.035), b0 + k + 0.5, 0.18)

    # 旋律（後半 8 小節）
    melody = [
        ('E5', 1), ('D5', 0.5), ('C5', 0.5), ('D5', 1), ('E5', 1), ('C5', 2), ('A4', 2),
        ('G4', 1), ('A4', 0.5), ('C5', 0.5), ('D5', 1), ('E5', 1), ('D5', 3), ('R', 1),
        ('E5', 1), ('G5', 1), ('A5', 1), ('G5', 0.5), ('E5', 0.5), ('D5', 2), ('C5', 2),
        ('D5', 1), ('E5', 1), ('C5', 1), ('B4', 1), ('A4', 4),
    ]
    at = 32.0
    for name, length in melody:
        if name != 'R':
            d = length * beat
            tone = fm(note_freq(name), 2.0, np.linspace(1.6, 0.4, int(SR * d)), d) * env(d, 0.01, 0.2, 0.55, 0.1)
            put(tone, at, 0.2)
        at += length
    return delay(out, beat * 0.75, 0.3, 0.25)


def main() -> None:
    for name, x in sfx().items():
        save(name, x)
    save('bgm_trial', bgm_trial(), 0.7)
    print('wrote audio to', OUT)


if __name__ == '__main__':
    main()
