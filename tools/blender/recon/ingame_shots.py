"""Godot の中のハル（haru_r）の確認の画像を撮る（build/recon/review/ingame_*.png）。bpy は使わない。

  .venv-blender/bin/python tools/blender/recon/ingame_shots.py [--out build/recon/review] [--skip-demo]
  1. tools/godot.sh import（haru_r.glb を取り込み直す）
  2. 見本の撮影：tools/godot.sh shot --resolution 1600x900 -- --demo=<一時フォルダ> --haru=r
     （ゲームの見本の流れ。タイトル・走り・会話・ロックオン・斬り・ドリル。約 4 分）→ ingame_00_title.png など
  3. 見せる画像：godot_showcase.gd（全身 4 方向・顔の 4 表情・動作 4 つ。ゲームと同じ PlayerView と光）
     → ingame_showcase.png
  --demo のフォルダは Godot のプロジェクト（godot/）から見た相対パスになるので、絶対パスを渡す。
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
GODOT_SH = os.path.join(REPO, 'tools', 'godot.sh')
SHOWCASE = os.path.join(REPO, 'tools', 'blender', 'recon', 'godot_showcase.gd')


def sh(args: list[str]) -> str:
    print('$', ' '.join(args), flush=True)
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode != 0:
        print(out[-3000:])
        raise SystemExit(f'失敗（終了コード {r.returncode}）：{" ".join(args)}')
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(REPO, 'build', 'recon', 'review'))
    ap.add_argument('--skip-demo', action='store_true', help='見本の撮影（約 4 分）を飛ばし、見せる画像だけ')
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    sh([GODOT_SH, 'import'])
    if not args.skip_demo:
        tmp = tempfile.mkdtemp(prefix='haru_r_demo_')
        log = sh([GODOT_SH, 'shot', '--resolution', '1600x900', '--', f'--demo={tmp}', '--haru=r'])
        if '見本の完了（失敗 0 件）' not in log:
            print(log[-3000:])
            raise SystemExit('見本が失敗した')
        for p in sorted(glob.glob(os.path.join(tmp, '*.png'))):
            dst = os.path.join(out, 'ingame_' + os.path.basename(p))
            shutil.move(p, dst)
            print('撮影：', os.path.relpath(dst, REPO))
        shutil.rmtree(tmp, ignore_errors=True)
    dst = os.path.join(out, 'ingame_showcase.png')
    log = sh([GODOT_SH, 'shot', '--resolution', '400x450', '--script', SHOWCASE, '--', dst])
    print([ln for ln in log.splitlines() if ln.startswith('撮影')][-1])


if __name__ == '__main__':
    main()
