"""絵から起こしたキャラクター（ハル haru_r、ヤーナ yana）を、元の絵からゲームの GLB まで一度に作る。

  .venv-blender/bin/python tools/blender/recon/build_char.py [--char yana]   古い段だけ作り直す（既定 --char haru）
      --char 名前       キャラクター（tools/blender/recon/chars/<名前>.json。ハル haru、ヤーナ yana）
      --list            段の一覧と、それぞれが最新か（作り直しが要るか）を表示するだけ
      --from 名前       その段から後ろだけを見る（前の段は動かさず、出力があることだけ確かめる）
      --only 名前       その段だけ
      --force           見る段を、最新でも作り直す
      --standin         テクスチャの段の代わりに代役（standin.py：絵をまっすぐ投影しただけの色）を使う
      --review          最後に確認の画像（review.py の Cycles の画像。ハルは ingame_shots.py の Godot の画像も）も作る
  npm run haru:recon・npm run yana:recon でも動く（引数は -- のあとに：npm run yana:recon -- --from rig）
  build_haru_r.py は --char haru のこれ（以前からの入口）。

■ キャラクターの設定（char.py、chars/<id>.json）
  作業のフォルダ（ハル build/recon、ヤーナ build/yana）、絵のファイル名、視点の一覧、顔の絵・表情の順、
  出力の GLB、骨付けの持ち物の引数（rig_args）、動かさない段（stages_skip）、各スクリプトの定数の上書き（params）。
  各段のスクリプトは環境変数 RECON_CHAR で同じ設定を読む（このスクリプトが渡す）。

■ 段（上から順に動かす）
  各段は (名前, スクリプト, 引数, 出力, 入力)。段を動かし終えると、入力・スクリプト・補助のスクリプト・引数・
  キャラクターの設定の中身の指紋（sha1）を <作業のフォルダ>/stamps/<段>.json に残す。出力がすべてあり、今の指紋が
  残した指紋と同じなら、その段は飛ばす（中身で比べるので、git の取り出しなどで更新時刻だけ変わっても作り直さない）。
  calib.json は後の段が確認の値（silhouette_iou_final_mesh）を書き足すので、その値は指紋から除く。
  指紋がまだ無い段は、更新時刻で比べる（出力が入力より新しければ最新とみなす）。
      --adopt 名前|all  今ある出力を「今の入力で作ったもの」として指紋だけ残す（動かさない）。
                        手で作り直した出力を受け入れるときに使う
  まだ無い段を足すときは Stage(..., todo=True) で印を付けておくと、重い段を動かす前に止まる。

■ 座標・材質の約束（段の間の受け渡し。<id> はキャラクターの名前）
  <id>_textured_apose.glb：A ポーズ、身長 1.55m（再構築の座標）、正面 -Y（Blender）、靴底 z=0、物体 1 つ（殻は複数でもよい）、
    材質 '<id>_body'（下地の色＋発光のテクスチャ）と '<id>_face'（face_atlas.png、UV は区画 0：
    Blender の u∈[0,0.5]、v∈[0.5,1]）
  spark_gun.glb（ハルだけ）：原点 = 握りの中心、銃身 +X、上 +Z、材質 'spark_gun'、空の目印 'muzzle'
  haru_r.glb：標準の 20 本の骨・14 動作・銃（右手の拳で握る。拳はシェイプキー 'fist'、基準は開いた手）・光刃 'LightBlade'（左の籠手のレール）・目印 'muzzle'、
    'blade_socket'。材質 'haru_body'、'haru_face'、'spark_gun'、'haru_blade'
  yana.glb：標準の 20 本の骨・14 動作（持ち物なし）。材質 'yana_body'、'yana_face'。骨の物体を 172/155 倍に拡大（身長 1.72m）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
PY = os.path.join(REPO, '.venv-blender', 'bin', 'python')
RECON_PY = 'tools/blender/recon'
CHAR_ID = 'haru'     # main() で --char から決める
CFG: dict = {}
R = PREP = OUT_GLB = ID = OUT_NAME = ''
SRC_FULL: list[str] = []
SRC_FACE: list[str] = []
SRC_GUN: list[str] = []
MASKS: list[str] = []
CHAR_FILES: list[str] = []


def setup(char_id: str) -> None:
    """キャラクターの設定を読み、段の一覧に使う値を決める"""
    global CHAR_ID, CFG, R, PREP, OUT_GLB, ID, OUT_NAME, SRC_FULL, SRC_FACE, SRC_GUN, MASKS, CHAR_FILES
    CHAR_ID = char_id
    with open(os.path.join(REPO, RECON_PY, 'chars', f'{char_id}.json'), encoding='utf-8') as fp:
        CFG = json.load(fp)
    ID = CFG['id']
    R = CFG['work']                 # 作業のフォルダ（git の外）
    PREP = f'{R}/prep'
    OUT_GLB = CFG['out_glb']
    OUT_NAME = os.path.splitext(os.path.basename(OUT_GLB))[0]
    views = CFG['views']
    SRC_FULL = list(dict.fromkeys(f'{R}/src/{v["file"]}' for v in views.values()))
    SRC_FACE = [f'{R}/src/{CFG["face"]["file"]}', f'{R}/src/{CFG["face"]["expressions_file"]}']
    SRC_GUN = [f'{R}/src/{f}' for f in CFG.get('gun', {}).get('sources', [])]
    MASKS = [f'{R}/mask_{v}.png' for v in views]
    # 設定と読み込み口は全段の補助（変われば作り直す。ハルの設定を変えるとハルの全段）
    CHAR_FILES = [f'{RECON_PY}/char.py', f'{RECON_PY}/chars/{char_id}.json']


@dataclass
class Stage:
    name: str
    script: str | None             # リポジトリからの相対パス（None は、まだ無い段）
    args: list[str]
    outputs: list[str]
    inputs: list[str]
    deps: list[str] = field(default_factory=list)   # スクリプトが読み込む補助のスクリプト（変われば作り直す）
    todo: bool = False              # まだ無い段（統合する人が埋める）
    note: str = ''


def stages(standin: bool) -> list[Stage]:
    textured = f'{PREP}/standin_textured.glb' if standin else f'{R}/{ID}_textured_apose.glb'
    mesh = f'{R}/{ID}_mesh'
    joints = f'{PREP}/{ID}_joints.json'
    stats = f'{R}/{OUT_NAME}.stats.json'
    rig_args = [a.replace('{work}', R) for a in CFG.get('rig_args', [])]
    rig_inputs = [textured, joints] + [a for a in rig_args if a.endswith('.glb')]
    if abs(CFG.get('height_m', 1.55) - CFG.get('recon_height_m', 1.55)) > 1e-6:
        rig_args += ['--final-height', str(CFG['height_m'])]
    if ID != 'haru':
        rig_args += ['--name', ID.capitalize()]
    lst = [
        Stage('views', f'{RECON_PY}/views.py', [],
              outputs=[f'{R}/calib.json'] + MASKS, inputs=SRC_FULL,
              note=f'元の絵の取り出し（無ければ git の {CFG["art"]["ref"]} から）・外形のマスク・最初の較正'),
        Stage('calib', f'{RECON_PY}/carve.py', ['--stage', 'calib'],
              outputs=[f'{R}/calib.json'], inputs=MASKS,
              deps=[f'{RECON_PY}/views.py'],
              note='較正の追い込み（斜めの絵の方位角など）。calib.json を書き直す'),
        Stage('hull', f'{RECON_PY}/carve.py', ['--stage', 'hull'],
              outputs=[f'{R}/hull.npz'], inputs=[f'{R}/calib.json'] + MASKS,
              deps=[f'{RECON_PY}/fair.py', f'{RECON_PY}/hair.py', f'{RECON_PY}/views.py'],
              note='なめらかな形の場：体のレンズ＋頭と髪の房（約 3 分）'),
        Stage('mesh', f'{RECON_PY}/carve.py', ['--stage', 'mesh'],
              outputs=[f'{mesh}.glb', f'{mesh}.blend', f'{mesh}.npz'],
              inputs=[f'{R}/hull.npz', f'{R}/calib.json'],
              deps=[f'{RECON_PY}/fair.py', f'{RECON_PY}/snap.py', f'{RECON_PY}/uvparts.py', f'{RECON_PY}/check.py',
                    f'{RECON_PY}/surfcheck.py', f'{RECON_PY}/uvcheck.py', f'{RECON_PY}/views.py'],
              note='面・外形への留め・間引き・部位ごとの UV・確認画像（約 7 分）'),
        Stage('face', f'{RECON_PY}/face.py', [],
              outputs=[f'{R}/face_atlas.png', f'{R}/face_atlas.json'],
              inputs=SRC_FACE + [f'{R}/src/{CFG["views"]["front"]["file"]}', f'{R}/calib.json'],
              note='表情の 2×2 のテクスチャ（約 3 分）'),
        Stage('gun', f'{RECON_PY}/gun.py', [],
              outputs=[f'{R}/spark_gun.glb'], inputs=SRC_GUN,
              note='銃（スパーク）'),
        Stage('texture', f'{RECON_PY}/texture.py' if not standin else None, ['--mesh', f'{mesh}.glb'],
              outputs=[f'{R}/{ID}_textured_apose.glb', f'{R}/tex/{ID}_body_base.png', f'{R}/tex/{ID}_body_emit.png'],
              inputs=[f'{mesh}.glb', f'{R}/calib.json', f'{R}/face_atlas.png', f'{R}/face_atlas.json',
                      f'{R}/face_align.json'] + SRC_FULL,
              deps=[f'{RECON_PY}/views.py', f'{RECON_PY}/hair.py', f'{RECON_PY}/uvparts.py', f'{RECON_PY}/flat.py',
                    f'{RECON_PY}/flat_views.py'],
              note='下地の色・発光を 2048 角に焼き、顔の材質と UV を付ける（A ポーズの GLB、確認画像込みで約 5 分）'),
        Stage('joints', f'{RECON_PY}/joints.py', ['--mesh', textured, '--out', joints],
              outputs=[joints], inputs=[textured],
              note='関節の位置（左右・高さは絵で読んだ表、前後はメッシュから）'),
        Stage('rig', 'tools/blender/models/ai_character.py',
              ['--input', textured, '--out', OUT_GLB, '--keep-frame', '--joints', joints] + rig_args
              + ['--stats', stats],
              outputs=[OUT_GLB, stats],
              inputs=rig_inputs,
              deps=['tools/blender/lib/humanoid.py', 'tools/blender/lib/mesh.py', 'tools/blender/lib/common.py',
                    'tools/blender/models/humanoid_anims.py', 'tools/blender/models/haru_a.py'],
              note='骨・重み・腕を下ろした基準の姿勢・14 動作・持ち物・目印を付けて、ゲームの GLB に'),
    ]
    if standin:
        # 代役：テクスチャの段の代わり（形 <id>_mesh.glb に、絵をまっすぐ投影しただけの色）
        lst[lst.index(next(s for s in lst if s.name == 'texture'))] = Stage(
            'texture', f'{RECON_PY}/standin.py', ['--mesh', f'{mesh}.glb', '--out', textured],
            outputs=[textured], inputs=[f'{mesh}.glb', f'{R}/calib.json', f'{R}/face_atlas.png',
                                        f'{R}/face_atlas.json'] + SRC_FULL[:2],
            note='代役（--standin）：正面・背面の絵をまっすぐ投影しただけの色')
    skip = set(CFG.get('stages_skip', []))
    lst = [s for s in lst if s.name not in skip]
    for s in lst:
        s.deps = s.deps + CHAR_FILES
    return lst


def review_stages() -> list[Stage]:
    stats = f'{R}/{OUT_NAME}.stats.json'
    lst = [
        Stage('review', f'{RECON_PY}/review.py', ['--glb', OUT_GLB, '--stats', stats],
              outputs=[f'{R}/review/compare_views.png', f'{R}/review/face.png', f'{R}/review/poses.png',
                       f'{R}/review/joints.png'],
              inputs=[OUT_GLB, stats, f'{R}/calib.json', f'{R}/face_atlas.png'] + SRC_FULL,
              deps=[f'{RECON_PY}/views.py'] + CHAR_FILES,
              note=f'確認の画像（Cycles、{R}/review/、約 8 分）'),
    ]
    if ID == 'haru':
        lst.append(Stage('ingame', f'{RECON_PY}/ingame_shots.py', [],
                         outputs=[f'{R}/review/ingame_showcase.png', f'{R}/review/ingame_02_run.png'],
                         inputs=[OUT_GLB, 'godot/scripts/view/player_view.gd', 'godot/scripts/main.gd'],
                         deps=[f'{RECON_PY}/godot_showcase.gd'],
                         note='Godot の中の画像（見本の撮影と、全身・表情・動作の一覧。約 6 分）'))
    return lst


def mtime(p: str) -> float | None:
    full = os.path.join(REPO, p)
    return os.path.getmtime(full) if os.path.exists(full) else None


# 後の段が書き足す確認の値（入力の指紋から除く）
REPORT_KEYS = {'calib.json': ('silhouette_iou_final_mesh',)}


def file_digest(p: str) -> str:
    full = os.path.join(REPO, p)
    if not os.path.exists(full):
        return 'missing'
    base = os.path.basename(p)
    if base in REPORT_KEYS:
        with open(full, encoding='utf-8') as fp:
            d = json.load(fp)
        for k in REPORT_KEYS[base]:
            d.pop(k, None)
        return hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()
    h = hashlib.sha1()
    with open(full, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(s: Stage) -> dict:
    """段の入力・スクリプト・補助・引数の指紋"""
    files = sorted(set(s.inputs + [s.script] + s.deps))
    return {'args': s.args, 'files': {p: file_digest(p) for p in files}}


def stamp_path(s: Stage) -> str:
    return os.path.join(REPO, R, 'stamps', f'{s.name}.json')


def write_stamp(s: Stage) -> None:
    os.makedirs(os.path.join(REPO, R, 'stamps'), exist_ok=True)
    with open(stamp_path(s), 'w', encoding='utf-8') as fp:
        json.dump(fingerprint(s), fp, indent=1, ensure_ascii=False)


def status(s: Stage) -> str:
    """'ok'（最新）、'stale'（作り直しが要る）、'todo'（まだ無い段）"""
    if s.todo or s.script is None or not os.path.exists(os.path.join(REPO, s.script)):
        return 'todo'
    outs = [mtime(p) for p in s.outputs]
    if any(t is None for t in outs):
        return 'stale'
    if os.path.exists(stamp_path(s)):
        with open(stamp_path(s), encoding='utf-8') as fp:
            old = json.load(fp)
        return 'ok' if old == fingerprint(s) else 'stale'
    # 指紋がまだ無い：更新時刻で比べる
    srcs = [mtime(p) for p in s.inputs + [s.script] + s.deps]
    newest = max((t for t in srcs if t is not None), default=0.0)
    return 'ok' if min(outs) >= newest else 'stale'


def run(s: Stage) -> None:
    cmd = [PY, os.path.join(REPO, s.script)] + s.args
    print(f'\n=== {s.name}: {" ".join(os.path.relpath(c, REPO) if c.startswith(REPO) else c for c in cmd)}',
          flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=REPO, env=dict(os.environ, RECON_CHAR=CHAR_ID))
    if r.returncode != 0:
        raise SystemExit(f'段 {s.name} が失敗した（終了コード {r.returncode}）')
    missing = [p for p in s.outputs if mtime(p) is None]
    if missing:
        raise SystemExit(f'段 {s.name} の出力が無い：{missing}')
    write_stamp(s)
    print(f'=== {s.name}: {time.time() - t0:.0f} 秒', flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--char', default='haru', help='キャラクター（chars/<名前>.json）')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--from', dest='start')
    ap.add_argument('--only')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--standin', action='store_true')
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--adopt')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    setup(args.char)

    want_review = args.review or any(n in ('review', 'ingame') for n in (args.only, args.start, args.adopt))
    lst = stages(args.standin) + (review_stages() if want_review else [])
    names = [s.name for s in lst]
    for n in (args.start, args.only, None if args.adopt == 'all' else args.adopt):
        if n and n not in names:
            raise SystemExit(f'段の名前が違う：{n}（{", ".join(names)}）')
    if args.adopt:
        for s in lst:
            if args.adopt in ('all', s.name):
                missing = [p for p in s.outputs if mtime(p) is None]
                if missing or status(s) == 'todo':
                    print(f'{s.name}: 出力が無いか TODO なので受け入れない {missing}')
                    continue
                write_stamp(s)
                print(f'{s.name}: 今の出力を受け入れた（指紋を残した）')
        return
    if args.list:
        for s in lst:
            print(f'{s.name:8s} {status(s):5s} {s.script or "-":45s} {s.note}')
        return
    if args.only:
        sel = [s for s in lst if s.name == args.only]
    elif args.start:
        sel = lst[names.index(args.start):]
    else:
        sel = lst
    # 選ばなかった前の段は、出力があることだけ確かめる
    for s in lst[:lst.index(sel[0])]:
        missing = [p for p in s.outputs if mtime(p) is None]
        if missing:
            raise SystemExit(f'前の段 {s.name} の出力が無い：{missing}（--from {s.name} で作る）')
    # まだ無い段があれば、重い段を動かす前に止める
    for s in sel:
        if status(s) == 'todo':
            if s.script and os.path.exists(os.path.join(REPO, s.script)):
                raise SystemExit(f'段 {s.name} は TODO の印のまま（{s.script} はある）。stages() のその行の args・outputs・'
                                 'inputs が合っているか確かめて todo=False にする')
            raise SystemExit(f'段 {s.name} はまだ無い（TODO：{s.note}）。{s.script} を作って stages() を埋めるか、'
                             '--standin で代役を使う')
    for s in sel:
        st = status(s)
        if st == 'ok' and not args.force:
            print(f'--- {s.name}: 最新なので飛ばす', flush=True)
            continue
        run(s)
    print(f'\nできた：{OUT_GLB}')
    print('次に：tools/godot.sh import && tools/godot.sh test && '
          'tools/godot.sh run --fixed-fps 60 -- --demo=/tmp/demo_r' + (' --haru=r' if ID == 'haru' else ''))


if __name__ == '__main__':
    main()
