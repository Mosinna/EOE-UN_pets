from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


COLS = 8
SOURCE_COLS = 4
SOURCE_ROWS = 2
CELL_W = 192
CELL_H = 208
STATE_COUNTS = [
    ("idle", 6),
    ("running_right", 8),
    ("running_left", 8),
    ("waving", 4),
    ("jumping", 5),
    ("failed", 8),
    ("waiting", 6),
    ("running", 6),
    ("review", 6),
]
OUTFITS = ("coat_on", "coat_off")
WAVING_SCALE_FACTOR = 1.0
WAVING_BOTTOM = 3
COAT_OFF_REVIEW_SEQUENCE = (0, 1, 2, 3, 2, 1)


def is_green_pixel(r: int, g: int, b: int) -> bool:
    return g > 95 and g - r > 38 and g - b > 38


def estimate_background(image: Image.Image) -> tuple[int, int, int]:
    rgba = image.convert("RGBA")
    samples = []
    max_x = rgba.width - 1
    max_y = rgba.height - 1
    for x, y in (
        (0, 0),
        (max_x, 0),
        (0, max_y),
        (max_x, max_y),
        (rgba.width // 2, 0),
        (rgba.width // 2, max_y),
    ):
        r, g, b, _a = rgba.getpixel((x, y))
        samples.append((r, g, b))
    return tuple(sorted(channel)[len(channel) // 2] for channel in zip(*samples))


def clamp(value: float, low: int = 0, high: int = 255) -> int:
    return max(low, min(high, round(value)))


def remove_green_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    bg_r, bg_g, bg_b = estimate_background(rgba)
    cleaned = []
    for r, g, b, a in rgba.getdata():
        distance = ((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2) ** 0.5
        green_dominance = g - max(r, b)
        if a < 8 or (is_green_pixel(r, g, b) and distance < 90):
            cleaned.append((0, 0, 0, 0))
            continue

        alpha = a
        if is_green_pixel(r, g, b):
            alpha = min(alpha, clamp((distance - 24) / 96 * 255))
        if alpha < 12:
            cleaned.append((0, 0, 0, 0))
            continue

        if green_dominance > 10:
            g = min(g, max(r, b) + 10)
        cleaned.append((r, g, b, alpha))
    rgba.putdata(cleaned)
    return rgba


def frame_slot(source: Image.Image, slot_index: int) -> Image.Image:
    return source.crop(slot_box(source, slot_index))


def slot_box(source: Image.Image, slot_index: int) -> tuple[int, int, int, int]:
    slot_w = source.width // SOURCE_COLS
    slot_h = source.height // SOURCE_ROWS
    col = slot_index % SOURCE_COLS
    row = slot_index // SOURCE_COLS
    return (col * slot_w, row * slot_h, (col + 1) * slot_w, (row + 1) * slot_h)


def state_boxes(source: Image.Image, outfit: str, state_name: str, frame_count: int) -> list[tuple[int, int, int, int]]:
    if state_name == "waving":
        slot_w = source.width // SOURCE_COLS
        return [(index * slot_w, 0, (index + 1) * slot_w, source.height) for index in range(frame_count)]
    return [slot_box(source, index) for index in range(frame_count)]


def fit_crop_to_cell(crop: Image.Image, scale: float, bottom: int = 3, x_bias: int = 0, y_offset: int = 0) -> Image.Image:
    transparent = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    if crop.getchannel("A").getbbox() is None:
        return transparent

    resized = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.Resampling.LANCZOS)
    x = (CELL_W - resized.width) // 2 + x_bias
    y = CELL_H - resized.height - bottom + y_offset
    transparent.alpha_composite(resized, (x, y))
    return transparent


def clear_low_alpha(image: Image.Image, threshold: int = 12) -> Image.Image:
    rgba = image.copy()
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if pixels[x, y][3] <= threshold:
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def normalize_transparent_pixels(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if pixels[x, y][3] == 0:
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def crop_foreground(source: Image.Image, box: tuple[int, int, int, int]) -> Image.Image | None:
    cleaned = remove_green_background(source.crop(box))
    bbox = cleaned.getchannel("A").getbbox()
    if bbox is None:
        return None
    pad = 2
    bbox = (
        max(0, bbox[0] - pad),
        max(0, bbox[1] - pad),
        min(cleaned.width, bbox[2] + pad),
        min(cleaned.height, bbox[3] + pad),
    )
    return cleaned.crop(bbox)


def foreground_crops(source: Image.Image, boxes: list[tuple[int, int, int, int]]) -> tuple[list[Image.Image | None], int, int]:
    crops = []
    max_w = 1
    max_h = 1
    for box in boxes:
        crop = crop_foreground(source, box)
        if crop is None:
            crops.append(None)
            continue
        crops.append(crop)
        max_w = max(max_w, crop.width)
        max_h = max(max_h, crop.height)
    return crops, max_w, max_h


def fit_scale(max_w: int, max_h: int) -> float:
    return min((CELL_W - 10) / max_w, (CELL_H - 6) / max_h)


def scale_for_boxes(source: Image.Image, boxes: list[tuple[int, int, int, int]]) -> float:
    _crops, max_w, max_h = foreground_crops(source, boxes)
    return fit_scale(max_w, max_h)


def strip_to_cells(
    source: Image.Image,
    boxes: list[tuple[int, int, int, int]],
    max_scale: float | None = None,
    bottom: int = 3,
) -> list[Image.Image]:
    crops, max_w, max_h = foreground_crops(source, boxes)
    scale = min((CELL_W - 10) / max_w, (CELL_H - 6) / max_h)
    if max_scale is not None:
        scale = min(scale, max_scale)
    cells = []
    for crop in crops:
        if crop is None:
            cells.append(Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)))
        else:
            cells.append(clear_low_alpha(fit_crop_to_cell(crop, scale, bottom=bottom)))
    return cells


def anchor_center_x(cell: Image.Image) -> float | None:
    alpha = cell.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return None

    pixels = alpha.load()
    total = 0
    weighted_x = 0
    for y in range(min(CELL_H, 158)):
        for x in range(30, CELL_W - 30):
            if pixels[x, y] > 16:
                total += 1
                weighted_x += x
    if not total:
        return (bbox[0] + bbox[2]) / 2
    return weighted_x / total


def shift_cell(cell: Image.Image, x_offset: int) -> Image.Image:
    if x_offset == 0:
        return cell
    shifted = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    shifted.alpha_composite(cell, (x_offset, 0))
    return shifted


def alpha_components(cell: Image.Image, threshold: int = 16) -> list[list[tuple[int, int]]]:
    alpha = cell.getchannel("A")
    pixels = alpha.load()
    seen = [[False for _x in range(CELL_W)] for _y in range(CELL_H)]
    components: list[list[tuple[int, int]]] = []
    for y in range(CELL_H):
        for x in range(CELL_W):
            if seen[y][x] or pixels[x, y] <= threshold:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            component: list[tuple[int, int]] = []
            while stack:
                px, py = stack.pop()
                component.append((px, py))
                for ny in range(max(0, py - 1), min(CELL_H, py + 2)):
                    for nx in range(max(0, px - 1), min(CELL_W, px + 2)):
                        if seen[ny][nx] or pixels[nx, ny] <= threshold:
                            continue
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            components.append(component)
    return sorted(components, key=len, reverse=True)


def remove_detached_specks(cell: Image.Image) -> Image.Image:
    components = alpha_components(cell)
    if len(components) <= 1:
        return cell
    keep = components[0]
    cutoff = max(24, round(len(keep) * 0.006))
    cleaned = cell.copy()
    pixels = cleaned.load()
    for component in components[1:]:
        if len(component) >= cutoff:
            continue
        for x, y in component:
            pixels[x, y] = (0, 0, 0, 0)
    return cleaned


def stabilize_horizontal_by_anchor(cells: list[Image.Image]) -> list[Image.Image]:
    anchors = [anchor_center_x(cell) for cell in cells]
    valid = sorted(anchor for anchor in anchors if anchor is not None)
    if not valid:
        return cells
    target = valid[len(valid) // 2]
    return [
        shift_cell(cell, round(target - anchor)) if anchor is not None else cell
        for cell, anchor in zip(cells, anchors)
    ]


def stable_idle_cells(source: Image.Image, frame_count: int) -> list[Image.Image]:
    return [remove_detached_specks(cell) for cell in stabilize_horizontal_by_anchor(strip_to_cells(source, state_boxes(source, "", "idle", frame_count)))]


def stable_coat_off_review_cells(source: Image.Image) -> list[Image.Image]:
    all_boxes = state_boxes(source, "coat_off", "review", 6)
    stable_crops, stable_max_w, stable_max_h = foreground_crops(source, all_boxes[:4])
    scale = fit_scale(stable_max_w, stable_max_h)
    source_cells = [
        clear_low_alpha(fit_crop_to_cell(crop, scale)) if crop is not None else Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        for crop in stable_crops
    ]
    sequenced = [source_cells[index].copy() for index in COAT_OFF_REVIEW_SEQUENCE]
    return stabilize_horizontal_by_anchor(sequenced)


def compose_outfit(source_dir: Path, outfit: str) -> tuple[Image.Image, dict[str, int]]:
    atlas = Image.new("RGBA", (CELL_W * COLS, CELL_H * len(STATE_COUNTS)), (0, 0, 0, 0))
    counts: dict[str, int] = {}
    row_cells: dict[str, list[Image.Image]] = {}
    idle_source = Image.open(source_dir / f"{outfit}_idle.png").convert("RGBA")
    idle_scale = scale_for_boxes(idle_source, state_boxes(idle_source, outfit, "idle", 6))
    for row, (state_name, frame_count) in enumerate(STATE_COUNTS):
        source_state = "running_right" if state_name == "running_left" else state_name
        source_name = f"{outfit}_{source_state}.png"
        source = Image.open(source_dir / source_name).convert("RGBA")
        if state_name == "running_left":
            cells = [cell.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for cell in row_cells["running_right"]]
        elif state_name == "idle":
            cells = stable_idle_cells(source, frame_count)
        else:
            boxes = state_boxes(source, outfit, state_name, frame_count)
            if outfit == "coat_off" and state_name == "review":
                cells = stable_coat_off_review_cells(source)
            else:
                max_scale = idle_scale * WAVING_SCALE_FACTOR if state_name == "waving" else None
                bottom = WAVING_BOTTOM if state_name == "waving" else 3
                cells = strip_to_cells(source, boxes, max_scale=max_scale, bottom=bottom)
            if state_name == "waving":
                cells = stabilize_horizontal_by_anchor(cells)
        counts[state_name.replace("_", "-")] = len(cells)
        row_cells[state_name] = cells
        for col in range(COLS):
            if col < len(cells):
                cell = cells[col]
            else:
                cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
            atlas.alpha_composite(cell, (col * CELL_W, row * CELL_H))
    return atlas, counts


def make_contact_sheet(atlases: dict[str, Image.Image], output: Path) -> None:
    scale = 0.42
    row_gap = 34
    label_h = 28
    thumb_w = round(CELL_W * COLS * scale)
    thumb_h = round(CELL_H * len(STATE_COUNTS) * scale)
    sheet = Image.new("RGB", (thumb_w, len(atlases) * (thumb_h + label_h + row_gap) - row_gap), "#f4f6f8")
    draw = ImageDraw.Draw(sheet)
    y = 0
    for outfit, atlas in atlases.items():
        draw.text((8, y + 6), outfit, fill="#111827")
        checker = Image.new("RGB", atlas.size, "#ffffff")
        check_draw = ImageDraw.Draw(checker)
        check = 16
        for cy in range(0, atlas.height, check):
            for cx in range(0, atlas.width, check):
                if (cx // check + cy // check) % 2:
                    check_draw.rectangle((cx, cy, cx + check - 1, cy + check - 1), fill="#e5e7eb")
        preview = Image.alpha_composite(checker.convert("RGBA"), atlas)
        preview = preview.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS).convert("RGB")
        sheet.paste(preview, (0, y + label_h))
        y += label_h + thumb_h + row_gap
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--asset-dir", required=True, type=Path)
    parser.add_argument("--qa-dir", required=True, type=Path)
    args = parser.parse_args()

    args.asset_dir.mkdir(parents=True, exist_ok=True)
    args.qa_dir.mkdir(parents=True, exist_ok=True)

    atlases: dict[str, Image.Image] = {}
    report = {"source_dir": str(args.source_dir), "atlases": {}}
    for outfit in OUTFITS:
        atlas, counts = compose_outfit(args.source_dir, outfit)
        atlases[outfit] = atlas
        atlas = normalize_transparent_pixels(atlas)
        asset_path = args.asset_dir / f"spritesheet_{outfit}.png"
        qa_path = args.qa_dir / f"spritesheet_{outfit}.png"
        atlas.save(asset_path)
        atlas.save(qa_path)
        report["atlases"][outfit] = {
            "asset": str(asset_path),
            "qa_png": str(qa_path),
            "size": list(atlas.size),
            "cell": [CELL_W, CELL_H],
            "states": counts,
        }

    contact_sheet = args.qa_dir / "suit-contact-sheet.png"
    make_contact_sheet(atlases, contact_sheet)
    report["contact_sheet"] = str(contact_sheet)
    (args.qa_dir / "suit-build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
