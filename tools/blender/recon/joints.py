"""絵から起こしたハルの関節の位置（骨を入れる所）を決め、ai_character.py の --joints 用の JSON に書く。

  .venv-blender/bin/python tools/blender/recon/joints.py [--mesh <A ポーズの GLB>] [--out <json>]
      既定：--mesh build/recon/haru_textured_apose.glb（無ければ build/recon/prep/standin_textured.glb）
            --out  build/recon/prep/haru_joints.json

ai_character.py の自動の推定（頂点の水平の輪切り）は、面の大きさがそろった AI のメッシュ向け。
起こしたハルは平らな所の面が大きく（間引きが場所で違う）、頂点の輪切りに隙間ができて腕の軸を読み違える。
そこで：
  - 左右（x）と高さ（z）：正面の絵（calib.json の正投影）で読んだ値の表 ART_XZ（本人の左 = +X 側。右は鏡写し）
  - 前後（y）：メッシュのその場所の前後の幅の中央（その点のまわりの頂点の y の最小と最大の中点）
単位は m。表の値は haru_3d_front.png に 5cm の格子を重ねて読んだ（肩・肘・手首・指先、膝の琥珀の継ぎ目の中点など）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from lib import common as C  # noqa: E402

RECON = os.path.join(C.REPO, 'build', 'recon')

# 絵で読んだ関節（x, z、m）と、y を求める方法
#   'mid'：まわりの頂点の y の最小と最大の中点、'torso'：体の中央（|x|<0.06）の輪切りの中点、
#   'shaft'：靴の筒の高さ SHAFT_Z の輪切りの中点
ART_XZ = {
    'hips': ((0.0, 0.728), 'torso'),
    'spine': ((0.0, 0.845), 'torso'),
    'chest': ((0.0, 0.960), 'torso'),
    'neck': ((0.0, 1.128), 'torso'),
    'head': ((0.0, 1.180), 'torso'),
    'shoulder': ((0.040, 1.105), 'torso'),
    'upper_arm': ((0.137, 1.105), 'mid'),   # 肩の丸みの中心（上腕の軸と肩の高さの交点）
    'forearm': ((0.245, 0.912), 'mid'),     # 肘（袖口と籠手の間の肌）
    'hand': ((0.335, 0.755), 'mid'),        # 手首（手袋の袖口）
    'hand_end': ((0.400, 0.642), 'mid'),    # 手の先（手首から指先への 8 割）
    'thigh': ((0.095, 0.715), 'mid'),       # 股関節（股の付け根の 3cm 上、太ももの中心）
    'shin': ((0.143, 0.395), 'mid'),        # 膝（左右の琥珀の継ぎ目の中点）
    'foot': ((0.150, 0.090), 'shaft'),      # 足首（y は靴の筒の高さで測る。足首の高さではつま先の塊が混ざる）
}
SHAFT_Z = 0.16   # 靴の筒（爪先の塊より上）の高さ

# 左の籠手のレール（射出口）の手首側の端（x, z）
BLADE_XZ = (0.398, 0.755)


def load_points(path: str) -> np.ndarray:
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    pts = []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        n = len(o.data.vertices)
        a = np.empty(n * 3)
        o.data.vertices.foreach_get('co', a)
        a = a.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        pts.append(a @ mw[:3, :3].T + mw[:3, 3])
    return np.concatenate(pts)


def y_mid(pts: np.ndarray, x: float, z: float, how: str) -> float:
    if how == 'torso':
        m = (np.abs(pts[:, 0]) < 0.06) & (np.abs(pts[:, 2] - z) < 0.015)
    elif how == 'shaft':
        m = (np.abs(pts[:, 0] - x) < 0.05) & (np.abs(pts[:, 2] - SHAFT_Z) < 0.015)
    else:
        for r in (0.025, 0.04, 0.06):
            m = np.hypot(pts[:, 0] - x, pts[:, 2] - z) < r
            if m.sum() >= 8:
                break
    if m.sum() < 3:
        return 0.0
    y = pts[m, 1]
    return float((y.min() + y.max()) / 2)


def main() -> None:
    ap = argparse.ArgumentParser()
    default_mesh = os.path.join(RECON, 'haru_textured_apose.glb')
    if not os.path.exists(default_mesh):
        default_mesh = os.path.join(RECON, 'prep', 'standin_textured.glb')
    ap.add_argument('--mesh', default=default_mesh)
    ap.add_argument('--out', default=os.path.join(RECON, 'prep', 'haru_joints.json'))
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    pts = load_points(args.mesh)
    J = {}
    for name, ((x, z), how) in ART_XZ.items():
        J[name] = [x, round(y_mid(pts, x, z, how), 4), z]
    # 左右のすね・足先：足首の真下、つま先の 7 割
    feet = pts[(pts[:, 2] < 0.035) & (pts[:, 0] > 0)]
    toe_y = float(feet[:, 1].min()) if len(feet) else -0.1
    fy = J['foot'][1]
    J['toe'] = [J['foot'][0], round(fy + (toe_y - fy) * 0.7, 4), 0.012]
    # 光刃の根元：左の籠手の外側のレールの、手首側の端（正面の絵で読んだ外形の角）。ai_character.py の
    # --blade-anchor auto がこれを使う（'_' で始まる項目は骨にはならない）
    bx, bz = BLADE_XZ
    J['_blade_anchor'] = [bx, round(y_mid(pts, bx, bz, 'mid'), 4), bz]
    J['root'] = [0.0, 0.0, 0.0]
    J['head_end'] = [0.0, J['head'][1], round(float(pts[:, 2].max()), 4)]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(J, f, indent=2)
    print(json.dumps(J))
    print('wrote', args.out)


if __name__ == '__main__':
    main()
