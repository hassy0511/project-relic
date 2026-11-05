"""焼き直した動作だけを、元の GLB に差し込む（GLB の中身を直接書き換える。Blender は使わない）。

  python3 tools/blender/recon/splice_anims.py --clips combo1,combo2,combo3
      [--from godot/assets/models/haru_r.glb] [--base <GLB のパス か git の版>] [--out godot/assets/models/haru_r.glb]

rebake_anims.py は元の GLB を Blender で読み込んで書き出すので、動作を 1 本直しただけでも、形（法線・UV の境で頂点が
分かれて増える：haru 21354 → 22051）、節の数値（1e-7 の誤差）、ほかの動作（標本の数：dead 37 → 19、run 41 → 21）まで
少しずつ変わる。この道具は、元の GLB（既定は rebake_anims.py の BASE_REV の版）をそのまま使い、--clips の動作だけを
--from の GLB（rebake_anims.py が書き出した物）から差し替える。形・材質・画像・節・スキン・ほかの動作は元のバイトのまま。

使い方（動作を直したら）：
  .venv-blender/bin/python tools/blender/recon/rebake_anims.py --only combo1,combo2,combo3
  python3 tools/blender/recon/splice_anims.py --clips combo1,combo2,combo3
--from の動作の対象の節は、名前で元の GLB の節に合わせる（無い名前があれば止まる）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DEFAULT = 'godot/assets/models/haru_r.glb'
COMP_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
N_COMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}


def base_rev() -> str:
    """rebake_anims.py の BASE_REV（bpy を読み込まずに、文字で拾う）"""
    src = open(os.path.join(os.path.dirname(__file__), 'rebake_anims.py'), encoding='utf-8').read()
    return re.search(r"^BASE_REV = '([0-9a-f]+)'", src, re.M).group(1)


def read_glb(data: bytes) -> tuple[dict, bytes]:
    magic, _ver, _total = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67, 'GLB ではない'
    n, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    js = json.loads(data[20:20 + n])
    o = 20 + n
    if o >= len(data):
        return js, b''
    bl, kind = struct.unpack_from('<II', data, o)
    assert kind == 0x004E4942
    return js, data[o + 8:o + 8 + bl]


def write_glb(path: str, js: dict, bin_: bytes) -> None:
    jb = json.dumps(js, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    jb += b' ' * (-len(jb) % 4)
    bin_ += b'\0' * (-len(bin_) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bin_)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(jb), 0x4E4F534A) + jb)
        f.write(struct.pack('<II', len(bin_), 0x004E4942) + bin_)


def accessor_bytes(js: dict, bin_: bytes, i: int) -> bytes:
    """アクセサの中身を、詰めた（間の空かない）バイト列で返す"""
    a = js['accessors'][i]
    if 'sparse' in a or 'bufferView' not in a:
        sys.exit(f'アクセサ {i} は疎（sparse）か中身が無い：この道具は扱わない')
    bv = js['bufferViews'][a['bufferView']]
    elem = COMP_SIZE[a['componentType']] * N_COMP[a['type']]
    stride = bv.get('byteStride') or elem
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    if stride == elem:
        return bin_[start:start + elem * a['count']]
    return b''.join(bin_[start + k * stride:start + k * stride + elem] for k in range(a['count']))


def splice(base_js: dict, base_bin: bytes, src_js: dict, src_bin: bytes, clips: list[str]) -> tuple[dict, bytes]:
    js = json.loads(json.dumps(base_js))
    node_index = {n.get('name'): i for i, n in enumerate(js['nodes'])}
    # 1) 元の動作のうち、差し替える物を除いて、使われているアクセサ・バッファビューを集めて詰め直す
    keep_anims = [a for a in js.get('animations', []) if a['name'] not in clips]
    used_acc: list[int] = []

    def use(i: int) -> None:
        if i not in used_acc:
            used_acc.append(i)

    for m in js.get('meshes', []):
        for pr in m['primitives']:
            for v in pr['attributes'].values():
                use(v)
            if 'indices' in pr:
                use(pr['indices'])
            for t in pr.get('targets', []):
                for v in t.values():
                    use(v)
    for s in js.get('skins', []):
        if 'inverseBindMatrices' in s:
            use(s['inverseBindMatrices'])
    for a in keep_anims:
        for sm in a['samplers']:
            use(sm['input'])
            use(sm['output'])
    used_acc.sort()
    used_bv = sorted({js['accessors'][i]['bufferView'] for i in used_acc}
                     | {im['bufferView'] for im in js.get('images', []) if 'bufferView' in im})
    out = bytearray()
    bv_map: dict[int, int] = {}
    new_bvs = []
    for old in used_bv:
        bv = dict(js['bufferViews'][old])
        out += b'\0' * (-len(out) % 4)
        start = bv.get('byteOffset', 0)
        bv['byteOffset'] = len(out)
        bv['buffer'] = 0
        out += base_bin[start:start + bv['byteLength']]
        bv_map[old] = len(new_bvs)
        new_bvs.append(bv)
    acc_map: dict[int, int] = {}
    new_accs = []
    for old in used_acc:
        a = dict(js['accessors'][old])
        a['bufferView'] = bv_map[a['bufferView']]
        acc_map[old] = len(new_accs)
        new_accs.append(a)

    def remap(i: int) -> int:
        return acc_map[i]

    for m in js.get('meshes', []):
        for pr in m['primitives']:
            pr['attributes'] = {k: remap(v) for k, v in pr['attributes'].items()}
            if 'indices' in pr:
                pr['indices'] = remap(pr['indices'])
            if 'targets' in pr:
                pr['targets'] = [{k: remap(v) for k, v in t.items()} for t in pr['targets']]
    for s in js.get('skins', []):
        if 'inverseBindMatrices' in s:
            s['inverseBindMatrices'] = remap(s['inverseBindMatrices'])
    for im in js.get('images', []):
        if 'bufferView' in im:
            im['bufferView'] = bv_map[im['bufferView']]
    for a in keep_anims:
        for sm in a['samplers']:
            sm['input'] = remap(sm['input'])
            sm['output'] = remap(sm['output'])

    # 2) 新しい動作のアクセサを足す（同じ時間の列は 1 本にまとめたまま）
    def add_accessor(src_i: int, cache: dict[int, int]) -> int:
        if src_i in cache:
            return cache[src_i]
        a = dict(src_js['accessors'][src_i])
        data = accessor_bytes(src_js, src_bin, src_i)
        out.extend(b'\0' * (-len(out) % 4))
        new_bvs.append({'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data)})
        out.extend(data)
        a['bufferView'] = len(new_bvs) - 1
        a.pop('byteOffset', None)
        new_accs.append(a)
        cache[src_i] = len(new_accs) - 1
        return cache[src_i]

    src_anims = {a['name']: a for a in src_js.get('animations', [])}
    new_anims: dict[str, dict] = {}
    for name in clips:
        if name not in src_anims:
            sys.exit(f'--from に動作 {name} が無い')
        sa = src_anims[name]
        cache: dict[int, int] = {}
        samplers, channels = [], []
        for ch in sa['channels']:
            sm = sa['samplers'][ch['sampler']]
            tname = src_js['nodes'][ch['target']['node']].get('name')
            if tname not in node_index:
                sys.exit(f'動作 {name} の対象の節 {tname} が元の GLB に無い')
            samplers.append({'input': add_accessor(sm['input'], cache), 'output': add_accessor(sm['output'], cache),
                             'interpolation': sm.get('interpolation', 'LINEAR')})
            channels.append({'sampler': len(samplers) - 1,
                             'target': {'node': node_index[tname], 'path': ch['target']['path']}})
        an = {'name': name, 'channels': channels, 'samplers': samplers}
        for k, v in sa.items():
            if k not in an:
                an[k] = v
        new_anims[name] = an

    # 元の並びを保つ（差し替えた動作は元の位置。元に無ければ最後）
    anims = []
    for a in js.get('animations', []):
        anims.append(new_anims.pop(a['name']) if a['name'] in clips else a)
    anims.extend(new_anims.values())
    js['animations'] = anims
    js['accessors'] = new_accs
    js['bufferViews'] = new_bvs
    js['buffers'] = [{'byteLength': len(out) + (-len(out) % 4)}]
    return js, bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--clips', required=True, help='差し替える動作（, 区切り）')
    ap.add_argument('--from', dest='src', default=DEFAULT, help='新しい動作の入った GLB（rebake_anims.py の書き出し）')
    ap.add_argument('--base', default=None, help='元の GLB（ファイル か git の版。既定は rebake_anims.py の BASE_REV の --out）')
    ap.add_argument('--out', default=DEFAULT)
    args = ap.parse_args()
    clips = [c for c in args.clips.split(',') if c]
    out_rel = os.path.relpath(os.path.abspath(args.out), REPO)
    if args.base and os.path.exists(args.base):
        base_data = open(args.base, 'rb').read()
        print(f'元の GLB：{args.base}')
    else:
        rev = args.base or base_rev()
        base_data = subprocess.run(['git', 'show', f'{rev}:{out_rel}'], cwd=REPO, capture_output=True, check=True).stdout
        print(f'元の GLB：git {rev}:{out_rel}')
    src_js, src_bin = read_glb(open(args.src, 'rb').read())
    base_js, base_bin = read_glb(base_data)
    js, bin_ = splice(base_js, base_bin, src_js, src_bin, clips)
    write_glb(args.out, js, bin_)
    print(f'差し替え：{", ".join(clips)} → {args.out}（{os.path.getsize(args.out) / 1e6:.2f} MB、'
          f'動作 {len(js["animations"])} 本、アクセサ {len(js["accessors"])}）')


if __name__ == '__main__':
    main()
