"""Курсоры тем: пишет файлы формата Xcursor без внешних утилит."""
import io
import random
import struct
import subprocess
from pathlib import Path

from PIL import Image

SIZES = [24, 32, 48, 64, 96]
ARROW = "M8 6V46L19 36 27 54 35 50 27 33H42Z"
HAND = ("M24 9a5 5 0 0 1 10 0V26l14 3a5 5 0 0 1 4 5V48l-4 10H26L12 40"
        "a4.5 4.5 0 0 1 7-6l5 5Z")
ALIASES = {
    "default": ["left_ptr", "arrow", "top_left_arrow"],
    "pointer": ["hand", "hand1", "hand2", "pointing_hand",
                "9d800788f1b08800ae810202380a0822", "e29285e634086352946a0e7090d73106"],
    "wait": ["watch", "clock", "0426c94ea35c87780ff01dc239897213"],
    "progress": ["left_ptr_watch", "half-busy", "00000000000000020006000e7e9ffc3f",
                 "08e8e1c95fe2fc01f976f1f063a24ccd", "3ecb610c1bf2410f44200f48c40d3599",
                 "9116a3ea924ed2162ecab71ba103b17f"],
}
TYPE = 0xfffd0002
FRAMES = 6


def render(svg: str, size: int) -> Image.Image:
    png = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)],
                         input=svg.encode(), capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def wrap(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{body}</svg>'


def shape(d: str, fill: str, edge: str, mark: str) -> str:
    return (f'<path d="{d}" fill="{fill}" stroke="{edge}" stroke-width="3" stroke-linejoin="round"/>'
            f'<circle cx="17" cy="27" r="3.2" fill="{mark}"/>' if d == ARROW else
            f'<path d="{d}" fill="{fill}" stroke="{edge}" stroke-width="3" stroke-linejoin="round"/>')


def gear(cx: float, cy: float, r: float, angle: float, fill: str, edge: str, core: str) -> str:
    teeth = "".join(f'<rect x="{-r * .2}" y="{-r}" width="{r * .4}" height="{r * .42}" fill="{fill}" '
                    f'stroke="{edge}" stroke-width="1" transform="rotate({i * 45})"/>' for i in range(8))
    return (f'<g transform="translate({cx} {cy}) rotate({angle})">{teeth}'
            f'<circle r="{r * .66}" fill="{fill}" stroke="{edge}" stroke-width="1.5"/>'
            f'<circle r="{r * .26}" fill="{core}"/></g>')


def glitch(im: Image.Image, seed: int) -> Image.Image:
    """Смещает две тонкие полосы: «помехи» Скрапкода."""
    rnd = random.Random(seed)
    out = im.copy()
    for _ in range(2):
        band = max(1, im.height // 14)
        y = rnd.randrange(im.height // 5, im.height - band)
        dx = rnd.choice([-1, 1]) * max(1, im.width // 16)
        strip = im.crop((0, y, im.width, y + band))
        out.paste((0, 0, 0, 0), (0, y, im.width, y + band))
        out.paste(strip, (dx, y))
    return out


def chunk(size: int, im: Image.Image, hot: tuple[int, int], delay: int) -> bytes:
    x, y = round(hot[0] * size / 64), round(hot[1] * size / 64)
    raw = im.tobytes()
    px = bytearray()
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i:i + 4]
        px += bytes((b * a // 255, g * a // 255, r * a // 255, a))
    return struct.pack("<9I", 36, TYPE, size, 1, size, size, x, y, delay) + bytes(px)


def write(path: Path, images: list[tuple[int, bytes]]) -> None:
    head = 16 + 12 * len(images)
    toc, pos = b"", head
    for size, data in images:
        toc += struct.pack("<3I", TYPE, size, pos)
        pos += len(data)
    path.write_bytes(b"Xcur" + struct.pack("<3I", 16, 0x10000, len(images)) + toc
                     + b"".join(d for _, d in images))


def build(out: Path, themes: dict) -> None:
    for key, t in themes.items():
        forge = key == "forge"
        fill = t["accent2"] if forge else t["accent"]
        edge = t["bg"]
        core = t["accent"] if forge else t["accent2"]
        root = out / f"{t['scheme']}Cursor"
        (root / "cursors").mkdir(parents=True)

        arrow = shape(ARROW, fill, edge, core)
        hand = shape(HAND, fill, edge, core)
        sets = {
            "default": ([arrow], (8, 6), 0),
            "pointer": ([hand], (29, 4), 0),
            "wait": ([gear(32, 32, 28, i * 45 / FRAMES, fill, edge, core) for i in range(FRAMES)], (32, 32), 80),
            "progress": ([arrow + gear(47, 47, 15, i * 45 / FRAMES, fill, edge, core) for i in range(FRAMES)],
                         (8, 6), 80),
        }
        for name, (frames, hot, delay) in sets.items():
            images = [(s, chunk(s, render(wrap(b), s) if forge else glitch(render(wrap(b), s), i), hot, delay))
                      for s in SIZES for i, b in enumerate(frames)]
            write(root / "cursors" / name, images)
            for alias in ALIASES[name]:
                (root / "cursors" / alias).symlink_to(name)
        (root / "index.theme").write_text(
            f"[Icon Theme]\nName={t['scheme']}Cursor\nComment=Курсор Когитатора\nInherits=capitaine-cursors\n")
