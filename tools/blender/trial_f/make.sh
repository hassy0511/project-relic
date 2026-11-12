#!/usr/bin/env bash
# haru_f を作り直す：顔の地図 → 形と GLB（Blender）→ 動作の差し込み → ゲームの素材へ置く。
#   bash tools/blender/trial_f/make.sh [--no-face]
# 先に：bash tools/setup_blender.sh と、絵の取り出し（build/art_f/。docs/art_orders/W1_ハル_Fable試作.md の「作り直しのコマンド」）
set -euo pipefail
cd "$(dirname "$0")/../../.."
PY=.venv-blender/bin/python
if [ "${1:-}" != "--no-face" ]; then
  $PY -m tools.blender.trial_f.face_tex
fi
$PY -m tools.blender.trial_f.build --out build/f/haru_f_mesh.glb | grep -E "tris|exported"
$PY -m tools.blender.trial_f.anim_bake --in build/f/haru_f_mesh.glb --out build/f/haru_f.glb
cp build/f/haru_f.glb godot/assets/models/haru_f.glb
echo "置いた：godot/assets/models/haru_f.glb（このあと tools/godot.sh import）"
