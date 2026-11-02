"""町で感じるオルドの足音（自作シンセのみ）。場面の足音 ordo_step（cinema.py）より遠く・柔らかく・低い。

  .venv-blender/bin/python tools/audio/build.py --only=ordo_thud,ordo_thud_in,ordo_thud_deep,ordo_rattle

ID：
  ordo_thud       町の外（甲羅の上）で聞く足音。120 m 下の砂に足が着いた揺れが、背の骨組みを伝わってくる遠い地響き。
                  耳より体で感じる音：打ち始めをやわらかく（約 40 ms で立ち上がる）、500 Hz より上はほとんど無い。約 3 秒
  ordo_thud_in    家の中で聞く足音：ordo_thud をもっとこもらせ（壁ごしの低い音）、家の骨組みが小さく鳴る音（板の「ごとん」）を足す。約 2.6 秒
  ordo_thud_deep  遺構（オルドの体の中）で聞く足音：重い地響きに、大きな鉄の胴が鳴る倍音でない響き（52〜241 Hz）と低いうなりを足す。約 4 秒
  ordo_rattle     棚の器・道具が小さく鳴る音（家の中で、足音のあと少し遅れて）。高い音の小さな粒が 0.5 秒ほど。約 0.8 秒
  ordo_rattle_2, ordo_rattle_3  同じ器の音の別の鳴り方（粒の数・間・高さが違う。ゲームは 3 つから 1 つを選ぶ）
長い時間遊んでも気にならないよう、どれも打ち始めは鋭くしない。大きさはゲームの側（OrdoSteps）が脚までの距離で決める。
スマホの小さなスピーカー（300 Hz より下はほとんど鳴らない）でも足音と分かるよう、どの足音にも骨組みの「ごとっ」という中くらいの
高さの響き（250〜800 Hz。_mid_knock）を、低い地響きの下に小さく重ねる。
"""
from __future__ import annotations

import numpy as np

from synth import SR, env, highpass, lowpass, noise, osc, pad_to, sweep, t_axis


# 骨組みの「ごとっ」（_mid_knock）の大きさ：スマホのスピーカーの帯（300 Hz より上）で、町の曲の中くらいの大きさに届く程度
KNOCK = 0.5


def _lp(x: np.ndarray, cutoff, poles: int = 3) -> np.ndarray:
    for _ in range(poles):
        x = lowpass(x, cutoff)
    return x


def _soft_env(d: float, a: float, dec: float, sus: float = 0.0, rel: float = 0.2) -> np.ndarray:
    """立ち上がりを丸くした ADSR（打ち始めの角を取る：直線の立ち上がりを smoothstep に）"""
    e = env(d, a, dec, sus, rel)
    n = int(SR * a)
    if n > 1:
        u = np.linspace(0.0, 1.0, n, endpoint=False)
        e[:n] = u * u * (3 - 2 * u)
    return e


def _later(x: np.ndarray, at: float, d: float) -> np.ndarray:
    return pad_to(np.concatenate([np.zeros(int(SR * at)), x]), d)


def _thud_core(d: float, seed: int) -> np.ndarray:
    """遠い地響きの芯：とても低い打音（46 → 30 Hz）・低く絞った雑音の面・小さなスピーカー用の「どん」（88 Hz 前後）・余韻"""
    t = t_axis(d)
    sub = np.tanh(1.6 * osc(sweep(46, 30, d, 0.5), d, 'sine')) * _soft_env(d, 0.035, 1.1, 0.0, 0.3)
    body = _lp(noise(d, seed), sweep(220, 70, d, 0.6)) * _soft_env(d, 0.04, 0.8, 0.0, 0.2) * 3.2
    knock = np.tanh(2.0 * osc(sweep(96, 80, d, 0.4), d, 'sine')) * _soft_env(d, 0.025, 0.38, 0.0, 0.1)
    # 骨組みを伝わる中くらいの面の音（150〜350 Hz の雑音、短く）：スマホの小さなスピーカーでも「どん」と分かる高さ
    frame = highpass(_lp(noise(d, seed + 2), 350, 2), 150) * _soft_env(d, 0.03, 0.3, 0.0, 0.05) * 2.0
    tail = _lp(noise(d, seed + 1), 90) * _soft_env(d, 0.15, 0.6, 0.4, 1.6) * (0.8 + 0.2 * np.sin(2 * np.pi * 5 * t)) * 5.0
    return sub * 0.8 + body * 0.5 + knock * 0.36 + frame * 0.55 + tail * 0.55


def _mid_knock(d: float, seed: int, f0: float, dec: float = 0.22, at: float = 0.02) -> np.ndarray:
    """骨組みの「ごとっ」：倍音でない 3 つの音（f0・1.47 f0・2.09 f0。高いものほど早く消える）と、250〜800 Hz の短い雑音。
    打ち始めは 12 ms で丸く立ち上げる（鋭くしない）。スマホのスピーカーで足音と分かる高さ"""
    tone = np.zeros(int(SR * d))
    for k, (m, a) in enumerate(((1.0, 0.6), (1.47, 0.35), (2.09, 0.2))):
        tone += osc(f0 * m * (1.0 - 0.02 * t_axis(d) / d), d, 'sine') * a * _soft_env(d, 0.012, dec / (1.0 + 0.5 * k), 0.0, 0.05)
    grit = highpass(_lp(noise(d, seed), 800, 2), 250) * _soft_env(d, 0.01, dec * 0.6, 0.0, 0.05) * 2.5
    return _later(_lp(tone + grit * 0.5, 1100, 2), at, d)


