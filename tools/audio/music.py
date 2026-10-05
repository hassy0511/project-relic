"""第 1 章の音楽（短いループ 5 曲）と、足りない効果音。自作シンセのみ（外部の素材なし）。

  .venv-blender/bin/python tools/audio/build.py   で public/assets/audio と godot/assets/audio へ書き出す
ID：bgm_town_day / bgm_town_night / bgm_ruins / bgm_boss / bgm_end（ファンファーレ、ループしない）
"""
from __future__ import annotations

import numpy as np

from synth import (SR, delay, env, fm, highpass, lowpass, noise, note_freq, osc, pad_to, sweep, t_axis)


class Track:
    def __init__(self, bpm: float, bars: int, tail: float = 0.0, beats_per_bar: int = 4):
        self.beat = 60.0 / bpm
        self.bpb = beats_per_bar
        self.n_loop = int(SR * self.beat * beats_per_bar * bars)
        self.out = np.zeros(self.n_loop + int(SR * tail))

    def put(self, x: np.ndarray, at_beat: float, gain: float = 1.0) -> None:
        i = int(SR * at_beat * self.beat)
        if i >= len(self.out):
            return
        j = min(len(self.out), i + len(x))
        self.out[i:j] += x[: j - i] * gain

    def note(self, name: str, at_beat: float, beats: float, wave: str = 'tri', gain: float = 0.3,
             a: float = 0.005, d: float = 0.15, s: float = 0.5, r: float = 0.08) -> None:
        dur = beats * self.beat
        self.put(osc(note_freq(name), dur, wave) * env(dur, a, d, s, r), at_beat, gain)

    def finish(self, loop: bool = True) -> np.ndarray:
        """ループの継ぎ目：はみ出した余韻を先頭へ重ねる"""
        if not loop:
            return self.out
        y = self.out[: self.n_loop].copy()
        tail = self.out[self.n_loop:]
        y[: len(tail)] += tail
        return y


def _kick(dur: float = 0.2) -> np.ndarray:
    return osc(sweep(150, 45, dur), dur, 'sine') * env(dur, 0.001, dur * 0.9)


def _snare(seed: int, dur: float = 0.16) -> np.ndarray:
    return highpass(noise(dur, seed), 1500) * env(dur, 0.001, dur * 0.85) * 0.8


def _hat(seed: int, dur: float = 0.04) -> np.ndarray:
    return highpass(noise(dur, seed), 6000) * env(dur, 0.001, dur * 0.85)


def _echo(tr: Track, beats: float, fb: float, mix: float) -> None:
    tr.out = delay(tr.out, tr.beat * beats, fb, mix)


def town_day() -> np.ndarray:
    """昼の町：明るく、のどかな C メジャー。ゆったり 92 BPM、8 小節"""
    tr = Track(92, 8, tail=2.0)
    prog = [['C3', 'E4', 'G4'], ['A2', 'E4', 'A4'], ['F2', 'C4', 'A4'], ['G2', 'D4', 'B4']] * 2
    for bar, ch in enumerate(prog):
        b0 = bar * 4
        root = ch[0]
        # 弾むベース（1 拍と 3 拍）
        tr.note(root, b0, 0.9, 'tri', 0.34, 0.004, 0.25, 0.3)
        tr.note(root[:-1] + str(int(root[-1]) + 1), b0 + 2, 0.9, 'tri', 0.26, 0.004, 0.25, 0.3)
        # 爪弾き（3 連の分散和音）
        for k, nm in enumerate([ch[1], ch[2], ch[1], ch[2], ch[1], ch[2], ch[2], ch[1]]):
            tr.note(nm, b0 + k * 0.5, 0.45, 'tri', 0.16, 0.002, 0.3, 0.0, 0.05)
        # 柔らかいパッド
        pad = sum(osc(note_freq(x) * (1.0 + 0.002 * i), tr.beat * 4, 'sine') for i, x in enumerate(ch))
        tr.put(pad * env(tr.beat * 4, 0.4, 0.5, 0.6, 0.6), b0, 0.07)
        # 軽い刻み
        for k in range(4):
            tr.put(_hat(bar * 7 + k), b0 + k + 0.5, 0.12)
    mel = [('E5', 1.5), ('D5', 0.5), ('C5', 1), ('D5', 1), ('E5', 2), ('G5', 1), ('E5', 1),
           ('A5', 1.5), ('G5', 0.5), ('E5', 1), ('C5', 1), ('D5', 3), ('R', 1),
           ('C5', 1), ('E5', 1), ('F5', 1.5), ('E5', 0.5), ('D5', 2), ('C5', 2),
           ('B4', 1), ('D5', 1), ('G5', 1), ('F5', 1), ('E5', 3), ('R', 1)]
    at = 0.0
    for nm, ln in mel:
        if nm != 'R':
            tr.note(nm, at, ln * 0.95, 'tri', 0.22, 0.01, 0.2, 0.55, 0.15)
        at += ln
    _echo(tr, 0.75, 0.3, 0.25)
    return tr.finish()


