"""オルド背町の部品（キット）を作る入口。何度流しても同じ物ができる。

  .venv-blender/bin/python tools/blender/kit/town.py              全部の部品を作る
  .venv-blender/bin/python tools/blender/kit/town.py --only crate,barrel
  .venv-blender/bin/python tools/blender/kit/town.py --list
  .venv-blender/bin/python tools/blender/kit/town.py --review     部品を 1 枚ずつ Cycles で描いて並べる（build/kit_town/review.jpg）
  .venv-blender/bin/python tools/blender/kit/town.py --sky        遠景の空（bg_desert_* → godot/assets/kit/town/sky_*.jpg）も作る
  .venv-blender/bin/python tools/blender/kit/town.py --tex        表面の絵（tex_town_* → godot/assets/kit/tex/town_*.jpg）も作る
  絵は先に取り出しておく：git archive origin/art/w2-town art/concepts/W2_town | tar -x -C build/intake/w2town --strip-components=3

できるもの
  godot/assets/kit/town/<部品>.glb   部品ごとの GLB（材質は town_ivory など共通の名前、平らな 1 色、発光は town_glow）
  godot/assets/kit/town/parts.json   部品の一覧（三角形の数・大きさ・灯の芯の位置）
  build/kit_town/                    確認の画像

部品の中身は town_parts.py（キットと小物）と town_sets.py（広場・市場・段の正面などの組み合わせ）、
遠景は town_backdrop.py。絵は origin/art/w2-town（W2-05）、寸法は spec_town_3d.md。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(REPO, 'godot', 'assets', 'kit', 'town')
WORK = os.path.join(REPO, 'build', 'kit_town')


def catalog() -> dict:
    import town_backdrop as BD
    import town_parts as P
    import town_sets as S
    return {
        # 建物キット
        'wall_2': lambda: P.wall(2, 2), 'wall_4': lambda: P.wall(2, 4), 'wall_door': lambda: P.wall(2, 2, 'door'),
        'wall_window': lambda: P.wall(2, 2, 'window'), 'roof_flat': lambda: P.roof('flat'), 'roof_wood': lambda: P.roof('wood'),
        'roof_canvas': lambda: P.roof('canvas'), 'awning_hard': lambda: P.awning('hard'), 'awning_soft': lambda: P.awning('soft'),
        'stairs': P.stairs, 'railing': P.railing,
        # 地面キット
        'ledge': P.ledge, 'ladder': P.ladder, 'pipes': P.pipes, 'power_pole': P.power_pole, 'lamp_post': P.lamp_post, 'lamp_tall': P.lamp_tall,
        # 小物
        'crate': P.crate, 'barrel': P.barrel, 'clothesline': P.clothesline, 'planter': P.planter, 'stall_table': P.stall_table,
        'water_tower': P.water_tower, 'bench': P.bench, 'junk_pile': P.junk_pile, 'tool_rack': P.tool_rack, 'chest': P.chest,
        'tank': P.tank, 'pipe_bend': P.pipe_bend, 'canvas_roll': P.canvas_roll, 'sand_screen': P.sand_screen,
        'hand_lantern': P.hand_lantern, 'stool': P.stool,
        # 看板（文字はゲームが板に貼る）
        'sign_wall_2': lambda: P.sign_board(2.2, mount='wall'), 'sign_wall_3': lambda: P.sign_board(3.0, mount='wall'),
        'sign_post_2': lambda: P.sign_board(2.2, mount='post', post_len=1.75), 'sign_post_3': lambda: P.sign_board(3.0, mount='post', post_len=1.75),
        'sign_roof_2': lambda: P.sign_board(2.2, mount='post', post_len=1.65),
        # 組み合わせ（町の場所ごと）
        **S.SETS,
        # 遠景
        **BD.PARTS,
    }


def make_textures(size: int = 1024) -> None:
    """町の表面の絵（W2-05 tex_town_*.png、1 枚 = 2 m 四方）。納品の時点で上下左右の端がつながっているので、縮めるだけ"""
    from PIL import Image
    src = os.path.join(REPO, 'build', 'intake', 'w2town')
    out = os.path.join(REPO, 'godot', 'assets', 'kit', 'tex')
    os.makedirs(out, exist_ok=True)
    for n in ('shell', 'canvas', 'wood', 'rust'):
        im = Image.open(os.path.join(src, f'tex_town_{n}.png')).convert('RGB').resize((size, size), Image.LANCZOS)
        p = os.path.join(out, f'town_{n}.jpg')
        im.save(p, quality=88)
        print('[town] 表面', p, flush=True)
    # 床・壁用の落ち着いた版：継ぎ目と金具の濃さを半分にし、平均の色を白磁へ寄せる（広い面で同じ模様が強く繰り返さないように）
    import numpy as np
    a = np.asarray(Image.open(os.path.join(out, 'town_shell.jpg')), np.float32)
    soft = (a - a.mean((0, 1))) * 0.45 + np.array([236.0, 226.0, 206.0])    # 平均を白磁（#ECE2CE）へ
    Image.fromarray(np.clip(soft, 0, 255).astype(np.uint8)).save(os.path.join(out, 'town_shell_soft.jpg'), quality=88)
    print('[town] 表面', os.path.join(out, 'town_shell_soft.jpg'), flush=True)


def gallery(cat: dict) -> None:
    """確認ページ（tools/model_viewer）用：遠景・空・床の板・段の正面を除く部品を格子に並べた 1 つの GLB"""
    import bpy

    import town_geo as geo
    skip = {'ordo_far', 'deck_slab', 'plaza_ring'}
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    names = [n for n in cat if n not in skip]
    cols, step = 8, 4.5
    x = 0
    row_z, row_h, k = 0.0, 0.0, 0
    for n in names:
        part = cat[n]()
        part.name = n
        lo, hi = part.bounds()
        w = float(hi[0] - lo[0])
        if k % cols == 0 and k:
            row_z += row_h + 2.0
            row_h, x = 0.0, 0.0
        ob = geo.to_object(part)
        ob.location = (x - float(lo[0]), row_z - float(lo[2]) * 0, 0)
        x += max(w, 2.0) + 1.5
        row_h = max(row_h, float(hi[2] - lo[2]))
        k += 1
    bpy.ops.object.select_all(action='SELECT')
    path = os.path.join(REPO, 'tools', 'model_viewer', 'kit_town.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, use_selection=True, export_animations=False,
                              export_apply=True, export_vertex_color='ACTIVE', export_active_vertex_color_when_no_material=True)
    print('[town] 確認ページ用', path, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--sky', action='store_true')
    ap.add_argument('--gallery', action='store_true', help='確認ページ用に全部の部品を格子に並べた tools/model_viewer/kit_town.glb')
    ap.add_argument('--tex', action='store_true', help='tex_town_*.png → godot/assets/kit/tex/town_*.jpg（1024）')
    a = ap.parse_args()
    cat = catalog()
    if a.list:
        print('\n'.join(cat))
        return
    import town_geo as geo
    names = [n for n in a.only.split(',') if n] or list(cat)
    t0 = time.time()
    index_path = os.path.join(OUT, 'parts.json')
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    for n in names:
        part = cat[n]()
        part.name = n
        info = geo.write_glb(part, os.path.join(OUT, f'{n}.glb'))
        index[n] = info
        print(f'[town] {n}: {info}', flush=True)
    index = {k: index[k] for k in cat if k in index}
    os.makedirs(OUT, exist_ok=True)
    with open(index_path, 'w') as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    if a.sky:
        import town_backdrop as BD
        BD.make_sky(OUT)
    if a.tex:
        make_textures()
    if a.gallery:
        gallery(cat)
    if a.review:
        import town_review
        town_review.render(cat, names, WORK)
    print(f'[town] {len(names)} 部品、{time.time() - t0:.1f} 秒', flush=True)


if __name__ == '__main__':
    main()