def ordo_thud() -> np.ndarray:
    d = 3.0
    x = _thud_core(d, 61)
    # 遠くの骨組みの低いうなり（倍音でない 3 つの音。少し遅れて、ゆっくり消える）
    groan = (osc(63, d, 'sine') * 0.5 + osc(97, d, 'sine') * 0.3 + osc(151, d, 'sine') * 0.18) * _soft_env(d, 0.25, 1.4, 0.0, 0.3)
    x = x + _later(groan[: int(SR * (d - 0.12))], 0.12, d) * 0.12
    # 高い音は落とす（遠く・体で感じる音）。スマホ用の骨組みの「ごとっ」はそのあとに小さく
    return _lp(x, 650, 2) + _mid_knock(d, 64, 330.0) * KNOCK


def ordo_thud_in() -> np.ndarray:
    d = 2.6
    x = _lp(_thud_core(d, 71), 170, 2) * 1.4
    # 家の骨組みが小さく鳴る：板の箱の「ごとん」（150 Hz 前後の短い響き）と、梁のかすかなきしみ（少し遅れて）
    box = (osc(sweep(158, 142, d, 0.5), d, 'sine') * 0.7 + osc(231, d, 'sine') * 0.3) * _soft_env(d, 0.012, 0.22, 0.0, 0.05)
    cd = 0.55
    creak = highpass(_lp(osc(sweep(290, 215, cd), cd, 'saw') * (0.6 + 0.4 * _lp(noise(cd, 72), 30) * 8), 900, 2), 150)
    creak = creak * _soft_env(cd, 0.06, 0.4, 0.0, 0.1)
    return x + _later(box, 0.03, d) * 0.22 + _later(creak, 0.35, d) * 0.05 + _mid_knock(d, 74, 280.0, 0.18) * KNOCK * 1.8


def ordo_thud_deep() -> np.ndarray:
    d = 4.0
    t = t_axis(d)
    x = _thud_core(d, 81)
    sub = np.tanh(2.0 * osc(sweep(40, 26, d, 0.45), d, 'sine')) * _soft_env(d, 0.03, 1.5, 0.0, 0.4)
    # 鉄の胴の響き：倍音でない 5 つの音が、高いものほど早く消える
    hull = np.zeros(int(SR * d))
    for f, a, dec in ((52, 0.55, 2.6), (81, 0.42, 2.1), (118, 0.3, 1.6), (173, 0.18, 1.1), (241, 0.1, 0.8)):
        hull += osc(f * (1.0 - 0.012 * t / d), d, 'sine') * a * _soft_env(d, 0.05, dec, 0.0, 0.3)
    # 低いうなり（押しつぶされた骨組みが鳴る。少し遅れて、ゆっくり上がって消える）
    groan = _lp(osc(sweep(72, 54, d, 0.7), d, 'saw'), 260, 2) * _soft_env(d, 0.35, 1.8, 0.0, 0.5)
    y = x * 0.8 + sub * 0.6 + _later(hull, 0.04, d) * 0.45 + _later(groan, 0.2, d) * 0.3
    # 鉄の胴の「ごーん」（中くらいの高さ。長めに響く）
    return _lp(y, 700, 2) + _mid_knock(d, 84, 360.0, 0.45, 0.04) * KNOCK * 0.6


def ordo_rattle(seed: int = 91, n_hits: int = 11, shelf_f: float = 410.0) -> np.ndarray:
    """器・道具が小さく鳴る：短い高い粒（陶器の 2 つの響き＋かすかな雑音）を 0.5 秒にばらまき、だんだん弱く"""
    d = 0.8
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * d))
    for k in range(n_hits):
        at = 0.02 + rng.uniform(0.0, 0.5) * (k / n_hits) ** 0.7
        hd = 0.07
        f1 = rng.uniform(2100, 2900)
        f2 = f1 * rng.uniform(1.48, 1.62)
        tick = (osc(f1, hd, 'sine') * 0.6 + osc(f2, hd, 'sine') * 0.35) * env(hd, 0.0015, 0.03, 0.0, 0.01)
        tick += highpass(noise(hd, seed + 1 + k), 3000) * env(hd, 0.0005, 0.006) * 0.4
        g = (1.0 - 0.6 * k / n_hits) * rng.uniform(0.5, 1.0)
        i = int(SR * at)
        out[i:i + len(tick)] += tick[: len(out) - i] * g
    # 棚の板が小さく鳴る低めの響き（最初に）
    shelf = osc(shelf_f, d, 'sine') * env(d, 0.003, 0.08) * 0.25
    return out + shelf


def steps_sfx() -> dict[str, np.ndarray]:
    return {'ordo_thud': ordo_thud(), 'ordo_thud_in': ordo_thud_in(), 'ordo_thud_deep': ordo_thud_deep(),
            'ordo_rattle': ordo_rattle(), 'ordo_rattle_2': ordo_rattle(57, 8, 372.0), 'ordo_rattle_3': ordo_rattle(133, 14, 455.0)}
