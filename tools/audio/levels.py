"""効果音の数値の確かめ（耳で聞く前に、数で形を見る）：帯ごとの大きさ・包絡（立ち上がり・消えるまで）・全体の大きさ。

  .venv-blender/bin/python tools/audio/levels.py ordo_thud ordo_thud_in ordo_thud_deep ordo_rattle ordo_step

帯（Hz）：<40・40–80・80–160・160–320・320–640・640–2k・2k–8k・>8k。値は帯の中の音の強さの割合（dB、全部の帯の和 = 0 dB）。
包絡：10 ms ごとの RMS。立ち上がり = 最大の 10 % → 90 % の時間、-20 dB = 最大から 20 dB 下がるまでの時間、
RMS = 全体の実効値（dBFS。ファイルは最大 0.8 にそろえてあるので、ゲームでの大きさは呼ぶ側の gain で決まる）。
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

BANDS = [(0, 40), (40, 80), (80, 160), (160, 320), (320, 640), (640, 2000), (2000, 8000), (8000, 30000)]


def analyze(path: str) -> dict:
    x, sr = sf.read(path)
    if x.ndim > 1:
        x = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    total = spec.sum() + 1e-20
    bands = [10 * np.log10(spec[(freqs >= lo) & (freqs < hi)].sum() / total + 1e-12) for lo, hi in BANDS]
    hop = int(sr * 0.01)
    frames = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    pk = frames.max() + 1e-12
    i_pk = int(frames.argmax())
    i10 = int(np.argmax(frames >= pk * 0.1))
    i90 = int(np.argmax(frames >= pk * 0.9))
    after = np.where(frames[i_pk:] < pk * 0.1)[0]
    t20 = (after[0] if len(after) else len(frames) - i_pk) * 0.01
    centroid = float((freqs * spec).sum() / total)
    return {"dur": len(x) / sr, "peak": float(np.abs(x).max()), "rms_db": 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12),
            "attack_ms": (i90 - i10) * 10.0, "peak_ms": i_pk * 10.0, "to_m20_s": t20, "centroid": centroid, "bands": bands}


def main() -> None:
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ordo_thud', 'ordo_thud_in', 'ordo_thud_deep', 'ordo_rattle', 'ordo_step']
    head = '  '.join(f'{lo}-{hi}' if hi < 30000 else f'>{lo}' for lo, hi in BANDS)
    print(f'{"音":16s} 長さ  最大  RMS    立上 最大の時 -20dB 重心Hz | 帯 dB: {head}')
    for n in names:
        p = os.path.join(REPO, 'godot', 'assets', 'audio', f'{n}.ogg')
        a = analyze(p)
        b = ' '.join(f'{v:6.1f}' for v in a['bands'])
        print(f'{n:16s} {a["dur"]:4.1f}s {a["peak"]:.2f} {a["rms_db"]:6.1f}dB {a["attack_ms"]:4.0f}ms {a["peak_ms"]:5.0f}ms '
              f'{a["to_m20_s"]:4.2f}s {a["centroid"]:6.0f} | {b}')


if __name__ == '__main__':
    main()
