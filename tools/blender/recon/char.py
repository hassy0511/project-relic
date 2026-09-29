"""キャラクターごとの設定（tools/blender/recon/chars/<id>.json）を読む。再構築の各段が共通に使う。

どのキャラクターを作るかは環境変数 RECON_CHAR（既定 'haru'）で選ぶ。build_char.py（`--char yana`）が
子の段（views.py・carve.py・texture.py など）を動かすときにこの変数を渡す。段を単独で動かすときは
  RECON_CHAR=yana .venv-blender/bin/python tools/blender/recon/texture.py
のようにする。

■ 設定ファイルの中身（chars/haru.json を見本に）
  id               キャラクターの名前。作業のファイル名の頭（<id>_mesh.glb、<id>_textured_apose.glb、材質 <id>_body・<id>_face）
  art.ref, art.dir 絵のブランチとフォルダ（元の絵が作業のフォルダの src に無いとき git show で取り出す）
  work             作業のフォルダ（リポジトリからの相対。ハルは build/recon）
  height_m         本来の身長。再構築そのものは基準の身長 recon_height_m（1.55m）の座標で行い、各スクリプトの
                   長さの定数（ハルで決めた値）をそのまま使えるようにする。骨付けの段（ai_character.py の --final-height）で
                   本来の身長へ一様に拡大する
  views            全身の絵：{視点: {file, azimuth}}。'three_quarter' は「形に使う斜めの絵」の役
                   （ハルは約 31 度の古い絵、ヤーナは右前 45 度の絵を同じ役で使う）
  shape_views      形の外形に使ってよい絵（腕の無い絵は除く）
  source_files     src に取り出す絵の一覧
  face             顔の絵のファイル名・表情の順（アトラスの左上・右上・左下・右下）・顔の絵の上の範囲
  out_glb          ゲームの GLB（リポジトリからの相対）
  rig_args         ai_character.py へ渡す持ち物・拳などの引数（ハル：銃・光刃・拳のシェイプキー）
  stages_skip      動かさない段（ヤーナは銃の段 'gun' が要らない）
  params           各スクリプトの定数の上書き：{"モジュール.定数名": 値}。書かなければハルの値のまま
"""
from __future__ import annotations

import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CHARS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chars')
ID = os.environ.get('RECON_CHAR', 'haru') or 'haru'


def load(char_id: str) -> dict:
    path = os.path.join(CHARS_DIR, f'{char_id}.json')
    if not os.path.exists(path):
        raise SystemExit(f'キャラクターの設定が無い：{path}')
    with open(path, encoding='utf-8') as fp:
        return json.load(fp)


CFG = load(ID)
WORK_REL = CFG['work']
WORK = os.path.join(REPO, WORK_REL)
HEIGHT = float(CFG.get('height_m', 1.55))              # 本来の身長
RECON_HEIGHT = float(CFG.get('recon_height_m', 1.55))  # 再構築の座標の身長
OUT_GLB = CFG['out_glb']
OUT_NAME = os.path.splitext(os.path.basename(OUT_GLB))[0]   # haru_r、yana
MAT_BODY = f'{ID}_body'
MAT_FACE = f'{ID}_face'
PARAMS = CFG.get('params', {})


def _like(v, default):
    """JSON の値（リストなど）を、既定の値と同じ形（タプル）にそろえる"""
    if isinstance(default, tuple) and isinstance(v, list):
        return tuple(_like(x, default[i] if i < len(default) else None) for i, x in enumerate(v))
    if isinstance(default, dict) and isinstance(v, dict):
        return {k: _like(x, default.get(k)) for k, x in v.items()}
    return v


def p(key: str, default):
    """定数の上書き（params の "モジュール.定数名"）。無ければ既定の値（ハルの値）"""
    if key in PARAMS:
        return _like(PARAMS[key], default)
    return default


def get(key: str, default=None):
    """設定の値（"face.file" のように . で区切った道）"""
    cur = CFG
    for k in key.split('.'):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
