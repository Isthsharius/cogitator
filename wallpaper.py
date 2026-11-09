#!/usr/bin/env python3
"""Обои по умолчанию: рисуются кодом, поэтому их можно свободно распространять."""
import math
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SEED = 40_000
BG = (11, 8, 6)
LINE = (90, 58, 28)
BRASS = (192, 138, 62)
EMBER = (224, 40, 30)


def gear(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, teeth: int, width: int) -> None:
    points = []
    for i in range(teeth * 4):
        r = radius * (1.09 if i % 4 in (1, 2) else 1.0)
        a = 2 * math.pi * i / (teeth * 4)
        points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.line([*points, points[0]], fill=BRASS, width=width, joint="curve")


def traces(draw: ImageDraw.ImageDraw, rng: random.Random, w: int, h: int, unit: int) -> None:
    for _ in range(90):
        x, y = rng.randrange(0, w, unit), rng.randrange(0, h, unit)
        path = [(x, y)]
        for _ in range(rng.randint(3, 7)):
            dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1)])
            step = rng.randint(2, 7) * unit
            x, y = x + dx * step, y + dy * step
            path.append((x, y))
        draw.line(path, fill=LINE, width=max(1, unit // 16))
        r = max(2, unit // 6)
        draw.ellipse((x - r, y - r, x + r, y + r), outline=BRASS, width=max(1, unit // 16))


def render(w: int, h: int) -> Image.Image:
    rng = random.Random(SEED)
    unit = max(4, w // 64)
    art = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(art)
    traces(draw, rng, w, h, unit)
    cx, cy = w / 2, h * 0.56
    base = min(w, h)
    for ratio, teeth, width in ((0.46, 48, 3), (0.36, 36, 2), (0.25, 24, 3), (0.14, 12, 2)):
        gear(draw, cx, cy, base * ratio, teeth, max(1, width * w // 2560))
    art = art.filter(ImageFilter.GaussianBlur(max(0.4, w / 3000)))

    glow = Image.new("L", (w // 8 or 1, h // 8 or 1), 0)
    gw, gh = glow.size
    glow.putdata([min(255, int(255 * max(0.0, 1 - math.hypot((x - gw / 2) / (gw * 0.42), (y - gh * 0.68) / (gh * 0.62)))))
                  for y in range(gh) for x in range(gw)])
    glow = glow.resize((w, h), Image.Resampling.BICUBIC)
    lit = Image.composite(ImageChops.screen(art, Image.new("RGB", (w, h), EMBER)), art, glow.point(lambda v: v // 3))
    shade = glow.point(lambda v: 95 + v * 160 // 255)
    return ImageChops.multiply(lit, Image.merge("RGB", (shade, shade, shade)))


if __name__ == "__main__":
    width, height = (int(v) for v in sys.argv[2].split("x"))
    render(width, height).save(sys.argv[1])