def town_night() -> np.ndarray:
    """停電の夜の町：静かな A マイナー。低い持続音とまばらな鐘。56 BPM、8 小節"""
    tr = Track(56, 8, tail=3.0)
    prog = [['A2', 'E3', 'C4'], ['F2', 'C3', 'A3'], ['D3', 'A3', 'F4'], ['E2', 'B2', 'G#3']] * 2
    for bar, ch in enumerate(prog):
        b0 = bar * 4
        pad = sum(osc(note_freq(x) * (1.0 + 0.0025 * i), tr.beat * 4.4, 'saw') for i, x in enumerate(ch))
        pad = lowpass(pad, 700)
        tr.put(pad * env(tr.beat * 4.4, 1.2, 1.0, 0.7, 1.4), b0, 0.12)
        tr.note(ch[0], b0, 3.8, 'sine', 0.35, 0.05, 0.6, 0.6, 0.8)
    bell = [('E5', 0), ('A5', 2), ('C6', 5), ('B5', 8), ('E5', 11), ('G5', 14), ('A5', 18), ('E5', 22),
            ('C6', 24), ('A5', 27), ('D5', 30), ('E5', 33), ('B5', 36), ('A5', 40), ('E5', 44), ('C5', 48),
            ('E5', 52), ('A5', 56), ('G5', 60), ('E5', 62)]
    for nm, at in bell:
        f = note_freq(nm)
        dur = 3.2
        x = fm(f, 3.5, np.linspace(1.4, 0.0, int(SR * dur)), dur) * env(dur, 0.002, 2.5, 0.0, 0.5)
        tr.put(x, at, 0.17)
    _echo(tr, 1.5, 0.45, 0.5)
    return tr.finish()


def ruins() -> np.ndarray:
    """遺構：低い持続音、脈打つ低音、金属のカチカチ音、遠い鐘。D マイナー、78 BPM、8 小節"""
    tr = Track(78, 8, tail=2.5)
    roots = ['D2', 'D2', 'Bb2' if False else 'A#2', 'A2', 'D2', 'D2', 'F2', 'A2']
    notes = {'A#2': 'A#2'}
    for bar, rt in enumerate(roots):
        b0 = bar * 4
        for k in range(8):
            f = note_freq(rt) * (2 if k % 4 == 3 else 1)
            dur = tr.beat * 0.45
            x = lowpass(osc(f, dur, 'saw'), 500) * env(dur, 0.005, 0.15, 0.4, 0.05)
            tr.put(x, b0 + k * 0.5, 0.42)
        pad = lowpass(sum(osc(note_freq(rt) * m * (1 + 0.003 * i), tr.beat * 4.2, 'saw') for i, m in enumerate([2, 3, 4.03])), 600)
        tr.put(pad * env(tr.beat * 4.2, 1.0, 1.0, 0.6, 1.0), b0, 0.1)
        # 金属の音（不規則）
        for at in ([0.75, 2.5] if bar % 2 == 0 else [1.5, 3.25, 3.75]):
            x = osc(1900 + 70 * bar, 0.06, 'square') * env(0.06, 0.001, 0.05) * 0.5
            tr.put(x, b0 + at, 0.12)
    for nm, at in [('A5', 2), ('D6', 9), ('F5', 14), ('A5', 18), ('C6', 25), ('D5', 29)]:
        dur = 2.4
        x = fm(note_freq(nm), 1.41, np.linspace(1.8, 0.0, int(SR * dur)), dur) * env(dur, 0.002, 1.8, 0.0, 0.5)
        tr.put(x, at, 0.1)
    for k in range(8):
        tr.put(_kick(0.3), k * 4, 0.5)
    _echo(tr, 0.75, 0.4, 0.35)
    return tr.finish()


