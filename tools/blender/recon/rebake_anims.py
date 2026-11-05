"""今ある GLB（骨・形・塗り・持ち物・目印はそのまま）に、humanoid_anims.py の動作だけを焼き直す。

  .venv-blender/bin/python tools/blender/recon/rebake_anims.py [--out godot/assets/models/haru_r.glb]
      [--base <GLB のパス か git の版>] [--only combo1,combo2,combo3]
  ほかの人物（recon で作った NPC）：動作の組と足の裏の接地点を chars/<id>.json の rig_args と同じにする
  .venv-blender/bin/python tools/blender/recon/rebake_anims.py --out godot/assets/models/junker.glb --clips child \
      --foot-contacts=-0.17,0.13,-0.09
  （ハルの外は --base を省くと HEAD の GLB が元。形はバイトのまま残すので、何度焼き直しても頂点は増えない。
   杖の老人（--clips elder）は骨付けの段の手の測りが要るので、ここでは焼けない）

動作を直すたびに絵からの完全な再構築（build_char.py、約 40 分、build/recon が要る）をしなくてよいための入口。
動作の定義は従来どおり tools/blender/models/humanoid_anims.py（完全な再構築でも同じ動作になる）。

元の GLB は「骨・形・塗りを最後に作り直した版」から取る（--base）。既定は BASE_REV のコミットの GLB（git show）。
骨・形・塗りを作り直したら BASE_REV をその版に直す（古い版から焼くと、その後の作り直し（髪など）が消える）。
Blender の読み込み→書き出しを 1 回通すと、法線・UV の境で頂点が分かれて頂点が増え、法線も少し変わる
（haru_r：60,026 → 60,969）。そこで書き出した GLB からは動作だけを取り、元の GLB の形（メッシュ・骨・塗り・目印）は
バイトのまま残す（glb_splice_anims.py）。形が同じかは、出力のあとに頂点の数・材質・骨の名前を並べて見る。
--only：その動作だけ新しい定義にし、ほかは元の GLB の動作をバイトのまま残す（既定は全部焼き直す）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402
from models import humanoid_anims as A  # noqa: E402
from recon.glb_splice_anims import splice  # noqa: E402

REPO = C.REPO
DEFAULT_OUT = 'godot/assets/models/haru_r.glb'
# 骨・形・塗りを最後に作り直した版（2026-11-02 髪の葉の房 37・耳を避けた髪の土台・輪ごとの揺れの重み（H1）を作り直した版。
# 前は 2026-10-20 揺れの骨を足した f2516e2、その前は 2026-10-07 外装フレームを群に分けた c9faf94）。
# この版の GLB を元にして動作だけ替える（前の版から焼き直すと、その後の作り直しが消える）
BASE_REV = '06ea887'


def base_glb(base: str | None, out_rel: str) -> str:
    """--base がファイルならそれ、無ければ git の版（ハルは BASE_REV、ほかは HEAD）の GLB を一時ファイルに出す"""
    if base and os.path.exists(base):
        return os.path.abspath(base)
    rev = base or (BASE_REV if out_rel == DEFAULT_OUT else 'HEAD')
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
    ap.add_argument('--clips', default='standard', choices=('standard', 'child'),
                    help='動作の組（ai_character.py --clips と同じ。standard = humanoid_anims、child = child_anims）')
    ap.add_argument('--foot-contacts', default=None,
                    help='足の裏の接地点「つま先 y,かかと y,下 z」（ai_character.py --foot-contacts と同じ。省略時はハルの値）')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    out_rel = os.path.relpath(os.path.abspath(args.out), REPO)
    src = base_glb(args.base, out_rel)

    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=src)
    summary('元')
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    if args.clips == 'child':
        from models import child_anims
        clips = child_anims.all_clips()
    else:
        clips = A.all_clips()
    contacts = None
    if args.foot_contacts:
        ty, hy, dz = (float(v) for v in args.foot_contacts.split(','))
        contacts = ((0.0, ty, dz), (0.0, hy, dz))
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
    H.bake_clips(arm, clips, contacts)
    bpy.ops.object.select_all(action='SELECT')
    out = os.path.abspath(args.out)
    fd, baked = tempfile.mkstemp(suffix='.glb', prefix='rebake_anims_')
    os.close(fd)
    C.export_glb(baked)
    # 動作だけを元の GLB に入れる（形はバイトのまま）
    fd, spliced = tempfile.mkstemp(suffix='.glb', prefix='rebake_out_')
    os.close(fd)
    r = splice(src, baked, spliced, only)
    shutil.move(spliced, out)
    os.remove(baked)
    print(f'書き出し：{out}（{os.path.getsize(out) / 1e6:.2f} MB。差し替えた動作 {r["replaced"]}、元のまま {r["kept"]}）')

    # 読み直して、同じ物が残っているか
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=out)
    summary('結果')
    if src.startswith(tempfile.gettempdir()):
        os.remove(src)


if __name__ == '__main__':
    main()
