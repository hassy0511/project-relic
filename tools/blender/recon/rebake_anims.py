"""今ある GLB（骨・形・塗り・持ち物・目印はそのまま）に、humanoid_anims.py の動作だけを焼き直す。

  .venv-blender/bin/python tools/blender/recon/rebake_anims.py [--only combo1,combo2,combo3]
      [--model godot/assets/models/haru_r.glb] [--out build/rebake/haru_r.glb] [--base <GLB のパス か git の版>]

動作を直すたびに絵からの完全な再構築（build_char.py、約 40 分、build/recon が要る）をしなくてよいための入口。
動作の定義は従来どおり tools/blender/models/humanoid_anims.py（完全な再構築でも同じ動作になる）。

元の GLB は必ず「形が BASE_REV（最後の完全な再構築）と同じ物」から取る。読み込み→書き出しを繰り返すと、glTF の
書き出しが法線・UV の境で頂点を分けるので、頂点が少しずつ増える（46634 → 47529 → 47863）。既定は splice_anims.py と
同じく、形が BASE_REV と同じ物のうちいちばん新しい物（作業中の --model → git HEAD。ほかの動作が今の物のまま残る。
BASE_REV の版をそのまま元にすると、そのあとに直した動作が古い物に戻る）。骨・形・塗りを作り直したら BASE_REV をその版に直す。
--only：その動作だけ新しい定義にする。焼き直さなかった動作は、Blender の読み込み・書き出しで長さが半分になって
使えない（idle 2.0 → 1.0 秒、2026-11-05 に確かめた）。形・節も少しずつ変わる。
なので書き出しは既定で build/rebake/ に置き、ゲームの GLB は上書きしない。続けて splice_anims.py で直した動作だけを
ゲームの GLB に差し込む（splice_anims.py の --from の既定は build/rebake/<モデルの名前>）。

ほかの人物（recon で作った NPC）：動作の組と足の裏の接地点を chars/<id>.json の rig_args と同じにする。元の GLB は
作業中の --model（無ければ git HEAD）。BASE_REV はハルの版なので、差し込むときは --base に同じファイルを渡す：
  .venv-blender/bin/python tools/blender/recon/rebake_anims.py --model godot/assets/models/junker.glb --clips child \
      --foot-contacts=-0.22,0.13,-0.09
  python3 tools/blender/recon/splice_anims.py --model godot/assets/models/junker.glb --out godot/assets/models/junker.glb \
      --base godot/assets/models/junker.glb --clips walk,cower,run,idle
（杖の老人（--clips elder）は骨付けの段の手の測りが要るので、ここでは焼けない）
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
from recon.splice_anims import pick_base  # noqa: E402

REPO = C.REPO
DEFAULT_MODEL = 'godot/assets/models/haru_r.glb'
# 骨・形・塗りを最後に作り直した版（2026-11-02 髪を房の部品で作り直し、耳の近くのかぶりを縮めない版。
# 今の haru_r.glb と形・材質・画像・節・スキンが同じ。動作は違う：2026-11-05 に combo1〜3 を入れ替えた）。
# 前は 2026-10-20 揺れの骨（髪 7・ポーチ 2）を足した f2516e2、その前は 2026-10-07 外装フレームを群に分けた c9faf94。
# 形の手本に使う（元の GLB の形がこれと同じか確かめる）。動作の元は今の haru_r.glb（splice_anims.pick_base）
BASE_REV = '06ea887'


def base_glb(base: str | None, model_rel: str) -> str:
    """--base がファイルならそれ、git の版ならその GLB、無ければ形が BASE_REV と同じ物のうちいちばん新しい物を
    一時ファイルに出す（ハルの外の人物は BASE_REV を持たないので、作業中のファイル → git HEAD）"""
    if base and os.path.exists(base):
        return os.path.abspath(base)
    if not base and model_rel != DEFAULT_MODEL:
        path = os.path.join(REPO, model_rel)
        if os.path.exists(path):
            return path
        base = 'HEAD'
    if base:
        data = subprocess.run(['git', 'show', f'{base}:{model_rel}'], cwd=REPO, capture_output=True, check=True).stdout
        label = f'git {base}:{model_rel}'
    else:
        data, label = pick_base(model_rel)
    fd, path = tempfile.mkstemp(suffix='.glb', prefix='rebake_base_')
    with os.fdopen(fd, 'wb') as f:
        f.write(data)
    print(f'元の GLB：{label}')
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
    ap.add_argument('--out', default=None, help='書き出し先（既定は build/rebake/<モデルの名前>）')
    ap.add_argument('--base', default=None,
                    help='元の GLB（ファイル か git の版）。既定は形が BASE_REV と同じ物のうちいちばん新しい物（作業中 → HEAD）')
    ap.add_argument('--only', default=None, help='新しくする動作の名前（, 区切り）。省略時は全部')
    ap.add_argument('--model', default=DEFAULT_MODEL, help='元を探すときの、リポジトリの中のパス')
    ap.add_argument('--clips', dest='clip_set', default='standard', choices=('standard', 'child'),
                    help='動作の組（ai_character.py --clips と同じ。standard = humanoid_anims、child = child_anims）')
    ap.add_argument('--foot-contacts', default=None,
                    help='足の裏の接地点「つま先 y,かかと y,下 z」（ai_character.py --foot-contacts と同じ。省略時はハルの値）')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    args.model = os.path.relpath(os.path.abspath(os.path.join(REPO, args.model)), REPO)
    args.out = args.out or os.path.join(REPO, 'build', 'rebake', os.path.basename(args.model))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    src = base_glb(args.base, args.model)

    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=src)
    summary('元')
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    if args.clip_set == 'child':
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
    C.export_glb(out)
    print(f'書き出し：{out}（{os.path.getsize(out) / 1e6:.2f} MB）')
    nb = args.base or (args.model if os.path.exists(os.path.join(REPO, args.model)) else 'HEAD')
    more = '' if args.model == DEFAULT_MODEL else f' --model {args.model} --out {args.model} --base {nb}'
    print(f'次：python3 tools/blender/recon/splice_anims.py --clips {",".join(c.name for c in clips)} --from {args.out}{more}'
          '（この GLB はそのまま使わない）')

    # 読み直して、同じ物が残っているか
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=out)
    summary('結果')
    if src.startswith(tempfile.gettempdir()):
        os.remove(src)


if __name__ == '__main__':
    main()
