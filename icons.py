"""Значки папок «Сигил» для обеих тем; рисунок повторяет макет."""
from pathlib import Path

BACK = "M6 13H25L30 19H58V54H6Z"
FRONT = "M6 24H58V54H6Z"
CX, CY = 32, 39
ARC4 = "A4 4 0 1 1-4 0A4 4 0 1 1 4 0"

GLYPHS = {
    "generic": "M0-9V9M-9 0H9M-6.4-6.4 6.4 6.4M6.4-6.4-6.4 6.4",
    "desktop": "M-9-8H9V4H-9ZM0 4V8M-5 8H5",
    "download": "M0-8V5M-5 0 0 6 5 0M-7 9H7",
    "documents": "M-6-9H3L6-6V9H-6ZM-3-3H3M-3 1H3M-3 5H2",
    "pictures": "M-9-7H9V7H-9ZM-9 5-3-2 1 2 4-1 9 5M4-4H4.1",
    "development": f"M4 0{ARC4}M0-9V-5M0 5V9M-9 0H-5M5 0H9"
                   "M-6-6-3.5-3.5M3.5 3.5 6 6M6-6 3.5-3.5M-3.5 3.5-6 6",
    "music": "M-3 6V-7L7-9V4M-3 6A3 3 0 1 1-9 6A3 3 0 1 1-3 6M7 4A3 3 0 1 1 1 4A3 3 0 1 1 7 4",
    "video": "M-9-6H9V6H-9ZM-3-3V3L3 0Z",
    "home": "M-9 0 0-8 9 0M-6-2V8H6V-2M-2 8V3H2V8",
}
SPECIFIC = {
    "desktop": ["folder-desktop", "user-desktop"],
    "download": ["folder-download", "folder-downloads"],
    "documents": ["folder-documents", "folder-text", "folder-txt", "folder-notes"],
    "pictures": ["folder-pictures", "folder-picture", "folder-images", "folder-image"],
    "development": ["folder-development", "folder-script", "folder-git", "folder-build"],
    "music": ["folder-music", "folder-sound"],
    "video": ["folder-video", "folder-videos"],
    "home": ["user-home", "folder-home"],
}
COLOURED = {"black", "blue", "brown", "cyan", "green", "grey", "magenta",
            "orange", "red", "violet", "yellow"}
START_ICONS = ["start-here", "start-here-kde", "start-here-kde-plasma", "start-here-symbolic",
               "start-here-kde-symbolic", "start-here-kde-plasma-symbolic", "cachyos"]
BREEZE_PLACES = Path("/usr/share/icons/breeze-dark/places/64")


def glyph(d: str, stroke: str, width: float, scale: float, opacity: float = 1) -> str:
    return (f'<g transform="translate({CX} {CY}) scale({scale})"><path d="{d}" fill="none" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="square" '
            f'stroke-opacity="{opacity}"/></g>')


def large(d: str, t: dict) -> str:
    a = t["accent"]
    ticks = "".join(
        f'<path d="M0-14.5V-12" transform="translate({CX} {CY}) rotate({i * 45})" '
        f'stroke="{a}" stroke-width="1.5" fill="none"/>' for i in range(8))
    return (f'<path d="{BACK}" fill="{t["panel"]}"/>'
            f'<path d="{FRONT}" fill="{t["bg"]}" stroke="{a}" stroke-width="1.5"/>'
            f'<circle cx="{CX}" cy="{CY}" r="11.5" fill="none" stroke="{a}" stroke-width="4" stroke-opacity=".22"/>'
            + glyph(d, a, 5, 0.72, 0.22)
            + f'<circle cx="{CX}" cy="{CY}" r="11.5" fill="none" stroke="{a}" stroke-width="1.3"/>'
            + ticks + glyph(d, a, 1.9, 0.72))


def small(d: str, t: dict) -> str:
    a = t["accent"]
    return (f'<path d="{BACK}" fill="{t["panel2"]}"/>'
            f'<path d="{FRONT}" fill="{t["bg"]}" stroke="{a}" stroke-width="3"/>'
            + glyph(d, a, 2.6, 1.1))


def sigil(t: dict) -> str:
    """Знак меню из макета."""
    a = t["accent"]
    rays = "".join(f'<path d="M0-15V-43M-5-36 0-44 5-36" transform="rotate({i * 45})"/>' for i in range(8))
    teeth = "".join(f'<rect x="-2.5" y="-21" width="5" height="6" fill="{a}" stroke="none" '
                    f'transform="rotate({j * 30 + 15})"/>' for j in range(12))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-50 -50 100 100" fill="none" stroke="{a}" '
            f'stroke-width="2.6" stroke-linecap="square"><circle r="47" stroke-width="1.8"/><circle r="15"/>'
            f'{rays}{teeth}<circle r="4" fill="{a}" stroke="none"/></svg>\n')


def svg(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{body}</svg>\n'


def names() -> dict[str, str]:
    table = {"folder": "generic", "folder-open": "generic", "inode-directory": "generic"}
    for p in BREEZE_PLACES.glob("folder-*.svg"):
        if p.stem.removeprefix("folder-") not in COLOURED:
            table[p.stem] = "generic"
    for kind, items in SPECIFIC.items():
        for name in items:
            table[name] = kind
    return table


INDEX = """[Icon Theme]
Name={name}
Comment=Папки Сигил
Inherits=breeze-dark,hicolor
Example=folder
Directories=small/places,small/mimetypes,scalable/places,scalable/mimetypes,scalable/apps

[small/places]
Size=22
MinSize=8
MaxSize=31
Context=Places
Type=Scalable

[small/mimetypes]
Size=22
MinSize=8
MaxSize=31
Context=MimeTypes
Type=Scalable

[scalable/places]
Size=64
MinSize=32
MaxSize=1024
Context=Places
Type=Scalable

[scalable/mimetypes]
Size=64
MinSize=32
MaxSize=1024
Context=MimeTypes
Type=Scalable

[scalable/apps]
Size=64
MinSize=8
MaxSize=1024
Context=Applications
Type=Scalable
"""


def build(out: Path, themes: dict) -> None:
    table = names()
    for t in themes.values():
        root = out / t["scheme"]
        for size, draw in (("small", small), ("scalable", large)):
            for ctx in ("places", "mimetypes"):
                (root / size / ctx).mkdir(parents=True)
            for name, kind in table.items():
                ctx = "mimetypes" if name == "inode-directory" else "places"
                (root / size / ctx / f"{name}.svg").write_text(svg(draw(GLYPHS[kind], t)))
        (root / "scalable/apps").mkdir()
        for name in START_ICONS:
            (root / "scalable/apps" / f"{name}.svg").write_text(sigil(t))
        (root / "index.theme").write_text(INDEX.format(name=t["scheme"]))
