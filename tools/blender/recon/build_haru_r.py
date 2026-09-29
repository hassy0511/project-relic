"""絵から起こしたハル（haru_r）を、元の絵から godot/assets/models/haru_r.glb まで一度に作る（以前からの入口）。

中身は build_char.py（キャラクターごとの設定 chars/<id>.json で動く一般の流れ）の --char haru。
引数は build_char.py と同じ（--list、--from、--only、--force、--standin、--review、--adopt）。
  .venv-blender/bin/python tools/blender/recon/build_haru_r.py          ＝ npm run haru:recon
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_char  # noqa: E402

if __name__ == '__main__':
    if not any(a == '--char' or a.startswith('--char=') for a in sys.argv[1:]):
        sys.argv[1:1] = ['--char', 'haru']
    build_char.main()
