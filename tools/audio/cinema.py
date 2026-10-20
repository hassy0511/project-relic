"""オープニングとオルドの停止の場面の音（自作シンセのみ）。

  .venv-blender/bin/python tools/audio/build.py --only=ordo_step,ordo_powerdown,amb_wind

ID：
  ordo_step       オルドの足が砂に着く音（遠くの地響き：低い打音・砂のざわめき・関節の金属の鳴り・長い余韻。約 3.2 秒）
  ordo_powerdown  動力が切れる音（下がっていく電気のうなり・機械のきしみ・震え。約 5.5 秒。足の打音は ordo_step を重ねる）
  amb_wind        砂漠の風（強弱のある低い風と、かすかな笛の音。12 秒のループ。つなぎ目は前後を重ねて消す）
"""
from __future__ import annotations

import numpy as np

from synth import SR, env, highpass, lowpass, noise, osc, pad_to, sweep, t_axis


def _smooth_lfo(dur: float, rate: float, seed: int) -> np.ndarray:
    """ゆっくり変わる 0〜1 の揺れ（rate Hz くらいの点を滑らかにつなぐ）"""
    n = int(SR * dur)
    k = max(4, int(dur * rate) + 4)
    pts = np.random.default_rng(seed).uniform(0.0, 1.0, k)
    x = np.linspace(0, k - 3, n)
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    return pts[i] * (1 - f) + pts[i + 1] * f


def _lp(x: np.ndarray, cutoff, poles: int = 3) -> np.ndarray:
    """1 次のローパスを重ねた、急な傾きのローパス（白い雑音から低い地響き・風を作る）"""
    for _ in range(poles):
        x = lowpass(x, cutoff)
    return x


def ordo_step() -> np.ndarray:
    d = 3.2
    t = t_axis(d)
    # 低い打音（58 → 27 Hz）。少しひずませて倍音を出す（スマホの小さなスピーカーでも重さが聞こえる）
    thump = np.tanh(2.2 * osc(sweep(58, 27, d, 0.35), d, 'sine')) * env(d, 0.012, 1.3, 0.0, 0.2)
    # 砂を押しつぶす重い面の音（低く絞った雑音。700 → 90 Hz）と、砂のつぶれる中くらいの音（250〜900 Hz、短く）
    body = _lp(noise(d, 31), sweep(700, 90, d, 0.5)) * env(d, 0.006, 0.9, 0.0, 0.1) * 3.0
    crunch = highpass(_lp(noise(d, 34), 900, 2), 250) * env(d, 0.004, 0.35, 0.0, 0.05) * 2.2
    # 地響きの余韻（130 Hz 以下の雑音、7 Hz でかすかに震える）
    tail = _lp(noise(d, 32), 130) * env(d, 0.08, 0.5, 0.55, 1.9) * (0.75 + 0.25 * np.sin(2 * np.pi * 7 * t)) * 5.0
    # 関節の金属の鳴り（倍音でない 3 つの音。少し遅れて）
    clank = pad_to(np.concatenate([np.zeros(int(SR * 0.05)),
                                    (osc(141, d - 0.05, 'sine') * 0.6 + osc(233, d - 0.05, 'sine') * 0.4 + osc(377, d - 0.05, 'sine') * 0.25)
                                    * env(d - 0.05, 0.004, 1.1)]), d)
    # 砂が散る音（高い雑音、ゆっくり消える）
    sand = highpass(noise(d, 33), 1800) * env(d, 0.04, 1.6, 0.0, 0.2)
    # 重い当たりの音（90 Hz と倍音。小さなスピーカーで「どん」と聞こえる高さ）
    knock = np.tanh(1.8 * osc(sweep(104, 82, d, 0.4), d, 'sine')) * env(d, 0.006, 0.45, 0.0, 0.05)
    return thump * 0.7 + body * 0.6 + knock * 0.55 + crunch * 1.1 + tail * 0.8 + clank * 0.5 + sand * 0.08


def ordo_powerdown() -> np.ndarray:
    d = 5.5
    t = t_axis(d)
    # 下がっていく電気のうなり（180 → 32 Hz、指数のように下がる）。終わりへ向かってふるえが増える
    f = 32 + 148 * np.exp(-t / 1.25)
    trem = 1.0 - 0.45 * (t / d) * (0.5 + 0.5 * np.sin(2 * np.pi * (6 + 5 * t / d) * t))
    whine = lowpass(osc(f, d, 'saw'), 700) * trem * env(d, 0.05, 0.4, 0.8, 1.6)
    hum = osc(f * 0.5, d, 'sine') * env(d, 0.08, 0.3, 0.85, 1.8)
    # 機械のきしみ（帯の雑音を、音の高さを下げながら何回か）
    creak = np.zeros(int(SR * d))
    rng = np.random.default_rng(41)
    for at, f0 in ((0.7, 420), (1.9, 330), (2.8, 260), (3.9, 210)):
        cd = 0.55 + rng.uniform(0, 0.25)
        x = osc(sweep(f0, f0 * 0.62, cd), cd, 'saw') * (0.6 + 0.4 * lowpass(noise(cd, int(f0)), 40) * 8)
        x = highpass(lowpass(x, 1400), 160) * env(cd, 0.03, cd * 0.7, 0.0, 0.1)
        i = int(SR * at)
        creak[i:i + len(x)] += x[: len(creak) - i]
    # 体の奥の震え（低い雑音、しだいに増えてから消える）
    rumble = _lp(noise(d, 42), 160) * env(d, 0.6, 1.0, 0.7, 2.6) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * t)) * 4.0
    return whine * 0.55 + hum * 0.45 + creak * 0.22 + rumble * 0.8


def amb_wind() -> np.ndarray:
    """12 秒のループ。14 秒作って、最後の 2 秒を最初に重ねてつなぐ"""
    loop, over = 12.0, 2.0
    d = loop + over
    gust = 0.35 + 0.65 * _smooth_lfo(d, 0.22, 51)
    slow = 0.6 + 0.4 * _smooth_lfo(d, 0.07, 52)
    base = _lp(noise(d, 53), 180 + 420 * gust) * gust * slow * 3.0
    air = highpass(_lp(noise(d, 54), 1400, 2), 500) * (gust ** 2) * 0.5
    whistle = _lp(highpass(noise(d, 55), 1000), 1300, 2) * np.clip(gust - 0.55, 0, 1) * 1.6
    x = base + air + whistle * 0.5
    n = int(SR * loop)
    m = int(SR * over)
    y = x[:n].copy()
    fade = np.linspace(0.0, 1.0, m)
    y[:m] = x[:m] * fade + x[n:n + m] * (1 - fade)
    return y


def cinema_sfx() -> dict[str, np.ndarray]:
    return {'ordo_step': ordo_step(), 'ordo_powerdown': ordo_powerdown(), 'amb_wind': amb_wind()}
