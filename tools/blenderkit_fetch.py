#!/usr/bin/env python3
"""BlenderKit（3D 素材のオンラインライブラリ）の素材を探して取ってくる。検討の結果：docs/art_orders/BlenderKit検討.md

リポジトリは公開で、確認ページは GLB を公開する。だから**リポジトリに入れてよいのは CC0 の素材だけ**。
Royalty Free（RF）は「簡単に取り出せない」ことが条件なので、git に入らない所（build/ など）にしか落とさず、`install` も断る。
落とした素材のフォルダの asset.json に、名前・id・ライセンス・作者・型（modelStyle など）・ページを書く。

  python3 tools/blenderkit_fetch.py search "rust" --type material --cc0      探す（--style lowpoly・-n 件数）
  python3 tools/blenderkit_fetch.py get <素材の id> [--file resolution_1K]   build/blenderkit/<名前>_<id8>/ へ落とす（asset.json に出所とライセンス）
  python3 tools/blenderkit_fetch.py texture <素材のフォルダ> [--map color|height] [--size 1024]
                                                材質：下地の色（albedo.jpg）か高さ（height.jpg）の絵を取り出し、size 以下の JPEG にする（Blender）
  python3 tools/blenderkit_fetch.py glb <素材のフォルダ>                     小物：Godot 用の GLB（gltf_godot・gltf・blend の順）を model.glb にする
  python3 tools/blenderkit_fetch.py install <素材のフォルダ> <置き先>         リポジトリへ写す。CC0 でなければ断る。置き先のフォルダの SOURCES.json に出所を足す

材質のファイル（resolution_1K など）は、絵を詰めた .blend。Blender（.venv-blender）で開いて絵を取り出す（中のスクリプトは動かさない）。
ネットワークは HTTPS_PROXY と SSL_CERT_FILE（無ければ /root/.ccr/ca-bundle.crt）に従う。API キーは要らない（無料の素材だけ）。
"""
import argparse
import datetime
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "build", "blenderkit")
BLENDER_PY = os.path.join(ROOT, ".venv-blender", "bin", "python")
API = "https://www.blenderkit.com/api/v1"
PAGE = "https://www.blenderkit.com/asset-gallery-detail/%s/"
# Godot で使える順（gltf_godot は Godot 向けに書き出した GLB）
MODEL_FILES = ["gltf_godot", "gltf", "blend"]


def _opener():
    ca = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
    ctx = ssl.create_default_context(cafile=ca if os.path.exists(ca) else None)
    return urllib.request.build_opener(urllib.request.ProxyHandler(), urllib.request.HTTPSHandler(context=ctx))


OPENER = _opener()


def http(url, raw=False, tries=5):
    """GET。途中で切れたら待って取り直す（HTTP のエラーはそのまま上げる）"""
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "project-relic/blenderkit_fetch"})
            with OPENER.open(req, timeout=120) as r:
                data = r.read()
            return data if raw else json.loads(data)
        except urllib.error.HTTPError:
            raise
        except Exception as e:  # 接続の切断・TLS の途中終了など
            if k == tries - 1:
                raise
            print(f"  取り直し（{e}）", file=sys.stderr)
            time.sleep(2 + 3 * k)


def params(a):
    """検索結果（dictParameters）と素材の詳細（parameters の並び）のどちらからも、型の情報を辞書で返す"""
    d = dict(a.get("dictParameters") or {})
    for p in a.get("parameters") or []:
        d.setdefault(p["parameterType"], p["value"])
    return d


def style_of(a):
    p = params(a)
    return p.get("modelStyle") or p.get("materialStyle") or ""


def record(a):
    """asset.json と SOURCES.json に書く出所の情報"""
    p = params(a)
    return {
        "name": a["name"], "id": a["id"], "asset_base_id": a.get("assetBaseId"),
        "license": a["license"], "author": (a.get("author") or {}).get("fullName", "").strip(),
        "style": style_of(a), "type": a.get("assetType"), "category": a.get("category"),
        "page": PAGE % a["id"], "faces": p.get("faceCount"), "texture_size_m": p.get("textureSizeMeters"),
        "procedural": p.get("procedural"),
        "files": sorted({f["fileType"] for f in a.get("files", [])}),
    }


def _git_ignored(path):
    """path がこのリポジトリに入らない所か（リポジトリの外か、.gitignore で無視される所。build/ など）"""
    if not (path + os.sep).startswith(ROOT + os.sep):
        return True
    r = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", path], capture_output=True)
    return r.returncode == 0


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:40] or "asset"


