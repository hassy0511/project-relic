"""部屋のキットの部品（GLB）を作る。何度流しても同じものができる。

  .venv-blender/bin/python tools/blender/kit/build.py            全部の部品を作る
  .venv-blender/bin/python tools/blender/kit/build.py --only b1_wall,b1_pillar

できるもの：godot/assets/kit/<キット>/<部品>.glb（例：ruins/b1_wall.glb）。表面の絵は textures.py（godot/assets/kit/tex/）。
部品の一覧の画像（Godot で、キットの材質を付けて描く）：
  tools/godot.sh import && tools/godot.sh shot --resolution 1800x1100 --script $PWD/tools/blender/kit/godot_kit_review.gd -- build/kit/review_ruins_b1.png ruins_b1
置き方（原点・向き）は各キットのファイル（ruins_b1.py）の冒頭と、docs/design/42_コンテンツの書き方.md 14 章。
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(REPO, 'godot', 'assets', 'kit')
WORK = os.path.join(REPO, 'build', 'kit')

import geo  # noqa: E402
import ruins_b1  # noqa: E402

# キット → (出力のフォルダ, 部品の作り方の一覧)
KITS = {
    'ruins_b1': ('ruins', ruins_b1.PARTS),
}


def export(part: geo.Part, path: str) -> int:
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob = geo.to_blender(part)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, use_selection=True,
                              export_animations=False, export_apply=True)
    return geo.tri_count(part)


def main() -> int:
    only = None
    for a in sys.argv[1:]:
        if a.startswith('--only'):
            only = set(sys.argv[sys.argv.index(a) + 1].split(',')) if a == '--only' else set(a.split('=', 1)[1].split(','))
    t0 = time.time()
    report = {}
    for kit, (folder, makers) in KITS.items():
        parts = [m() for m in makers]
        for p in parts:
            if only and p.name not in only:
                continue
            tris = export(p, os.path.join(OUT, folder, p.name + '.glb'))
            report[f'{folder}/{p.name}'] = {'triangles': tris, 'note': p.note}
            print(f'[kit] {folder}/{p.name}  {tris} 三角形', flush=True)
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, 'parts.json'), 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f'[kit] {len(report)} 部品（{time.time() - t0:.1f} 秒）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
