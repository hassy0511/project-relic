#!/usr/bin/env bash
# Godot を決まった設定で動かす。
#   tools/godot.sh import            素材の取り込み（.glb などを Godot 用に変換）
#   tools/godot.sh test              自動テスト（画面なし）
#   tools/godot.sh shot <引数...>    画面を描いて撮影（仮想ディスプレイ＋ソフトウェアの Vulkan）
#   tools/godot.sh run <引数...>     そのまま起動（画面なし）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT="$ROOT/.tools/godot/godot"
PROJ="$ROOT/godot"
[ -x "$GODOT" ] || bash "$ROOT/tools/setup_godot.sh" >/dev/null
cmd="${1:-}"; shift || true
case "$cmd" in
  import) "$GODOT" --headless --path "$PROJ" --import ;;
  test) "$GODOT" --headless --path "$PROJ" --fixed-fps 60 --script res://tests/run_tests.gd -- "$@" ;;
  shot)
    VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1920x1080x24" \
      "$GODOT" --path "$PROJ" --rendering-driver vulkan "$@" ;;
  run) "$GODOT" --headless --path "$PROJ" "$@" ;;
  *) echo "使い方: tools/godot.sh import|test|shot|run"; exit 1 ;;
esac
