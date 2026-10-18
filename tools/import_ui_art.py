"""Codex の UI の絵（W2-08、art/concepts/W2_ui）から、ゲームで使う分を godot/assets/ui/ へ写す。

使い方（Blender 用の Python に PIL が入っている）:
    mkdir -p build/intake/w2ui
    git archive origin/art/w2-ui art/concepts/W2_ui | tar -x -C build/intake/w2ui --strip-components=3
    .venv-blender/bin/python tools/import_ui_art.py build/intake/w2ui
    .venv-blender/bin/python tools/import_ui_art.py build/intake/w2ui ui_title_r2 ...   # 名前を並べると、その分だけ写す

写し方（絵は描き足さない。大きさを変えるだけ）:
- 9 分割で伸ばす枠（パネル・ボタン・タブ・会話・名前・選択肢）は 50% に縮める。
  Godot の 9 分割は角を画像の画素のまま描くので、1920×1080 の画面で見本と同じ角の大きさ（約半分）になるようにする。
  角の大きさ（縮めたあとの画素）は godot/scripts/ui/ui_art.gd の SLICE に書く（spec の値ではなく、実物を測った値）。
- アイコン（256×256）は 128×128 に縮める（画面では 40〜128px で使う。ミップマップなしでも粗くならないように）。
- そのほか（ゲージ・照準・顔の枠・スマホの操作の部品）は元の大きさのまま。画面では Control の縮尺で小さく描く。
- 取り込みの設定（.import）は UI 向け：圧縮なし、ミップマップなし、3D で使っても圧縮しない。
  ただし 3D の板として遠くからも見る部品（番機の頭上の「！」）はミップマップを作る（遠くで縮めてもちらつかない）。
- r2（2026-10-17 の直し。spec.md の「修正履歴」）：HP の中身 3 枚・チャージと解析の輪（枠と中身）は元の大きさのまま、
  選択中のボタン・選択肢の札は 50%。名前は納品のまま（_r2 付き。元の部品も残す）。
- タイトルの絵（ui_title_r2 1920×1080、ロゴ ui_title_logo / _nosub 1920×640）は元の大きさのまま。
  画面ではスマホで半分以下に縮めて描くので、ミップマップを作る（TextureRect は texture_filter を LINEAR_WITH_MIPMAPS に）。
  背景は不透明な絵なので、ブラウザ版の大きさを抑えるため非可逆（WebP）で取り込む。ロゴは透過の縁を保つため可逆。
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "godot" / "assets" / "ui"

HALF = [
    "ui_parts_panel_large", "ui_parts_panel_small", "ui_parts_panel_dialogue", "ui_parts_panel_name",
    "ui_parts_panel_choice", "ui_parts_panel_tab_idle", "ui_parts_panel_tab_selected",
    "ui_parts_panel_button_normal", "ui_parts_panel_button_focus", "ui_parts_panel_button_pressed",
    "ui_parts_panel_button_disabled",
    # r2
    "ui_parts_panel_button_focus_r2", "ui_parts_panel_choice_r2",
]
ICONS = [
    "icon_spark_rapid", "icon_spark_charge", "icon_blade", "icon_we_break_drill",
    "icon_item_repair_small", "icon_item_cell_small", "icon_item_chip", "icon_item_relic",
    "icon_item_kannuki_core", "icon_item_life_core", "icon_armor_body",
    "icon_rank_apprentice", "icon_rank_descent", "icon_rank_bronze", "icon_rank_silver",
    "icon_rank_gold", "icon_rank_master", "icon_rank_porcelain",
    "icon_map_current", "icon_map_quest", "icon_map_save_beacon", "icon_map_destination",
]
AS_IS = [
    "ui_parts_gauge_hp_frame", "ui_parts_gauge_hp_fill_full", "ui_parts_gauge_hp_fill_damaged",
    "ui_parts_gauge_hp_fill_danger", "ui_parts_gauge_energy_frame", "ui_parts_gauge_energy_fill",
    "ui_parts_gauge_boss_frame", "ui_parts_gauge_boss_fill", "ui_parts_gauge_boss_divider",
    "ui_parts_gauge_charge_stage1", "ui_parts_gauge_charge_stage2",
    "ui_parts_lockon_normal", "ui_parts_lockon_analyzing", "ui_parts_lockon_weakpoint",
    "ui_parts_lockon_alert",
    "ui_parts_face_frame", "ui_parts_face_frame_wait", "ui_parts_cursor", "ui_parts_advance",
    "ui_parts_touch_joystick_base", "ui_parts_touch_joystick_knob", "ui_parts_touch_button_normal",
    "ui_parts_touch_button_pressed", "ui_parts_touch_button_lock_on",
    "ui_parts_touch_symbol_jump", "ui_parts_touch_symbol_fire", "ui_parts_touch_symbol_slash",
    "ui_parts_touch_symbol_dash", "ui_parts_touch_symbol_special", "ui_parts_touch_symbol_heal",
    "ui_parts_touch_symbol_lock", "ui_parts_touch_symbol_behind", "ui_parts_touch_symbol_pause",
    # r2
    "ui_parts_gauge_hp_fill_full_r2", "ui_parts_gauge_hp_fill_damaged_r2", "ui_parts_gauge_hp_fill_danger_r2",
    "ui_parts_gauge_charge_track", "ui_parts_gauge_charge_fill_stage1", "ui_parts_gauge_charge_fill_stage2",
    "ui_parts_lockon_analyzing_track", "ui_parts_lockon_analyzing_fill",
]
# タイトルの絵（元の大きさ。ミップマップを作る。背景は非可逆）
TITLE = ["ui_title_r2", "ui_title_logo", "ui_title_logo_nosub"]
LOSSY = ["ui_title_r2"]

# 3D で使う部品（Sprite3D。遠くでは小さく描かれる）
MIPMAPPED = ["ui_parts_lockon_alert"]

IMPORT = """[remap]

importer="texture"
type="CompressedTexture2D"

[params]

compress/mode=0
mipmaps/generate=false
process/fix_alpha_border=true
process/premult_alpha=false
process/size_limit=0
detect_3d/compress_to=0
"""


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[2:])
    for name in HALF + ICONS + AS_IS + TITLE:
        if only and name not in only:
            continue
        im = Image.open(src / f"{name}.png").convert("RGBA")
        if name in LOSSY:
            im = im.convert("RGB")
        if name in HALF:
            im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        elif name in ICONS:
            im = im.resize((128, 128), Image.LANCZOS)
        dst = OUT / f"{name}.png"
        im.save(dst, optimize=True)
        imp = dst.with_suffix(".png.import")
        if not imp.exists():
            text = IMPORT
            if name in MIPMAPPED or name in TITLE:
                text = text.replace("mipmaps/generate=false", "mipmaps/generate=true")
            if name in LOSSY:
                text = text.replace("compress/mode=0", "compress/mode=1\ncompress/lossy_quality=0.9")
            imp.write_text(text)
        print(f"{name}.png {im.width}x{im.height}")


if __name__ == "__main__":
    main()
