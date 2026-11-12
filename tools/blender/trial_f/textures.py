"""haru_f：テクスチャ（色見本・発光）。顔の地図は face_tex.py"""
from __future__ import annotations

import math
import os

from PIL import Image

from . import spec

PAL_COLS, PAL_CELL = 4, 16


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_palette(out_dir):
    names = list(spec.PALETTE.keys())
    rows = math.ceil(len(names) / PAL_COLS)
    base = Image.new('RGB', (PAL_COLS * PAL_CELL, rows * PAL_CELL), (0, 0, 0))
    emit = Image.new('RGB', base.size, (0, 0, 0))
    for i, n in enumerate(names):
        x, y = (i % PAL_COLS) * PAL_CELL, (i // PAL_COLS) * PAL_CELL
        base.paste(hex_rgb(spec.PALETTE[n]), (x, y, x + PAL_CELL, y + PAL_CELL))
        if n in spec.EMISSIVE:
            emit.paste(hex_rgb(spec.EMISSIVE[n]), (x, y, x + PAL_CELL, y + PAL_CELL))
    os.makedirs(out_dir, exist_ok=True)
    pb, pe = os.path.join(out_dir, 'haru_f_palette.png'), os.path.join(out_dir, 'haru_f_emit.png')
    base.save(pb)
    emit.save(pe)
    return pb, pe


def make_face_placeholder(out_dir):
    p = os.path.join(out_dir, 'haru_f_face.png')
    Image.new('RGB', (64, 64), hex_rgb(spec.SKIN_HEX)).save(p)
    return p
