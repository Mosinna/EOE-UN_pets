from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
OUTPUT_DIR = ROOT / "docs" / "previews"

COLS = 8
CELL_W = 192
CELL_H = 208
STATES = [
    ("idle", 180),
    ("running-right", 80),
    ("running-left", 80),
    ("waving", 110),
    ("jumping", 110),
    ("failed", 170),
    ("waiting", 180),
    ("running", 115),
    ("review", 150),
]

PREVIEWS = [
    ("coat on waving", "spritesheet_coat_on.png", "waving", "coat-on-waving.gif"),
    ("coat on working", "spritesheet_coat_on.png", "running", "coat-on-working.gif"),
    ("coat on review", "spritesheet_coat_on.png", "review", "coat-on-review.gif"),
    ("coat on failed", "spritesheet_coat_on.png", "failed", "coat-on-failed.gif"),
    ("coat off waving", "spritesheet_coat_off.png", "waving", "coat-off-waving.gif"),
    ("coat off working", "spritesheet_coat_off.png", "running", "coat-off-working.gif"),
    ("coat off review", "spritesheet_coat_off.png", "review", "coat-off-review.gif"),
    ("coat off failed", "spritesheet_coat_off.png", "failed", "coat-off-failed.gif"),
]

BACKGROUND = (248, 250, 252)
CHECK = (234, 238, 244)
CANVAS_W = 288
CANVAS_H = 312
SCALE = 1.22


def state_index(state_name: str) -> int:
    for index, (name, _duration) in enumerate(STATES):
        if name == state_name:
            return index
    raise ValueError(f"Unknown state: {state_name}")


def state_duration(state_name: str) -> int:
    return STATES[state_index(state_name)][1]


def make_background() -> Image.Image:
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), BACKGROUND)
    draw = ImageDraw.Draw(image)
    size = 16
    for y in range(0, CANVAS_H, size):
        for x in range(0, CANVAS_W, size):
            if (x // size + y // size) % 2:
                draw.rectangle((x, y, x + size - 1, y + size - 1), fill=CHECK)
    return image


def extract_frames(sheet: Image.Image, state_name: str) -> list[Image.Image]:
    row = state_index(state_name)
    frames = []
    for col in range(COLS):
        box = (
            col * CELL_W,
            row * CELL_H,
            (col + 1) * CELL_W,
            (row + 1) * CELL_H,
        )
        frame = sheet.crop(box)
        if frame.getchannel("A").getbbox() is not None:
            frames.append(frame)
    if not frames:
        raise ValueError(f"No frames found for {state_name}")
    return frames


def render_frame(source: Image.Image, background: Image.Image) -> Image.Image:
    frame = source.resize((round(CELL_W * SCALE), round(CELL_H * SCALE)), Image.Resampling.LANCZOS)
    composed = background.copy().convert("RGBA")
    x = (CANVAS_W - frame.width) // 2
    y = CANVAS_H - frame.height - 14
    composed.alpha_composite(frame, (x, y))
    return composed.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)


def make_gif(sprite_name: str, state_name: str, output_name: str) -> Path:
    sheet = Image.open(ASSET_DIR / sprite_name).convert("RGBA")
    background = make_background()
    frames = [render_frame(frame, background) for frame in extract_frames(sheet, state_name)]
    output = OUTPUT_DIR / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=state_duration(state_name),
        loop=0,
        optimize=True,
        disposal=2,
    )
    return output


def main() -> int:
    outputs = []
    for _label, sprite_name, state_name, output_name in PREVIEWS:
        outputs.append(make_gif(sprite_name, state_name, output_name))
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
