#!/usr/bin/env python3
"""元の GLB の形（メッシュ・骨・塗り・目印）をバイトのまま残し、動作だけを別の GLB のものに差し替える（Blender なし）。

  python3 tools/blender/recon/glb_splice_anims.py 元.glb 動作.glb 出力.glb [--only combo1,dead]

rebake_anims.py が最後に使う。Blender の glTF の読み込み→書き出しを 1 回通すと、法線・UV の境で頂点が分かれて
頂点が増え（haru_r：60,026 → 60,969）、法線も少し変わる。そこで Blender で焼いて書き出した GLB からは動作だけを取り、
元の GLB に入れる。動作の道は骨（ノード）の名前で付け直す。
--only：その名前の動作だけ差し替え、ほかの動作は元の GLB のバイトのまま残す（省略時は元の動作を全部捨てて、動作.glb の全部を入れる）。
"""
from __future__ import annotations

import argparse
import copy
import json
import struct
import sys

JSON_CHUNK, BIN_CHUNK = 0x4E4F534A, 0x004E4942


def read_glb(path: str) -> tuple[dict, bytes]:
    b = open(path, 'rb').read()
    magic, _ver, ln = struct.unpack_from('<4sII', b, 0)
    if magic != b'glTF':
        raise ValueError('%s: GLB ではない' % path)
    off, js, bin_ = 12, None, b''
    while off < ln:
        cl, ct = struct.unpack_from('<II', b, off)
        data = b[off + 8: off + 8 + cl]
        if ct == JSON_CHUNK:
            js = json.loads(data)
        elif ct == BIN_CHUNK:
            bin_ = data
        off += 8 + cl
    return js, bin_


