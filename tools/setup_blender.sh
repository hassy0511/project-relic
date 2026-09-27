#!/usr/bin/env bash
# Blender（bpy）と音の生成（numpy, soundfile）をスクリプトから使うための Python 環境を作る。
# bpy 4.5 LTS は Python 3.11 専用。
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON311:-python3.11}
if ! command -v "$PY" >/dev/null 2>&1; then PY=python3; fi
"$PY" -c 'import sys; assert sys.version_info[:2]==(3,11), "bpy 4.5 には Python 3.11 が必要です"'
[ -d .venv-blender ] || "$PY" -m venv .venv-blender
.venv-blender/bin/pip install -q --upgrade pip
.venv-blender/bin/pip install -q "bpy==4.5.*" "numpy<2.3" soundfile
echo "Blender 環境の準備ができました: .venv-blender"
