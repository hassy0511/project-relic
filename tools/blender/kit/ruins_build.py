"""遺構 B2〜B4 のキットの部品（GLB）と、どの階層でも使う汚れのしみの部品を作る（B1 は build.py）。何度流しても同じものができる。

  .venv-blender/bin/python tools/blender/kit/ruins_build.py                    全部（ruins_b2・ruins_b3・ruins_b4・ruins_stain）
  .venv-blender/bin/python tools/blender/kit/ruins_build.py --kits=ruins_b2    キットを選んで
  .venv-blender/bin/python tools/blender/kit/ruins_build.py --only b2_wall,b2_pipe   部品を選んで（一覧の GLB は作らない）

できるもの：godot/assets/kit/ruins/<部品>.glb、確認ページ用の一覧 tools/model_viewer/kit_ruins_b2.glb など（build/kit/parts_ruins.json に三角形の数）。
部品の一覧の画像（Godot で、キットの材質を付けて描く）：
  tools/godot.sh import && tools/godot.sh shot --resolution 1800x1100 --script $PWD/tools/blender/kit/godot_kit_review.gd -- build/kit/review_ruins_b2.png ruins_b2
置き方（原点・向き）は各キットのファイル（ruins_b2.py・ruins_b3.py・ruins_b4.py・ruins_common.py）の冒頭と、docs/design/43_遺構の見た目.md。
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build  # noqa: E402
import ruins_b2  # noqa: E402
import ruins_b3  # noqa: E402
import ruins_b4  # noqa: E402
import ruins_common  # noqa: E402

KITS = {
    'ruins_b2': ('ruins', ruins_b2.PARTS),
    'ruins_b3': ('ruins', ruins_b3.PARTS),
    'ruins_b4': ('ruins', ruins_b4.PARTS),
    'ruins_stain': ('ruins', ruins_common.PARTS),
}


def main() -> int:
    only = kits = None
    for a in sys.argv[1:]:
        if a.startswith('--only='):
            only = set(a.split('=', 1)[1].split(','))
        elif a == '--only':
            only = set(sys.argv[sys.argv.index(a) + 1].split(','))
        elif a.startswith('--kits='):
            kits = set(a.split('=', 1)[1].split(','))
    t0 = time.time()
    rep_path = os.path.join(build.WORK, 'parts_ruins.json')
    report = json.load(open(rep_path, encoding='utf-8')) if os.path.exists(rep_path) else {}
    for kit, (folder, makers) in KITS.items():
        if kits and kit not in kits:
            continue
        parts = [m() for m in makers]
        for p in parts:
            if only and p.name not in only:
                continue
            tris = build.export(p, os.path.join(build.OUT, folder, p.name + '.glb'))
            report[f'{folder}/{p.name}'] = {'triangles': tris, 'note': p.note}
            print(f'[kit] {folder}/{p.name}  {tris} 三角形', flush=True)
        if not only:
            build.gallery(kit, parts, os.path.join(build.REPO, 'tools', 'model_viewer', f'kit_{kit}.glb'))
    os.makedirs(build.WORK, exist_ok=True)
    with open(rep_path, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f'[kit] {len(report)} 部品（{time.time() - t0:.1f} 秒）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