def cmd_search(args):
    terms = [args.words]
    if args.type:
        terms.append("asset_type:" + args.type)
    if args.cc0:
        terms.append("license:cc_zero")
    if args.style:
        terms.append("modelStyle:" + args.style)
    terms.append("is_free:true")
    q = urllib.parse.quote(" ".join(terms), safe=":+")
    d = http(f"{API}/search/?query={q}&page_size={args.n}&page={args.page}")
    print(f"{d['count']} 件（{args.page} ページ目）")
    for a in d["results"]:
        r = record(a)
        print(f"{a['id']}  {r['license']:<12} {r['style'] or '-':<11} {str(r['faces'] or ''):>7}  {r['name']}  / {r['author']}  [{','.join(r['files'])}]")


def cmd_get(args):
    a = http(f"{API}/assets/{args.id}/")
    rec = record(a)
    files = {f["fileType"]: f for f in a.get("files", [])}
    want = args.file or ("resolution_1K" if a.get("assetType") == "material" else next((t for t in MODEL_FILES if t in files), "blend"))
    if want not in files:
        want = "blend"   # 低い解像度の版が無い材質は、元の .blend（大きい）
    out = os.path.abspath(args.out)
    if a["license"] != "cc_zero" and not _git_ignored(out):
        sys.exit(f"{rec['name']} は {a['license']}：git が無視するフォルダ（build/ など）にしか落とさない（公開のリポジトリに入れないため）")
    d = os.path.join(out, f"{slug(rec['name'])}_{a['id'][:8]}")
    os.makedirs(d, exist_ok=True)
    f = files[want]
    ext = os.path.splitext(f["filename"])[1] or ".bin"
    dest = os.path.join(d, want + ext)
    if not os.path.exists(dest):
        # 取得先（署名つきの URL）を API に聞く。scene_uuid は何でもよい
        link = http(f"{f['downloadUrl']}?scene_uuid={uuid.uuid4()}")["filePath"]
        data = http(link, raw=True)
        with open(dest + ".part", "wb") as fp:
            fp.write(data)
        os.replace(dest + ".part", dest)
    rec.update({"fetched": datetime.date.today().isoformat(), "file": os.path.basename(dest), "file_type": want})
    with open(os.path.join(d, "asset.json"), "w") as fp:
        json.dump(rec, fp, ensure_ascii=False, indent=1)
    print(f"{rec['name']}（{rec['license']}・{rec['style'] or '-'}・{rec['author']}）→ {os.path.relpath(dest, ROOT)}")
    return d


def _asset(d):
    with open(os.path.join(d, "asset.json")) as fp:
        return json.load(fp)


def _blender(*argv):
    """この同じファイルを Blender の Python で動かす（-I：素材のフォルダのファイルを読み込まない）"""
    subprocess.run([BLENDER_PY, "-I", os.path.abspath(__file__), *argv], check=True)


def cmd_texture(args):
    a = _asset(args.dir)
    src = os.path.join(args.dir, a["file"])
    raw = os.path.join(args.dir, "texture_src.png")
    _blender("_blender_texture", src, raw, args.map)
    from PIL import Image
    im = Image.open(raw).convert("RGB" if args.map == "color" else "L")
    if max(im.size) > args.size:
        im.thumbnail((args.size, args.size), Image.LANCZOS)
    out = os.path.join(args.dir, "albedo.jpg" if args.map == "color" else "height.jpg")
    im.save(out, quality=90)
    os.remove(raw)
    print(f"{a['name']}：{im.size[0]}×{im.size[1]} → {os.path.relpath(out, ROOT)}")


def cmd_glb(args):
    a = _asset(args.dir)
    src = os.path.join(args.dir, a["file"])
    out = os.path.join(args.dir, "model.glb")
    if src.endswith(".glb"):
        shutil.copyfile(src, out)
    else:
        _blender("_blender_glb", src, out)
    print(f"{a['name']} → {os.path.relpath(out, ROOT)}（{os.path.getsize(out) // 1024} KB）")


def cmd_install(args):
    """リポジトリへ写す唯一の道。CC0 だけ。置き先のフォルダの SOURCES.json に出所を残す"""
    a = _asset(args.dir)
    if a["license"] != "cc_zero":
        sys.exit(f"{a['name']} は {a['license']}：公開のリポジトリには入れない（CC0 だけ）")
    dest = os.path.abspath(args.dest)
    if not dest.startswith(ROOT + os.sep) or dest.startswith(os.path.join(ROOT, "build") + os.sep):
        sys.exit("置き先はリポジトリの中（build/ を除く）")
    src = os.path.join(args.dir, args.what)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    man = os.path.join(os.path.dirname(dest), "SOURCES.json")
    data = {}
    if os.path.exists(man):
        with open(man) as fp:
            data = json.load(fp)
    data[os.path.basename(dest)] = {k: a[k] for k in ("name", "id", "license", "author", "style", "page", "fetched", "file_type")} | {
        "made_from": args.what}
    with open(man, "w") as fp:
        json.dump(dict(sorted(data.items())), fp, ensure_ascii=False, indent=1)
    print(f"{os.path.relpath(dest, ROOT)}（{a['name']}・CC0・{a['author']}）。出所：{os.path.relpath(man, ROOT)}")


