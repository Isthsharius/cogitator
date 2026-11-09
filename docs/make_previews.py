#!/usr/bin/env python3
"""Иллюстрации для README из настоящих обоев, палитры, шрифтов и эмблемы темы.

Это не снимки экрана: личный рабочий стол в них не попадает.
Запуск из корня после build.py: python3 docs/make_previews.py
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build
import emblem

W, H = 1600, 900
FONTS = {"Handjet": "Handjet[ELGR,ELSH,wght].ttf", "Tektur": "Tektur[wdth,wght].ttf", "Exo 2": "Exo2[wght].ttf"}


def bundled(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ROOT / "fonts" / FONTS[name]), size)


def mono(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = subprocess.run(["fc-match", "-f", "%{file}", name], capture_output=True, text=True, check=True).stdout
    return ImageFont.truetype(path, size)


def tint(hex_color: str) -> tuple[int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def ring(d: ImageDraw.ImageDraw, x: int, y: int, r: int, part: float, t: dict, color: str, label: str, font) -> None:
    box = (x - r, y - r, x + r, y + r)
    d.arc(box, 0, 360, fill=tint(t["panel2"]), width=11)
    d.arc(box, -90, -90 + 360 * part, fill=tint(color), width=11)
    d.text((x, y), label, font=font, fill=tint(t["text"]), anchor="mm")


def picture(key: str, t: dict, wall: Path) -> Image.Image:
    im = Image.open(wall).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")
    title, code, ui = bundled(t["font_title"], 34), mono(t["font_mono"], 21), bundled("Exo 2", 20)
    gear = mono(":charset=2699", 21)

    x0, y0, x1, y1 = 130, 105, 1040, 735
    d.rectangle((x0, y0, x1, y1), fill=(*tint(t["bg"]), 240), outline=tint(t["line"]), width=2)
    d.rectangle((x0, y0, x1, y0 + 54), fill=tint(t["panel2"]))
    d.rectangle((x0, y0 + 52, x1, y0 + 54), fill=tint(t["accent"]))
    d.text((x0 + 22, y0 + 27), f"Когитатор — {t['title']}", font=title, fill=tint(t["text"]), anchor="lm")
    for i, c in enumerate((t["accent"], t["accent2"], t["muted"])):
        cx = x1 - 34 - i * 36
        d.polygon([(cx, y0 + 14), (cx + 12, y0 + 27), (cx, y0 + 40), (cx - 12, y0 + 27)], fill=tint(c))

    grid = emblem.dots()
    tones = {1: tint(t["accent"]), 2: tint(t["accent2"])}
    for gy, row in enumerate(grid):
        for gx, v in enumerate(row):
            if v:
                px, py = x0 + 34 + gx * 4, y0 + 86 + gy * 4
                d.rectangle((px, py, px + 2, py + 2), fill=tones[v])

    tx, ty = x0 + 420, y0 + 90
    rows = [("user@когитатор", t["link"]), ("──────────────", t["muted"]), ("Ядро   linux", t["text"]),
            ("Среда  KDE Plasma 6", t["text"]), ("Тема   " + t["title"], t["accent2"]),
            ("Значки " + t["scheme"], t["text"]), ("Шрифт  " + t["font_ui"], t["text"])]
    for i, (text, c) in enumerate(rows):
        d.text((tx, ty + i * 34), text, font=code, fill=tint(c))
    for i, c in enumerate(t["ansi"][:8]):
        d.rectangle((tx + i * 40, ty + 262, tx + i * 40 + 34, ty + 290), fill=tint(c))

    py = y0 + 455
    d.text((x0 + 34, py), t["greet"], font=code, fill=tint(t["accent"]))
    px = x0 + 34
    for text, c, face in (("user", t["link"], code), ("@когитатор ", t["muted"], code), ("~ ", t["accent2"], code),
                          ("⚙ ", t["accent"], gear), ("облачение " + t["arg"], t["accent2"], code)):
        d.text((px, py + 42), text, font=face, fill=tint(c))
        px += int(face.getlength(text))
    d.text((x0 + 34, py + 84), "Облачение: " + t["title"], font=code, fill=tint(t["text"]))

    px0, py0 = 1110, 105
    d.rectangle((px0, py0, 1500, 735), fill=(*tint(t["panel"]), 230), outline=tint(t["line"]), width=2)
    d.text((px0 + 195, py0 + 42), "Литания", font=title, fill=tint(t["accent2"]), anchor="mm")
    small = bundled("Exo 2", 24)
    ring(d, px0 + 105, py0 + 180, 72, .42, t, t["accent"], "ЦП", small)
    ring(d, px0 + 285, py0 + 180, 72, .64, t, t["link"], "ГП", small)
    ring(d, px0 + 195, py0 + 370, 72, .35, t, t["accent2"], "ОЗУ", small)
    d.text((px0 + 195, py0 + 505), "Значения для примера", font=ui, fill=tint(t["muted"]), anchor="mm")

    d.rectangle((0, H - 58, W, H), fill=(*tint(t["panel"]), 245))
    d.rectangle((0, H - 58, W, H - 56), fill=tint(t["line"]))
    d.text((W - 26, H - 29), "20:26", font=ui, fill=tint(t["text"]), anchor="rm")
    d.text((26, H - 29), "⚙", font=gear, fill=tint(t["accent"]), anchor="lm")
    return im


def main() -> None:
    for key, t in json.loads((build.OUT / "palette.json").read_text(encoding="utf8")).items():
        t["arg"] = t.get("arg", key)
        path = ROOT / "docs" / f"preview-{key}.jpg"
        picture(key, t, build.OUT / f"wallpapers/{key}.jpg").save(path, quality=88)
        print(path)


if __name__ == "__main__":
    main()
