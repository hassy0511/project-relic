#!/usr/bin/env bash
# Godot の開発環境を用意する（Claude の作業環境・CI・手元の Linux 共通）。
#   bash tools/setup_godot.sh            # Godot 本体とソフトウェア描画の部品
#   bash tools/setup_godot.sh --templates  # 書き出し用の部品（約 1.3GB）も入れる
set -euo pipefail
VERSION="${GODOT_VERSION:-4.5.1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/.tools/godot"
BIN="$DEST/Godot_v${VERSION}-stable_linux.x86_64"
mkdir -p "$DEST"
if [ ! -x "$BIN" ]; then
  echo "Godot ${VERSION} を取得します"
  curl -sSL -o "$DEST/godot.zip" "https://github.com/godotengine/godot/releases/download/${VERSION}-stable/Godot_v${VERSION}-stable_linux.x86_64.zip"
  (cd "$DEST" && unzip -oq godot.zip && rm godot.zip)
fi
ln -sf "$BIN" "$DEST/godot"
# GPU の無い環境で画面を描くための部品（Vulkan のソフトウェア実装と仮想ディスプレイ）
if [ ! -f /usr/share/vulkan/icd.d/lvp_icd.json ] || ! command -v xvfb-run >/dev/null; then
  if command -v apt-get >/dev/null && [ "$(id -u)" = "0" ]; then
    apt-get update -q >/dev/null
    apt-get install -y -q mesa-vulkan-drivers xvfb >/dev/null
  else
    echo "注意：mesa-vulkan-drivers と xvfb を入れてください（画面の撮影に使う）"
  fi
fi
if [ "${1:-}" = "--templates" ]; then
  TDIR="$HOME/.local/share/godot/export_templates/${VERSION}.stable"
  if [ ! -f "$TDIR/version.txt" ]; then
    echo "書き出し用の部品を取得します（約 1.3GB）"
    mkdir -p "$TDIR"
    curl -sSL -o /tmp/godot_templates.tpz "https://github.com/godotengine/godot/releases/download/${VERSION}-stable/Godot_v${VERSION}-stable_export_templates.tpz"
    unzip -oq /tmp/godot_templates.tpz -d /tmp/godot_templates
    mv /tmp/godot_templates/templates/* "$TDIR/"
    rm -rf /tmp/godot_templates /tmp/godot_templates.tpz
  fi
fi
"$DEST/godot" --version