def boss() -> np.ndarray:
    """ボス：速い低音、鋭い旋律、ドラム。E マイナー、150 BPM、16 小節"""
    tr = Track(150, 16, tail=1.5)
    roots = ['E2', 'E2', 'C3', 'D3'] * 4
    for bar, rt in enumerate(roots):
        b0 = bar * 4
        for k in range(16):
            f = note_freq(rt) * (2 if k % 8 in (3, 7) else 1)
            dur = tr.beat * 0.22
            tr.put(osc(f, dur, 'saw') * env(dur, 0.002, 0.1, 0.5, 0.03), b0 + k * 0.25, 0.22)
        for k in range(4):
            tr.put(_kick(), b0 + k, 0.75 if k % 2 == 0 else 0.5)
            if k % 2 == 1:
                tr.put(_snare(bar * 4 + k), b0 + k, 0.55)
            tr.put(_hat(200 + bar * 4 + k), b0 + k + 0.5, 0.18)
        ch = {'E2': ['E4', 'G4', 'B4'], 'C3': ['E4', 'G4', 'C5'], 'D3': ['F#4', 'A4', 'D5']}[rt]
        pad = lowpass(sum(osc(note_freq(x) * (1 + 0.004 * i), tr.beat * 4, 'saw') for i, x in enumerate(ch)), 1800)
        tr.put(pad * env(tr.beat * 4, 0.02, 0.4, 0.6, 0.1), b0, 0.1)
    riff = [('E5', 0.5), ('E5', 0.5), ('G5', 0.5), ('E5', 0.5), ('B5', 1), ('A5', 0.5), ('G5', 0.5),
            ('E5', 0.5), ('E5', 0.5), ('G5', 0.5), ('A5', 0.5), ('B5', 1), ('R', 1),
            ('C6', 0.5), ('C6', 0.5), ('B5', 0.5), ('G5', 0.5), ('E5', 1), ('G5', 1),
            ('A5', 0.5), ('A5', 0.5), ('F#5', 0.5), ('A5', 0.5), ('D6', 2)]
    at = 16.0
    for rep in range(2):
        for nm, ln in riff:
            if nm != 'R':
                dur = ln * tr.beat
                x = fm(note_freq(nm), 2.0, np.linspace(2.2, 0.6, int(SR * dur)), dur) * env(dur, 0.004, 0.12, 0.55, 0.05)
                tr.put(x, at, 0.2)
            at += ln
        if rep == 0:
            at = 40.0
    _echo(tr, 0.5, 0.3, 0.2)
    return tr.finish()


def fanfare() -> np.ndarray:
    """第 1 章クリアのファンファーレ（ループしない）。C メジャー、104 BPM、約 12 秒"""
    tr = Track(104, 5, tail=3.0)
    chords = [(0, ['C3', 'E4', 'G4', 'C5'], 4), (4, ['F2', 'A3', 'C4', 'F4'], 2), (6, ['G2', 'B3', 'D4', 'G4'], 2),
              (8, ['C3', 'G3', 'E4', 'C5'], 8), (16, ['C3', 'G3', 'C4', 'E4'], 4)]
    for b0, ch, ln in chords:
        dur = ln * tr.beat
        pad = lowpass(sum(osc(note_freq(x) * (1 + 0.002 * i), dur + 0.5, 'saw') for i, x in enumerate(ch)), 2200)
        tr.put(pad * env(dur + 0.5, 0.03, 0.3, 0.7, 0.5), b0, 0.12)
        tr.note(ch[0], b0, ln * 0.95, 'tri', 0.3, 0.01, 0.3, 0.7, 0.4)
    mel = [('G4', 0.5), ('C5', 0.5), ('E5', 1), ('G5', 1.5), ('E5', 0.5),
           ('F5', 1), ('A5', 1), ('G5', 1), ('D5', 1),
           ('E5', 1), ('G5', 1), ('C6', 3), ('B5', 1), ('C6', 4), ('R', 4)]
    at = 0.0
    for nm, ln in mel:
        if nm != 'R':
            dur = ln * tr.beat
            x = fm(note_freq(nm), 2.0, np.linspace(1.5, 0.3, int(SR * dur)), dur) * env(dur, 0.01, 0.2, 0.6, 0.2)
            tr.put(x, at, 0.22)
        at += ln
    for b in [0, 8]:
        tr.put(_kick(0.3), b, 0.7)
    tr.put(highpass(noise(1.4, 3), 3000) * env(1.4, 0.01, 1.2) * 0.25, 8, 0.3)
    _echo(tr, 0.75, 0.35, 0.3)
    return tr.finish(loop=False)


