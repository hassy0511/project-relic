"""Blender のスクリプトをまとめて実行して、GLB を書き出す。

  npm run assets            # 変更のあったスクリプトだけ
  npm run assets -- --all   # すべて
  npm run assets -- --render  # 確認用の画像（art/renders/）も描く
スクリプトとその依存（lib/）の内容のハッシュを .build_cache.json に記録し、変わったものだけ実行する。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
PY = os.environ.get('BLENDER_PYTHON', os.path.join(REPO, '.venv-blender', 'bin', 'python'))
CACHE = os.path.join(HERE, '.build_cache.json')

TARGETS = [
    'models/haru_proxy.py',
    'levels/mvp_greybox.py',
]


def digest(paths: list[str]) -> str:
    h = hashlib.sha256()
    for p in paths:
        with open(p, 'rb') as f:
            h.update(f.read())
    return h.hexdigest()


def main() -> int:
    if not os.path.exists(PY):
        print('Blender の Python 環境がありません。先に npm run setup:blender を実行してください。')
        return 1
    force = '--all' in sys.argv
    render = '--render' in sys.argv
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    libs = sorted(os.path.join(HERE, 'lib', f) for f in os.listdir(os.path.join(HERE, 'lib')) if f.endswith('.py'))
    extra = [os.path.join(HERE, 'models', 'humanoid_anims.py')]
    failed = 0
    for t in TARGETS:
        path = os.path.join(HERE, t)
        key = digest([path, *libs, *extra])
        if not force and not render and cache.get(t) == key:
            print(f'skip  {t}')
            continue
        print(f'build {t}')
        args = [PY, path] + (['--render'] if render else [])
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            failed += 1
            print(r.stdout[-2000:], r.stderr[-4000:])
            continue
        cache[t] = key
    json.dump(cache, open(CACHE, 'w'), indent=2)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