def write_glb(path: str, js: dict, bin_: bytes) -> None:
    jb = json.dumps(js, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    jb += b' ' * (-len(jb) % 4)
    bb = bin_ + b'\0' * (-len(bin_) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bb)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<II', len(jb), JSON_CHUNK) + jb)
        f.write(struct.pack('<II', len(bb), BIN_CHUNK) + bb)


def view_bytes(js: dict, bin_: bytes, i: int) -> bytes:
    bv = js['bufferViews'][i]
    o = bv.get('byteOffset', 0)
    return bin_[o: o + bv['byteLength']]


def anim_accessors(anims: list[dict]) -> set[int]:
    out = set()
    for a in anims:
        for s in a['samplers']:
            out.add(s['input'])
            out.add(s['output'])
    return out


def other_accessors(js: dict) -> set[int]:
    """動作の外（メッシュ・皮）が使うアクセサー"""
    out = set()
    for m in js.get('meshes', []):
        for p in m['primitives']:
            out.update(p['attributes'].values())
            if 'indices' in p:
                out.add(p['indices'])
            for t in p.get('targets', []):
                out.update(t.values())
    for s in js.get('skins', []):
        if 'inverseBindMatrices' in s:
            out.add(s['inverseBindMatrices'])
    return out


def splice(base_path: str, anim_path: str, out_path: str, only: set[str] | None = None) -> dict:
    bjs, bbin = read_glb(base_path)
    sjs, sbin = read_glb(anim_path)
    src_anims = {a['name']: a for a in sjs.get('animations', [])}
    names = set(src_anims) if only is None else set(only)
    missing = names - set(src_anims)
    if missing:
        raise SystemExit('動作.glb に無い動作：%s' % sorted(missing))
    base_anims = bjs.get('animations', [])
    if only is None:
        kept = []
    else:
        kept = [a for a in base_anims if a['name'] not in names]
    # 元の GLB で残すアクセサー（動作の外と、残す動作）。番号を詰め直す
    keep_acc = sorted(other_accessors(bjs) | anim_accessors(kept))
    js = copy.deepcopy(bjs)
    js['animations'] = []
    acc_map = {old: new for new, old in enumerate(keep_acc)}
    keep_views = sorted({bjs['accessors'][i]['bufferView'] for i in keep_acc if 'bufferView' in bjs['accessors'][i]}
                        | {im['bufferView'] for im in bjs.get('images', []) if 'bufferView' in im})
    view_map = {old: new for new, old in enumerate(keep_views)}
    out_bin = bytearray()
    views = []

    def add_view(bv: dict, data: bytes) -> int:
        out_bin.extend(b'\0' * (-len(out_bin) % 4))
        nv = {k: v for k, v in bv.items() if k not in ('byteOffset', 'buffer')}
        nv['buffer'] = 0
        nv['byteOffset'] = len(out_bin)
        nv['byteLength'] = len(data)
        out_bin.extend(data)
        views.append(nv)
        return len(views) - 1

    for old in keep_views:
        add_view(bjs['bufferViews'][old], view_bytes(bjs, bbin, old))
    accessors = []
    for old in keep_acc:
        a = dict(bjs['accessors'][old])
        if 'bufferView' in a:
            a['bufferView'] = view_map[a['bufferView']]
        accessors.append(a)
    for im in js.get('images', []):
        if 'bufferView' in im:
            im['bufferView'] = view_map[im['bufferView']]
    for m in js.get('meshes', []):
        for p in m['primitives']:
            p['attributes'] = {k: acc_map[v] for k, v in p['attributes'].items()}
            if 'indices' in p:
                p['indices'] = acc_map[p['indices']]
            if 'targets' in p:
                p['targets'] = [{k: acc_map[v] for k, v in t.items()} for t in p['targets']]
    for s in js.get('skins', []):
        if 'inverseBindMatrices' in s:
            s['inverseBindMatrices'] = acc_map[s['inverseBindMatrices']]

    node_of = {}
    for i, n in enumerate(bjs['nodes']):
        if 'name' in n:
            node_of.setdefault(n['name'], i)
    src_acc_map: dict[int, int] = {}

    def take_src_accessor(i: int) -> int:
        if i in src_acc_map:
            return src_acc_map[i]
        a = dict(sjs['accessors'][i])
        if 'bufferView' in a:
            a['bufferView'] = add_view(sjs['bufferViews'][a['bufferView']], view_bytes(sjs, sbin, a['bufferView']))
        accessors.append(a)
        src_acc_map[i] = len(accessors) - 1
        return src_acc_map[i]

    def copy_kept(a: dict) -> dict:
        na = copy.deepcopy(a)
        for s in na['samplers']:
            s['input'], s['output'] = acc_map[s['input']], acc_map[s['output']]
        return na

    def copy_src(a: dict) -> dict:
        na = copy.deepcopy(a)
        for s in na['samplers']:
            s['input'], s['output'] = take_src_accessor(s['input']), take_src_accessor(s['output'])
        for c in na['channels']:
            nm = sjs['nodes'][c['target']['node']].get('name')
            if nm not in node_of:
                raise SystemExit('動作 %s の道の骨 %s が元の GLB に無い' % (a['name'], nm))
            c['target']['node'] = node_of[nm]
        return na

    # 並びは元の GLB の順（差し替えた動作は元の場所に）。元に無い動作は最後に
    order = [a['name'] for a in base_anims] + sorted(n for n in names if n not in {a['name'] for a in base_anims})
    for nm in order:
        if nm in names:
            js['animations'].append(copy_src(src_anims[nm]))
        else:
            ba = next((a for a in kept if a['name'] == nm), None)
            if ba is not None:
                js['animations'].append(copy_kept(ba))
    js['accessors'] = accessors
    js['bufferViews'] = views
    js['buffers'] = [{'byteLength': len(out_bin) + (-len(out_bin) % 4)}]
    if not js['animations']:
        del js['animations']
    write_glb(out_path, js, bytes(out_bin))
    return {'replaced': sorted(names), 'kept': [a['name'] for a in kept], 'bytes': len(out_bin)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('anims')
    ap.add_argument('out')
    ap.add_argument('--only', default=None)
    args = ap.parse_args()
    r = splice(args.base, args.anims, args.out, set(args.only.split(',')) if args.only else None)
    print('差し替えた動作 %s、元のまま %s、バイナリ %.2f MB' % (r['replaced'], r['kept'], r['bytes'] / 1e6))


if __name__ == '__main__':
    sys.exit(main())