# ---------------------------------------------------------------- 効果音（足りないもの）

def extra_sfx() -> dict[str, np.ndarray]:
    s: dict[str, np.ndarray] = {}
    d = 0.7
    s['door'] = (lowpass(noise(d, 21), sweep(1800, 300, d)) * env(d, 0.01, 0.5) * 0.7
                 + osc(sweep(130, 70, d), d, 'saw') * env(d, 0.02, 0.45) * 0.4)
    d = 0.18
    s['locked'] = osc(180, d, 'square') * env(d, 0.001, 0.15) * 0.5 + osc(150, d, 'square') * env(d, 0.05, 0.12) * 0.3
    d = 0.22
    s['switch'] = (osc(sweep(600, 300, d, 0.4), d, 'square') * env(d, 0.001, 0.08) * 0.4
                   + highpass(noise(d, 22), 2500) * env(d, 0.001, 0.03) * 0.4)
    d = 1.4
    s['lift'] = (osc(70 + 8 * np.sin(2 * np.pi * 9 * t_axis(d)), d, 'saw') * env(d, 0.15, 0.2, 0.7, 0.5) * 0.5
                 + lowpass(noise(d, 23), 700) * env(d, 0.15, 0.2, 0.6, 0.5) * 0.4)
    d = 1.8
    arp = np.concatenate([osc(note_freq(n), 0.3, 'sine') * env(0.3, 0.005, 0.28) for n in ['E5', 'A5', 'C6', 'E6']])
    s['beacon'] = delay(pad_to(arp, d), 0.18, 0.45, 0.5) + pad_to(osc(note_freq('A3'), 1.6, 'sine') * env(1.6, 0.1, 1.4) * 0.3, d)
    d = 0.9
    s['boss_phase'] = (osc(sweep(300, 70, d, 0.6), d, 'saw') * env(d, 0.005, 0.8) * 0.6
                       + lowpass(noise(d, 24), sweep(3000, 200, d)) * env(d, 0.001, 0.8) * 0.6)
    d = 1.8
    s['rumble'] = (lowpass(noise(d, 25), 300) * env(d, 0.15, 0.3, 0.8, 0.8) * (0.7 + 0.3 * np.sin(2 * np.pi * 13 * t_axis(d)))
                   + osc(48, d, 'sine') * env(d, 0.1, 0.3, 0.8, 0.8) * 0.5)
    d = 0.06
    s['blip'] = osc(660, d, 'square') * env(d, 0.001, 0.05) * 0.3
    d = 0.1
    s['ui_back'] = osc(sweep(800, 500, d), d, 'tri') * env(d, 0.001, 0.09) * 0.5
    d = 0.16
    s['buy'] = (osc(1400, d, 'sine') * env(d, 0.001, 0.05) * 0.5
                + pad_to(np.concatenate([np.zeros(int(SR * 0.06)), osc(2000, 0.1, 'sine') * env(0.1, 0.001, 0.09) * 0.5]), d))
    d = 0.5
    s['complete'] = delay(pad_to(np.concatenate([osc(note_freq(n), 0.1, 'tri') * env(0.1, 0.002, 0.09) * 0.6 for n in ['G5', 'C6', 'G6']]), d), 0.1, 0.4, 0.4)
    d = 0.4
    s['pass'] = highpass(noise(d, 26), 800) * env(d, 0.05, 0.3) * 0.4
    return s
