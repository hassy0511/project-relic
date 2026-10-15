#!/usr/bin/env python3
"""汚れ・傷みの層の「型」の絵を、CC0 の材質の写真から作る（docs/art_orders/BlenderKit検討.md・42 章 14.2）。

写真の色は使わない。写真から「どこが汚れているか」の形だけを取り出し、RGBA の絵 2 枚に詰める。
ゲームのシェーダー（godot/assets/shaders/kit_detail.gdshaderinc）が、形の内側をパレットの色で平らに塗る。

  masks.png（512 px）   RGB 汚れの斑（grime）  Dirty Concrete の暗い所。大きな斑
                        A   欠け（chips）      White Rusted Metal の欠け（白地に茶の小さな斑）
  masks2.png（256 px）  RGB むら（mottle）     White Plaster 02 の明暗。しっくいのむら
                        A   筋（streaks）      Rusty Metal Sheet の赤い所を縦に伸ばした筋（さび・雨だれ）

- どの型も、写真の細かな粒（近くで写真に見える元）をぼかして消し、なめらかな山と谷の形にする。
  シェーダーはその形を 1 本のしきい値で切るので、縁のはっきりした平らな斑になる（近くでも粒が出ない）。
- 値は 0〜1 に均す（順位で並べ直す）。だから「値が 1 - p より大きい所」の面積がちょうど p になり、
  材質の "cover"（覆う割合）がそのまま面積の割合になる。
- 写真はどれもつなぎ目の無い絵なので、ぼかしは周期のまま（FFT）にして、つなぎ目が出ないようにする。
- 1 枚に型を 2 つだけ入れる（RGB は 3 つとも同じ値の白黒、A は別の型）。VRAM 圧縮（PC は BC3、スマホは ETC2）は
  RGB の 3 つをまとめて近似するので、RGB に別々の型を 3 つ入れると、しきい値で切った縁が 4×4 画素の段々に崩れた
  （切った形の食い違いが 2.4%）。白黒の RGB と、別に圧縮される A なら、どちらの形式でも縁がなめらかなまま。

素材は tools/blenderkit_fetch.py get / texture で build/blenderkit/<フォルダ>/albedo.jpg に落としておく（git に入らない所）。
リポジトリへ入れてよいのは CC0 だけ：asset.json の license が cc_zero でなければ止まる。出所は置き先の SOURCES.json に書く。

  python3 tools/grime_masks.py                  godot/assets/kit/grime/masks.png・masks2.png と SOURCES.json を作る
  python3 tools/grime_masks.py --preview <png>  型ごとに、覆う割合 0.15・0.35・0.6 で切った見本も書く
  python3 tools/grime_masks.py --src <フォルダ>  素材のフォルダ（既定は build/blenderkit）
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "build", "blenderkit")
OUT_DIR = os.path.join(ROOT, "godot", "assets", "kit", "grime")

# 書き出す絵：名前・大きさ・RGB（白黒）の型・A の型
OUTPUTS = [
    ("masks.png", 512, "grime", "chips"),
    ("masks2.png", 256, "mottle", "streaks"),
]
# 型 → 素材のフォルダ（build/blenderkit の中）と、取り出し方（SOURCES.json に書く）
MASKS = {
    "grime": ("dirty_concrete_520cf6cb", "暗い所（明るさの反転）をぼかした大きな斑"),
    "chips": ("white_rusted_metal_5ada52b3", "茶の欠けの形（暗い所）の縁をなめらかにしたもの"),
    "streaks": ("rusty_metal_sheet_265a5e2e", "赤い所（R−B）を縦に長くぼかした筋"),
    "mottle": ("white_plaster_02_0965c56c", "明暗をぼかしたむら"),
}


def blur(x, sx, sy=None):
    """周期の（つなぎ目の無い）ガウスぼかし。sx・sy は画素の標準偏差"""
    sy = sx if sy is None else sy
    h, w = x.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2.0 * np.pi ** 2 * ((fx * sx) ** 2 + (fy * sy) ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(x) * g))


def equalize(x):
    """値を順位で 0〜1 に均す（値が 1 - p より大きい所の面積 = p）"""
    flat = x.ravel()
    order = np.argsort(flat, kind="stable")
    ranks = np.empty(flat.size, dtype=np.float64)
    ranks[order] = np.arange(flat.size)
    return (ranks / (flat.size - 1)).reshape(x.shape)


def down(x, size):
    """1024 → size（k×k の平均）"""
    k = x.shape[0] // size
    return x.reshape(size, k, size, k).mean(axis=(1, 3))


def load(folder, src):
    path = os.path.join(src, folder, "albedo.jpg")
    meta_path = os.path.join(src, folder, "asset.json")
    if not os.path.exists(path) or not os.path.exists(meta_path):
        sys.exit(f"素材が無い：{path}（tools/blenderkit_fetch.py get・texture で落とす）")
    with open(meta_path) as fp:
        meta = json.load(fp)
    if meta.get("license") != "cc_zero":
        sys.exit(f"{meta.get('name')} は {meta.get('license')}：公開のリポジトリには入れない（CC0 だけ）")
    img = Image.open(path).convert("RGB")
    if img.size != (1024, 1024):
        img = img.resize((1024, 1024), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0, meta


def lum(im):
    return im[..., 0] * 0.299 + im[..., 1] * 0.587 + im[..., 2] * 0.114


def tie_breaker(seed, size=1024):
    """同じ値の所（無地の所）を順位で並べるときの、なめらかな小さな揺れ（走査の順の模様を作らない）"""
    rng = np.random.default_rng(seed)
    n = blur(rng.standard_normal((size, size)), 24.0)
    return n / np.std(n)


def grime(im):
    d = 1.0 - lum(im)
    # 写真の粒を消し（10 px。縁の崩れは 3 px の分を少し残す）、明るさの大きなうねり（110 px）を引いて、斑が絵の全体に散るように
    f = blur(d, 10.0) + 0.12 * blur(d, 3.0) - 0.9 * blur(d, 110.0)
    return f + 1e-4 * tie_breaker(1)


def streaks(im):
    red = im[..., 0] - im[..., 2]
    # 赤い所を縦に長く（縦 48 px・横 6 px）ぼかし、横の広い斑（横 30 px）を引いて、筋を立たせる（256 px で横 1.5 px）
    f = blur(red, 6.0, 48.0) - 0.8 * blur(red, 30.0, 48.0)
    # 筋の長さ・太さを不ぞろいに：縦にゆっくり変わる濃さを足す
    rng = np.random.default_rng(7)
    n = blur(rng.standard_normal(f.shape), 6.0, 120.0)
    f = f / np.std(f) + 0.45 * n / np.std(n)
    return f + 1e-3 * tie_breaker(2)


def mottle(im):
    l = lum(im)
    f = blur(l, 9.0) - 0.7 * blur(l, 128.0)
    return -f / np.std(f) + 1e-3 * tie_breaker(3)


def chips(im):
    d = 1.0 - lum(im)
    # 欠け（茶）は白地よりずっと暗い。形だけを 0/1 にして、縁を少しだけなめらかにする（角ばった形は残す）
    core = blur(d, 1.0)
    t = np.percentile(core, 86.0)
    m = np.clip((core - t) / 0.06 + 0.5, 0.0, 1.0)
    # 欠けの中は形のまま高く、外は欠けから離れるほど低く（覆う割合を上げると、欠けが太り、つながる）
    f = blur(m, 1.0) + 0.5 * blur(m, 6.0) + 0.25 * blur(m, 20.0)
    # 欠けから遠い所の並び順は、なめらかな揺れで決める（無地の所に粒を作らない）
    return f + 0.03 * tie_breaker(4)


MAKERS = {"grime": grime, "streaks": streaks, "mottle": mottle, "chips": chips}


def build(src, size, rgb_kind, a_kind):
    planes = {}
    sources = []
    for ch, kind in (("rgb", rgb_kind), ("a", a_kind)):
        folder, how = MASKS[kind]
        im, meta = load(folder, src)
        planes[ch] = equalize(down(MAKERS[kind](im), size))
        sources.append({
            "channel": ch, "mask": kind, "made_from": f"{folder}/albedo.jpg", "how": how,
            "name": meta["name"], "id": meta["id"], "license": meta["license"], "author": meta["author"],
            "style": meta.get("style"), "page": meta.get("page"), "fetched": meta.get("fetched"),
            "file_type": meta.get("file_type"),
        })
    g = planes["rgb"]
    rgba = np.stack([g, g, g, planes["a"]], axis=-1)
    return np.clip(np.round(rgba * 255.0), 0, 255).astype(np.uint8), sources


def write_sources(name, size, sources):
    man = os.path.join(OUT_DIR, "SOURCES.json")
    data = {}
    if os.path.exists(man):
        with open(man) as fp:
            data = json.load(fp)
    kinds = "・".join(f"{s['channel'].upper()} {s['mask']}" for s in sources)
    data[name] = {
        "made_by": "tools/grime_masks.py",
        "made": datetime.date.today().isoformat(),
        "size": size,
        "note": f"写真の色は使わず、形だけを 0〜1 に均した型（{kinds}）。素材はどれも CC0",
        "sources": sources,
    }
    with open(man, "w") as fp:
        json.dump(dict(sorted(data.items())), fp, ensure_ascii=False, indent=1)
        fp.write("\n")
    return man


def preview(rgba, path):
    """型ごとに 3 つの覆う割合で切った見本（2 枚つなげて、つなぎ目が無いかも見る）"""
    rows = []
    for c in (1, 3):
        row = []
        for p in (0.15, 0.35, 0.6):
            v = rgba[..., c].astype(np.float64) / 255.0
            row.append(np.tile((v > 1.0 - p).astype(np.uint8) * 255, (1, 2)))
        rows.append(np.concatenate(row, axis=1))
    Image.fromarray(np.concatenate(rows, axis=0)).save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", help="切った見本の PNG の置き先（絵ごとに _masks.png などを付ける）")
    ap.add_argument("--src", default=SRC, help="素材のフォルダ（tools/blenderkit_fetch.py の置き場）")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, size, rgb_kind, a_kind in OUTPUTS:
        rgba, sources = build(args.src, size, rgb_kind, a_kind)
        out = os.path.join(OUT_DIR, name)
        Image.fromarray(rgba, "RGBA").save(out, optimize=True)
        man = write_sources(name, size, sources)
        print(f"{os.path.relpath(out, ROOT)}（{size}×{size} RGBA、{os.path.getsize(out) // 1024} KB）。出所：{os.path.relpath(man, ROOT)}")
        if args.preview:
            pv = args.preview.replace(".png", "_" + name)
            preview(rgba, pv)
            print("見本：", pv)


if __name__ == "__main__":
    main()
