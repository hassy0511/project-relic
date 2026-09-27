"""MVP 用の仮の地形（グレーボックス）。

docs/design/30_レベルデザイン設計.md 5 章の構成：
  A：スタート（段差と溝の計測場、案内役の NPC）
  通路：幅 4m × 長さ 30m
  B：戦闘の部屋（遮蔽物の柱、歩哨型と突撃型）
  ひび割れた壁の奥の小部屋（宝箱）

座標：Blender の X = ゲームの X、Blender の -Y = ゲームの +Z（北）。
ここでは読みやすさのため、ゲーム座標 (x, y=高さ, z) で書き、変換して置く。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib import common as C  # noqa: E402

FLOOR = C.hex_color('#8a8478')
WALL = C.hex_color('#6f6a62')
STEP = C.hex_color('#a89a7c')
PILLAR = C.hex_color('#7c7465')
ACCENT = C.hex_color('#c98a3a')


def g2b(x: float, y: float, z: float) -> tuple[float, float, float]:
    """ゲーム座標 → Blender 座標"""
    return (x, -z, y)


def gbox(name: str, center: tuple[float, float, float], size: tuple[float, float, float], mat) -> None:
    """ゲーム座標の中心と大きさ（幅 x, 高さ y, 奥行き z）で箱を置く"""
    sx, sy, sz = size
    C.box(name, g2b(*center), (sx, sz, sy), mat)


def marker(name: str, x: float, y: float, z: float, yaw_deg: float = 0.0) -> None:
    # ゲームの yaw（+Z が 0、+X が 90）→ Blender の Z 回転。-Y 方向が 0
    C.empty('m_' + name, g2b(x, y, z), yaw_deg)


def build() -> None:
    C.reset_scene()
    floor = C.material('grey_floor', FLOOR, roughness=0.9)
    wall = C.material('grey_wall', WALL, roughness=0.9)
    step = C.material('grey_step', STEP, roughness=0.8)
    pillar = C.material('grey_pillar', PILLAR, roughness=0.9)
    accent = C.material('grey_accent', ACCENT, roughness=0.6)

    # ---- A：スタートの部屋（中心 z=0、20m 四方）
    gbox('A_floor', (0, -0.5, 0), (20, 1, 20), floor)
    gbox('A_wall_s', (0, 3, -10.5), (22, 8, 1), wall)
    gbox('A_wall_w', (-10.5, 3, 0), (1, 8, 20), wall)
    gbox('A_wall_e', (10.5, 3, 0), (1, 8, 20), wall)
    gbox('A_wall_n_l', (-6.5, 3, 10.5), (9, 8, 1), wall)
    gbox('A_wall_n_r', (6.5, 3, 10.5), (9, 8, 1), wall)
    # 段差の計測（1.0m、1.8m、2.4m）
    gbox('A_step_10', (-7, 0.5, -6), (3, 1.0, 3), step)
    gbox('A_step_18', (-7, 0.9, -2), (3, 1.8, 3), step)
    gbox('A_step_24', (-7, 1.2, 2), (3, 2.4, 3), step)
    # 溝の計測：高台の上に 3m、5m、8m の溝（落ちても床に戻るだけ）
    gbox('A_ledge_1', (6.5, 1.0, -8), (5, 2, 3), step)
    gbox('A_ledge_2', (6.5, 1.0, -2), (5, 2, 3), step)   # 溝 3m
    gbox('A_ledge_3', (6.5, 1.0, 6), (5, 2, 3), step)    # 溝 5m
    gbox('A_ramp_block', (8.5, 0.5, -4.5), (1, 1, 1), accent)
    # 高台へ上がる階段
    gbox('A_stair_1', (3.4, 0.25, -8), (1.2, 0.5, 3), step)
    gbox('A_stair_2', (4.6, 0.5, -8), (1.2, 1.0, 3), step)
    gbox('A_stair_3', (5.8, 0.75, -8), (1.2, 1.5, 3), step)

    # ---- 通路（幅 4m、長さ 30m、z=10〜40）
    gbox('C_floor', (0, -0.5, 25), (4, 1, 30), floor)
    gbox('C_wall_w', (-2.5, 2.5, 25), (1, 6, 30), wall)
    gbox('C_wall_e', (2.5, 2.5, 25), (1, 6, 30), wall)
    gbox('C_ceiling', (0, 5.0, 25), (6, 1, 30), wall)

    # ---- B：戦闘の部屋（24m 四方、中心 z=52）
    gbox('B_floor', (0, -0.5, 52), (24, 1, 24), floor)
    gbox('B_wall_s_l', (-7.5, 4, 39.5), (11, 10, 1), wall)
    gbox('B_wall_s_r', (7.5, 4, 39.5), (11, 10, 1), wall)
    gbox('B_wall_w', (-12.5, 4, 52), (1, 10, 24), wall)
    gbox('B_wall_e', (12.5, 4, 52), (1, 10, 24), wall)
    gbox('B_wall_n_l', (-7.5, 4, 64.5), (11, 10, 1), wall)
    gbox('B_wall_n_r', (7.5, 4, 64.5), (11, 10, 1), wall)
    for i, (x, z) in enumerate([(-5, 47), (5, 47), (-5, 57), (5, 57)]):
        gbox(f'B_pillar_{i}', (x, 2.5, z), (1.6, 5, 1.6), pillar)
    gbox('B_cover', (0, 0.6, 52), (4, 1.2, 1), step)

    # ---- ひび割れた壁の奥の小部屋（z=65〜73）。入口はひび割れた壁（ゲーム側で置く）でふさぐ
    gbox('D_floor', (0, -0.5, 70), (8, 1, 10), floor)
    gbox('D_wall_w', (-4.5, 2.5, 70), (1, 6, 10), wall)
    gbox('D_wall_e', (4.5, 2.5, 70), (1, 6, 10), wall)
    gbox('D_wall_n', (0, 2.5, 75.5), (10, 6, 1), wall)

    # ---- 目印
    marker('start', 0, 0, -6, 0)
    marker('npc_guide', 2.5, 0, -3, 200)
    marker('beacon_a', -3, 0, 7, 0)
    marker('cp_a', 0, 0, 0, 0)
    marker('cp_b', 0, 0, 42, 0)
    marker('trig_corridor', 0, 0, 14, 0)
    marker('trig_arena', 0, 0, 44, 0)
    marker('enemy_1', -6, 0, 54, 180)
    marker('enemy_2', 6, 0, 54, 180)
    marker('enemy_3', 0, 0, 60, 180)
    marker('cracked_wall', 0, 0, 64.5, 0)
    marker('chest_1', 0, 0, 72, 180)


if __name__ == '__main__':
    build()
    out = os.path.join(C.REPO, 'public', 'assets', 'levels', 'mvp_greybox.glb')
    C.export_glb(out, animations=False)
    print('wrote', out)
