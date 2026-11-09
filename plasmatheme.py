"""Тема Plasma: всё берётся из Breeze, меняется только панель с линией цвета темы."""
import json
from pathlib import Path

STYLE = ('<style id="current-color-scheme" type="text/css">'
         '.ColorScheme-Background{color:#15100c}.ColorScheme-Highlight{color:#e0281e}</style>')


def part(name: str, x: int, y: int, w: int, h: int, cls: str, op: float) -> str:
    return (f'<rect id="{name}" x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}" '
            f'style="fill:currentColor;fill-opacity:{op}"/>')


def panel(op: float) -> str:
    bg, hi = "ColorScheme-Background", "ColorScheme-Highlight"
    body = "".join([
        part("topleft", 0, 0, 2, 2, hi, 1), part("top", 10, 0, 8, 2, hi, 1), part("topright", 26, 0, 2, 2, hi, 1),
        part("left", 0, 10, 2, 8, bg, op), part("center", 10, 10, 8, 8, bg, op), part("right", 26, 10, 2, 8, bg, op),
        part("bottomleft", 0, 26, 2, 2, bg, op), part("bottom", 10, 26, 8, 2, bg, op),
        part("bottomright", 26, 26, 2, 2, bg, op),
    ])
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">{STYLE}{body}</svg>\n'


def build(out: Path) -> None:
    root = out / "cogitator"
    for sub, op in (("widgets", 0.96), ("translucent/widgets", 0.96), ("opaque/widgets", 1.0)):
        (root / sub).mkdir(parents=True)
        (root / sub / "panel-background.svg").write_text(panel(op))
    meta = {"KPackageStructure": "Plasma/Theme", "X-Plasma-API": "5.0",
            "KPlugin": {"Id": "cogitator", "Name": "Когитатор", "Description": "Панель Когитатора", "Version": "1.0"}}
    (root / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
