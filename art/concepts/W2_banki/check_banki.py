"""Read-only PNG inspection for W2-02. Run with Pillow; never changes images."""

from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parent
IDS = ("mini", "sentry", "charger", "shield", "floater")
VIEWS = ("front", "back", "side_right", "top", "bottom", "front_right45")


def bbox(path):
    with Image.open(path) as image:
        size = image.size
        alpha = image.convert("RGBA").getchannel("A")
        box = alpha.getbbox()
        corner = (alpha.getpixel((0, 0)), alpha.getpixel((size[0] - 1, 0)),
                  alpha.getpixel((0, size[1] - 1)), alpha.getpixel((size[0] - 1, size[1] - 1)))
        return size, box, corner, sorted(image.info)


def main():
    errors = []
    measurements = []
    expected = {"banki_family.png"}
    for id_ in IDS:
        for kind in ("turnaround", "scale", "mechanics", "attack", "states"):
            expected.add(f"{id_}_{kind}.png")
        expected.add(f"{id_}_illustration_study.png")
        views = VIEWS + (("side_left",) if id_ in {"charger", "shield"} else ())
        for view in views:
            expected.add(f"{id_}_3d_{view}.png")
        for kind in ("parts", "broken"):
            expected.add(f"{id_}_3d_{kind}.png")
    actual = {p.name for p in ROOT.glob("*.png") if not p.name.startswith("_preview")}
    for name in sorted(expected - actual):
        errors.append(f"MISSING {name}")
    for name in sorted(actual - expected):
        errors.append(f"UNEXPECTED {name}")
    print("expected", len(expected), "actual", len(actual))
    for id_ in IDS:
        print("\n" + id_.upper())
        views = VIEWS + (("side_left",) if id_ in {"charger", "shield"} else ())
        for view in views:
            path = ROOT / f"{id_}_3d_{view}.png"
            if not path.exists():
                continue
            size, box, corners, info = bbox(path)
            if size != (2048, 2048):
                errors.append(f"SIZE {path.name} {size}")
            if any(corners):
                errors.append(f"CORNER_ALPHA {path.name} {corners}")
            if box is None:
                errors.append(f"EMPTY {path.name}")
                continue
            l, t, r, b = box
            measurements.append((id_, view, t, b - 1, (l + r - 1) / 2))
            if l <= 1 or t <= 1 or r >= 2047 or b >= 2047:
                errors.append(f"EDGE_CLIP {path.name} {box}")
            print(f"{view:<14} top={t:4d} bottom={b-1:4d} x-center={(l+r-1)/2:6.1f} "
                  f"bbox=({l},{t},{r-1},{b-1}) info={','.join(info)}")
        for kind in ("parts", "broken"):
            path = ROOT / f"{id_}_3d_{kind}.png"
            if path.exists():
                size, box, corners, _ = bbox(path)
                if size != (2048, 2048) or any(corners) or box is None:
                    errors.append(f"INVALID {path.name}: {size} {box} {corners}")
    for name in sorted(expected):
        path = ROOT / name
        if not path.exists() or "_3d_" in name:
            continue
        size, box, _, info = bbox(path)
        if min(size) < 2048:
            errors.append(f"DESIGN_SIZE {name} {size}")
        print("DESIGN", name, size, box, ",".join(info))
    for id_ in IDS:
        upright = [(t, b) for name, view, t, b, _ in measurements
                   if name == id_ and view in {"front", "back", "side_right", "side_left", "front_right45"}]
        if max(t for t, _ in upright) - min(t for t, _ in upright) > 1:
            errors.append(f"TOP_MISMATCH {id_} {upright}")
        if max(b for _, b in upright) - min(b for _, b in upright) > 1:
            errors.append(f"BOTTOM_MISMATCH {id_} {upright}")
    print("\nERRORS", len(errors))
    for error in errors:
        print(error)
    print("\nMARKDOWN_MEASUREMENTS")
    print("| 型 | 向き | 上端行 | 下端行 | アルファ外形の中心列 |")
    print("|---|---|---:|---:|---:|")
    for id_, view, top, bottom, center in measurements:
        print(f"| `{id_}` | `{view}` | {top} | {bottom} | {center:.1f} |")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