# ---------------------------------------------------------------- Blender の中で動く部分

def _open_blend(path):
    import bpy
    # 素材の .blend の中のスクリプト（ドライバーなど）は動かさない
    bpy.ops.wm.open_mainfile(filepath=path, use_scripts=False)
    return bpy


def _upstream_images(node, seen=None):
    """node の入力をさかのぼって、つながっている絵のノードを近い順に返す"""
    seen = seen if seen is not None else set()
    found = []
    for inp in node.inputs:
        for link in inp.links:
            n = link.from_node
            if n.name in seen:
                continue
            seen.add(n.name)
            if n.type == "TEX_IMAGE" and n.image is not None:
                found.append(n.image)
            found += _upstream_images(n, seen)
    return found


def _blender_texture(src, out, kind="color"):
    bpy = _open_blend(src)
    # color：原理化 BSDF の Base Color につながる絵。height：出力の Displacement か Bump の Height につながる絵
    want = {"color": [("BSDF_PRINCIPLED", "Base Color")],
            "height": [("OUTPUT_MATERIAL", "Displacement"), ("BUMP", "Height")]}[kind]
    best = None
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for node_type, socket in want:
            for n in m.node_tree.nodes:
                sock = n.inputs.get(socket) if n.type == node_type else None
                if sock is not None and sock.links:
                    imgs = _upstream_images_from(sock)
                    if imgs:
                        best = best or (imgs[0] if kind == "color" else imgs[-1])
    if best is None and kind != "color":
        sys.exit("高さの絵が無い")
    if best is None:
        # 下地の色が絵につながっていない（手続きの材質）：sRGB の絵があればそれ
        best = next((i for i in bpy.data.images if i.colorspace_settings.name == "sRGB" and i.size[0] > 0), None)
    if best is None:
        sys.exit("下地の色の絵が無い（手続きの材質。焼き付けが要る）")
    best.file_format = "PNG"
    best.save(filepath=out)
    print(f"  絵：{best.name}（{best.size[0]}×{best.size[1]}）")


def _upstream_images_from(sock):
    imgs = []
    for link in sock.links:
        n = link.from_node
        if n.type == "TEX_IMAGE" and n.image is not None:
            imgs.append(n.image)
        imgs += _upstream_images(n, {n.name})
    # 色の絵（sRGB）を先に
    return sorted(imgs, key=lambda i: i.colorspace_settings.name != "sRGB")


def _blender_glb(src, out):
    bpy = _open_blend(src)
    # 場面の中で見えるメッシュ（描画から外してある素材もあるので、画面か描画のどちらかで見えれば入れる）
    for ob in bpy.context.scene.objects:
        ob.select_set(ob.type == "MESH" and (ob.visible_get() or not ob.hide_render))
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("_blender_"):
        {"_blender_texture": _blender_texture, "_blender_glb": _blender_glb}[sys.argv[1]](*sys.argv[2:])
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("words")
    s.add_argument("--type", choices=["material", "model"])
    s.add_argument("--cc0", action="store_true")
    s.add_argument("--style", help="lowpoly / painterly / anime / realistic など")
    s.add_argument("-n", type=int, default=20)
    s.add_argument("--page", type=int, default=1)
    g = sub.add_parser("get")
    g.add_argument("id")
    g.add_argument("--file", help="resolution_0_5K / resolution_1K / resolution_2K / gltf_godot / gltf / blend")
    g.add_argument("--out", default=OUT)
    al = sub.add_parser("texture")
    al.add_argument("dir")
    al.add_argument("--map", choices=["color", "height"], default="color")
    al.add_argument("--size", type=int, default=1024)
    gl = sub.add_parser("glb")
    gl.add_argument("dir")
    ins = sub.add_parser("install")
    ins.add_argument("dir")
    ins.add_argument("dest")
    ins.add_argument("--what", default="albedo.jpg", help="写すファイル（albedo.jpg か model.glb）")
    args = ap.parse_args()
    {"search": cmd_search, "get": cmd_get, "texture": cmd_texture, "glb": cmd_glb, "install": cmd_install}[args.cmd](args)


if __name__ == "__main__":
    main()
