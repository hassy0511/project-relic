"""content/ の YAML（three.js 版の内容データ）を、Godot 版の JSON に変換する（移行のときに 1 回使った）。
以後は godot/content/ の JSON が正本。
  python3 tools/content_to_json.py
"""
import json
import os

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PAIRS = [
    ('content/tuning.yaml', 'godot/content/tuning.json'),
    ('content/areas/mvp.yaml', 'godot/content/areas/mvp.json'),
    ('content/dialogue/mvp.yaml', 'godot/content/dialogue/mvp.json'),
    ('content/events/mvp.yaml', 'godot/content/events/mvp.json'),
]
for src, dst in PAIRS:
    with open(os.path.join(ROOT, src), encoding='utf-8') as f:
        data = yaml.safe_load(f)
    with open(os.path.join(ROOT, dst), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(src, '->', dst)
