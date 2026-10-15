"""会話の顔のアイコンを、Codex の顔の絵（art/* のブランチ）から作る。

    python3 tools/face_icons.py

- 元の絵：胸から上・1024px・透過（W1-01b・W1-01c のハル、W1 のヤーナ・ナゴミ、W2-01 の住人）。
  人によって顔の大きさと位置が違うので、顔の大きさ・目の高さがそろうように、人ごとの正方形で切り出す（CROP）。
- 出力：godot/assets/ui/faces/<絵の名前>_<表情>.png（256px・透過）と、その .import（容量を抑える lossy の設定）。
  ゲームでは顔の枠（ui_parts_face_frame）の窓に入れる（Hud.face_texture。話し手の名前と表情の読み替えも Hud）。
- ハルは 2 組：フレームを着けた顔（W1-01b。smile だけ大きさをそろえた r2）と、着ける前の顔（W1-01c、haru_nf）。
- 絵の差し替え（r2 など）が届いたら、FACES の行を直して実行し直す。
"""
import io
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "godot", "assets", "ui", "faces")
SIZE = 256

# 絵の名前 → (ブランチ, ファイルの形（%s が表情）, {出力の表情: 元の表情})
FACES = {
    "haru": ("origin/art/w1-haru3d", "art/concepts/W1_haru_3d/haru_face_%s.png",
             {f: f for f in ["normal", "surprised", "smirk", "serious", "laugh", "sad", "angry", "troubled"]} | {"smile": "smile_r2"}),
    "haru_nf": ("origin/art/w1-haru3d", "art/concepts/W1_haru_3d/haru_face_%s_noframe.png",
                {f: f for f in ["normal", "surprised", "smirk", "serious", "laugh", "sad", "angry", "smile", "troubled"]}),
    "yana": ("origin/art/w1-yana", "art/concepts/W1_yana/yana_face_%s.png",
             {f: f for f in ["normal", "angry", "laugh", "sad", "serious", "smile", "smirk", "surprised"]}),
    "nagomi": ("origin/art/w1-nagomi", "art/concepts/W1_nagomi/nagomi_face_%s.png",
               {f: f for f in ["normal", "analyzing", "confused", "dormant", "happy", "joking", "sad", "warning"]}),
    "burton": ("origin/art/w2-townsfolk", "art/concepts/W2_townsfolk/burton_face_%s.png",
               {f: f for f in ["normal", "angry", "smile", "surprised"]}),
    # ニコは r2（女の子の版）
    "nico": ("origin/art/w2-townsfolk", "art/concepts/W2_townsfolk/nico_face_%s.png",
             {f: f + "_r2" for f in ["normal", "angry", "smile", "surprised"]}),
    "trude": ("origin/art/w2-townsfolk", "art/concepts/W2_townsfolk/trude_face_%s.png",
              {f: f for f in ["normal", "angry", "smile", "surprised"]}),
    "shopkeeper": ("origin/art/w2-townsfolk", "art/concepts/W2_townsfolk/shopkeeper_face_%s.png",
                   {f: f for f in ["normal", "smile"]}),
    "junker": ("origin/art/w2-townsfolk", "art/concepts/W2_townsfolk/junker_face_%s.png",
               {f: f for f in ["normal", "smile"]}),
}

# 切り出す正方形（元の 1024px の絵の画素で 左, 上, 1 辺）。顔の幅がハルとそろい、目の高さが正方形の約 5 割に来るように測った。
# はみ出す所は透明で埋める（ニコは髪が大きいので引いて切る）。ナゴミは球なので絵のまま
CROP = {
    "haru": (69, 40, 900),
    "haru_nf": (69, 40, 900),
    "yana": (25, -27, 870),
    "nagomi": (0, 0, 1024),
    "burton": (175, 60, 640),
    "nico": (-71, -39, 1100),
    "trude": (80, 30, 830),
    "shopkeeper": (95, 20, 820),
    "junker": (173, 58, 665),
}

IMPORT = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://assets/ui/faces/{name}"

[params]

compress/mode=1
compress/high_quality=false
compress/lossy_quality=0.85
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


def git_image(branch: str, path: str) -> Image.Image:
    data = subprocess.run(["git", "-C", ROOT, "show", f"{branch}:{path}"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(data)).convert("RGBA")


def crop(im: Image.Image, box) -> Image.Image:
    x0, y0, side = box
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, (-x0, -y0), im)
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for key, (branch, pattern, faces) in FACES.items():
        for face, src in faces.items():
            name = f"{key}_{face}.png"
            out = os.path.join(OUT, name)
            crop(git_image(branch, pattern % src), CROP[key]).save(out, optimize=True)
            imp = out + ".import"
            # 既にある .import（uid の入ったもの）は残す。新しい絵だけ lossy の設定を書く
            if not os.path.exists(imp):
                with open(imp, "w", encoding="utf-8") as f:
                    f.write(IMPORT.format(name=name))
            made += 1
    print(f"[faces] {made} 枚 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
