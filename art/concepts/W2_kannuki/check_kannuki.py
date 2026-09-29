"""Read-only deliverable checks for W2-03 PNGs (requires Pillow)."""

import json
from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parent
DESIGN = [
    "kannuki_turnaround.png", "kannuki_scale.png", "kannuki_mechanics.png",
    "kannuki_attacks.png", "kannuki_phases.png", "kannuki_arena.png",
]
MODEL = [
    "kannuki_3d_front.png", "kannuki_3d_back.png",
    "kannuki_3d_side_right.png", "kannuki_3d_top.png",
    "kannuki_3d_bottom.png", "kannuki_3d_front_right45.png",
    "kannuki_arm_side.png", "kannuki_arm_top.png", "kannuki_arm_front.png",
    "kannuki_3d_parts.png", "kannuki_core_open.png",
]
SPECIAL = {"kannuki_3d_parts.png"}
results = {}
errors = []

for name in DESIGN + MODEL:
    path = ROOT / name
    if not path.exists():
        errors.append(f"missing: {name}")
        continue
    with Image.open(path) as im:
        wanted_size = (4096, 2048) if name in DESIGN else (2048, 2048)
        if im.size != wanted_size:
            errors.append(f"wrong size {name}: {im.size}, expected {wanted_size}")
        if name in MODEL:
            if im.mode != "RGBA":
                errors.append(f"not RGBA: {name} ({im.mode})")
            alpha = im.getchannel("A") if "A" in im.getbands() else None
            bbox = alpha.point(lambda a: 255 if a > 5 else 0).getbbox() if alpha else None
            if not bbox:
                errors.append(f"no visible subject: {name}")
            elif name not in SPECIAL and min(bbox[0], bbox[1],
                                                  im.width-bbox[2], im.height-bbox[3]) < 8:
                errors.append(f"subject clipped or too close to edge: {name} {bbox}")
            corners = [alpha.getpixel((x, y)) for x, y in
                       ((0, 0), (im.width-1, 0), (0, im.height-1),
                        (im.width-1, im.height-1))] if alpha else []
            if any(c != 0 for c in corners):
                errors.append(f"opaque corner in transparent view: {name} {corners}")
            results[name] = {"size": im.size, "mode": im.mode,
                             "bbox_xyxy_px": bbox,
                             "top_row": bbox[1] if bbox else None,
                             "bottom_row": bbox[3]-1 if bbox else None,
                             "center_col": round((bbox[0]+bbox[2]-1)/2) if bbox else None}
        else:
            if name != "kannuki_arena.png":
                corner = im.convert("RGB").getpixel((0, im.height-1))
                if max(abs(c-230) for c in corner) > 8:
                    errors.append(f"sheet background differs from #E6E6E6: {name} {corner}")
            results[name] = {"size": im.size, "mode": im.mode}

for name in ("spec.md", "spec_kannuki_3d.md", "generate_kannuki.py",
             "kannuki_source.blend", "metrics.json"):
    if not (ROOT/name).exists():
        errors.append(f"missing source/spec: {name}")

print(json.dumps({"checked_png": len(results), "errors": errors,
                  "images": results}, indent=2, ensure_ascii=False))
raise SystemExit(1 if errors else 0)
