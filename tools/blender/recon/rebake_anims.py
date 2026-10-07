"""今ある GLB（骨・形・塗り・持ち物・目印はそのまま）に、humanoid_anims.py の動作だけを焼き直す。

  .venv-blender/bin/python tools/blender/recon/rebake_anims.py [--out godot/assets/models/haru_r.glb]
      [--base <GLB のパス か git の版>] [--only combo1,combo2,combo3]

動作を直すたびに絵からの完全な再構築（build_char.py、約 40 分、build/recon が要る）をしなくてよいための入口。
動作の定義は従来どおり tools/blender/models/humanoid_anims.py（完全な再構築でも同じ動作になる）。

元の GLB は必ず「動作を直す前の版」から取る（--base）。読み込み→書き出しを繰り返すと、glTF の書き出しが
法線・UV の境で頂点を分けるので、頂点が少しずつ増える（46634 → 47529 → 47863）。既定は BASE_REV のコミットの
GLB（git show）。骨・形・塗りを作り直したら BASE_REV をその版に直す。
--only：その動作だけ新しい定義にし、ほかは元の GLB の動作をそのまま残す（確認用。既定は全部焼き直す）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402
from models import humanoid_anims as A  # noqa: E402

REPO = C.REPO
DEFAULT_OUT = 'godot/assets/models/haru_r.glb'
# 骨・形・塗りを最後に作り直した版（ハル 8 回目のまま）。この版の GLB を元にして動作だけ替える
BASE_REV = 'f9dfc00'


def base_glb(base: str | None, out_rel: str) -> str:
    """--base がファイルならそれ、無ければ git の版 BASE_REV の GLB を一時ファイルに出す"""
    if base and os.path.exists(base):
        return os.path.abspath(base)
    rev = base or BASE_REV
    fd, path = tempfile.mkstemp(suffix='.glb', prefix='rebake_base_')
    with os.fdopen(fd, 'wb') as f:
        subprocess.run(['git', 'show', f'{rev}:{out_rel}'], cwd=REPO, stdout=f, check=True)
    print(f'元の GLB：git {rev}:{out_rel}')
    return path


def summary(tag: str) -> None:
    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    empties = sorted(o.name for o in bpy.data.objects if o.type == 'EMPTY')
    print(f'[{tag}] 骨 {len(arm.data.bones) if arm else 0} 本、動作 {sorted(a.name for a in bpy.data.actions)}')
    print(f'[{tag}] 材質 {sorted(m.name for m in bpy.data.materials)}、画像 {len(bpy.data.images)} 枚、目印 {empties}')
    for o in meshes:
        print(f'[{tag}]   {o.name}: 頂点 {len(o.data.vertices)}、重みの群 {len(o.vertex_groups)}、'
              f'親 {o.parent.name if o.parent else None}{"/" + o.parent_bone if o.parent_bone else ""}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--base', default=None, help='元の GLB（ファイル か git の版。既定は BASE_REV の --out）')
    ap.add_argument('--only', default=None, help='新しくする動作の名前（, 区切り）。省略時は全部')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    out_rel = os.path.relpath(os.path.abspath(args.out), REPO)
    src = base_glb(args.base, out_rel)

    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=src)
    summary('元')
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    clips = A.all_clips()
    only = set(args.only.split(',')) if args.only else None
    if only:
        clips = [c for c in clips if c.name in only]
        missing = only - {c.name for c in clips}
        if missing:
            sys.exit(f'無い動作：{sorted(missing)}')
    # 置き換える動作を消す（NLA の帯とアクション）。glTF の読み込みは動作ごとに 1 本の帯にしてある
    names = {c.name for c in clips}
    ad = arm.animation_data
    if ad:
        ad.action = None
        for t in list(ad.nla_tracks):
            if t.name in names or any(s.action and s.action.name in names for s in t.strips):
                ad.nla_tracks.remove(t)
    for a in list(bpy.data.actions):
        if a.name in names:
            bpy.data.actions.remove(a)
    H.bake_clips(arm, clips)
    bpy.ops.object.select_all(action='SELECT')
    out = os.path.abspath(args.out)
    C.export_glb(out)
    print(f'書き出し：{out}（{os.path.getsize(out) / 1e6:.2f} MB）')

    # 読み直して、同じ物が残っているか
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=out)
    summary('結果')
    if src.startswith(tempfile.gettempdir()):
        os.remove(src)


if __name__ == '__main__':
    main()
