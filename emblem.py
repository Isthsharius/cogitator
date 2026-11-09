"""Эмблема для fastfetch и neofetch: книга с рогатым ликом на звезде хаоса, символами Брайля."""
import io
import subprocess

from PIL import Image

COLS, ROWS = 44, 22
DOT_W, DOT_H = COLS * 2, ROWS * 4
SS = 6
RED, BRASS, CUT = "#ff0000", "#00ff00", "#000000"


def arm(angle: float) -> str:
    shaft = '<rect x="-4.5" y="-82" width="9" height="82"/>'
    head = '<path d="M0-99 19-66 7-72 0-70-7-72-19-66Z"/>'
    return f'<g transform="translate(100 100) rotate({angle})" fill="{RED}">{shaft}{head}</g>'


def mirror(body: str) -> str:
    return body + f'<g transform="translate(200 0) scale(-1 1)">{body}</g>'


def art() -> str:
    arms = "".join(arm(i * 45) for i in range(8))
    book_shape = "M100 156C82 142 60 140 34 148V68C60 60 84 62 100 76Z"
    page = (f'<path d="{book_shape}" fill="{CUT}" stroke="{BRASS}" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="M44 80C58 76 70 76 78 78M44 92H66M44 104H62M44 116H62M44 128C58 124 72 124 84 130" '
            f'fill="none" stroke="{BRASS}" stroke-width="3.2"/>')
    horn = f'<path d="M80 68C60 66 52 40 72 6 69 34 78 46 94 54Z" fill="{BRASS}"/>'
    horn_cut = '<path d="M80 68C60 66 52 40 72 6 69 34 78 46 94 54Z" fill="none" stroke="#000" stroke-width="7"/>'
    head = "M70 58 84 50 100 58 116 50 130 58 138 84 124 90 122 118 110 144 100 152 90 144 78 118 76 90 62 84Z"
    eye = f'<path d="M71 72 98 88 93 101 79 97Z" fill="{CUT}"/>'
    teeth = f'<path d="M82 113 91 134 100 118 109 134 118 113Z" fill="{BRASS}"/>'
    mouth = f'<path d="M76 108Q100 120 124 108L111 142 100 148 89 142Z" fill="{CUT}"/>'
    nose = f'<path d="M100 94 93 106H107Z" fill="{CUT}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect width="200" height="200" fill="#000"/>'
            f'{arms}{mirror(page)}{mirror(horn_cut)}'
            f'<path d="{head}" fill="none" stroke="#000" stroke-width="9"/>'
            f'{mirror(horn)}<path d="{head}" fill="{BRASS}"/>{mirror(eye)}{nose}{mouth}{teeth}</svg>')


def dots() -> list[list[int]]:
    """Сетка точек: 0 пусто, 1 звезда, 2 книга и лик."""
    png = subprocess.run(["rsvg-convert", "-w", str(DOT_W * SS), "-h", str(DOT_H * SS)],
                         input=art().encode(), capture_output=True, check=True).stdout
    im = Image.open(io.BytesIO(png)).convert("RGB")
    raw = im.tobytes()
    grid = []
    for y in range(DOT_H):
        row = []
        for x in range(DOT_W):
            r = g = 0
            for sy in range(y * SS, (y + 1) * SS):
                for sx in range(x * SS, (x + 1) * SS):
                    i = (sy * DOT_W * SS + sx) * 3
                    r += raw[i] > 127
                    g += raw[i + 1] > 127
            on = r + g > SS * SS * 0.45
            row.append(0 if not on else (2 if g >= r else 1))
        grid.append(row)
    return grid


BITS = (0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80)


def text(c1: str, c2: str) -> str:
    grid = dots()
    lines = []
    for row in range(ROWS):
        line, current = "", ""
        for col in range(COLS):
            cell = [grid[row * 4 + j][col * 2 + i] for j in range(4) for i in range(2)]
            mask = sum(b for v, b in zip(cell, BITS, strict=True) if v)
            if not mask:
                line += " "
                continue
            tone = c2 if cell.count(2) >= cell.count(1) else c1
            if tone != current:
                line += tone
                current = tone
            line += chr(0x2800 + mask)
        lines.append(line.rstrip())
    return "\n".join(lines) + "\n"


def preview(path: str) -> None:
    grid = dots()
    im = Image.new("RGB", (DOT_W, DOT_H), (11, 8, 6))
    tones = {1: (224, 40, 30), 2: (192, 138, 62)}
    for y, row in enumerate(grid):
        for x, v in enumerate(row):
            if v:
                im.putpixel((x, y), tones[v])
    im.resize((DOT_W * 8, DOT_H * 8), Image.Resampling.NEAREST).save(path)
