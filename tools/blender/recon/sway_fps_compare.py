"""godot_sway_fps.gd の 3 回（--fixed-fps 30・60・144）の出力を比べる：場面ごと（走って止まる・跳んで着地・ダッシュ）に、
刻みごとの揺れの角度の最大の、60 との差の平均・最大と、振れの山（W1_ハル再構築の結果.md 8.5）。
  python3 tools/blender/recon/sway_fps_compare.py <fps_30.log・fps_60.log・fps_144.log のあるフォルダ>
"""
import re
import sys

import numpy as np

root = sys.argv[1] if len(sys.argv) > 1 else '.'
S = {}
D = {}
for f in (30, 60, 144):
    t = open(f'{root}/fps_{f}.log', encoding='utf-8').read()
    S[f] = np.array([float(x) for x in re.search(r'^SWAY (.*)$', t, re.M).group(1).split()])
    D[f] = np.array([[float(c) for c in x.split(',')] for x in re.search(r'^DIRS (.*)$', t, re.M).group(1).split()])
# 刻み 100 から：止まる 110〜149、跳ぶ・着地 150〜229、ダッシュ 230〜（godot_sway_fps.gd の SEQ）
phases = {'走って止まる': (10, 50), '跳んで着地': (50, 130), 'ダッシュ': (130, len(S[60]))}
for name, (a, b) in phases.items():
    for f in (30, 144):
        d = np.abs(S[f][a:b] - S[60][a:b])
        print(f'{name} {f}: 差 平均 {d.mean():.2f} 度・最大 {d.max():.2f} 度／山 {S[f][a:b].max():.1f} 度（60 は {S[60][a:b].max():.1f} 度）')
for f in (30, 144):
    d = np.abs(S[f] - S[60])
    ang = np.degrees(np.arccos(np.clip((D[f] * D[60]).sum(axis=1), -1.0, 1.0)))
    print(f'全体 {f}: 差 平均 {d.mean():.2f} 度・最大 {d.max():.2f} 度／終わりの骨の向きの差 最大 {ang.max():.2f} 度')
