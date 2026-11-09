"""Рамки окон из макета: заголовок, контур, свечение активного окна, ромбовидные кнопки."""
import math
from pathlib import Path

PAD, EDGE, TITLE = 12, 2, 28
LEFT = PAD + EDGE
TOP = PAD + EDGE + TITLE + 1
MID = 8  # ширина и высота растягиваемых частей


def rgb(h: str) -> str:
    return ",".join(str(int(h[i:i + 2], 16)) for i in (1, 3, 5))


def rect(x: float, y: float, w: float, h: float, fill: str, op: float = 1) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" fill-opacity="{op:.3f}"/>'


def glow_alpha(dist: float, peak: float) -> float:
    return peak * max(0.0, 1 - dist / PAD) ** 2


def ramp(cells: int, peak: float) -> list[float]:
    return [glow_alpha(PAD - i - 0.5, peak) for i in range(cells)]


def slices(prefix: str, glow: str, peak: float, frame: str, t: dict) -> str:
    bg = t["panel2"]
    line = t["line"]
    out = []

    def element(name: str, x: int, y: int, w: int, h: int, body: str) -> None:
        out.append(f'<g id="{prefix}{name}" transform="translate({x} {y})">'
                   + rect(0, 0, w, h, "#000", 0) + body + '</g>')

    def h_edge(flip: bool) -> str:
        """Полоса свечения над или под окном, снаружи внутрь."""
        total = TOP if not flip else LEFT
        parts = []
        for i, a in enumerate(ramp(PAD, peak)):
            parts.append(rect(0, total - 1 - i if flip else i, MID, 1, glow, a))
        return "".join(parts)

    def v_edge(flip: bool) -> str:
        parts = []
        for i, a in enumerate(ramp(PAD, peak)):
            parts.append(rect(LEFT - 1 - i if flip else i, 0, 1, MID, glow, a))
        parts.append(rect(0 if flip else PAD, 0, EDGE, MID, frame))
        return "".join(parts)

    def corner(sx: int, sy: int, height: int) -> str:
        parts = []
        cx = PAD if sx > 0 else LEFT - PAD
        cy = PAD if sy > 0 else height - PAD
        for py in range(height if sy > 0 and height == PAD else min(height, PAD) if sy > 0 else height):
            for px in range(LEFT):
                dx = max(0.0, (cx - px - 0.5) if sx > 0 else (px + 0.5 - cx))
                dy = max(0.0, (cy - py - 0.5) if sy > 0 else (py + 0.5 - cy))
                if dx == 0 and dy == 0:
                    continue
                a = glow_alpha(math.hypot(dx, dy), peak)
                if a > 0.004:
                    parts.append(rect(px, py, 1, 1, glow, a))
        return "".join(parts)

    def side_glow_rows(flip: bool) -> str:
        """Боковое свечение рядом с заголовком."""
        parts = []
        for i, a in enumerate(ramp(PAD, peak)):
            parts.append(rect(LEFT - 1 - i if flip else i, PAD, 1, TOP - PAD, glow, a))
        return "".join(parts)

    def title_band(x: float, w: float) -> str:
        return (rect(x, PAD, w, EDGE, frame) + rect(x, PAD + EDGE, w, TITLE, bg)
                + rect(x, TOP - 1, w, 1, line))

    element("topleft", 0, 0, LEFT, TOP,
            corner(1, 1, PAD) + side_glow_rows(False) + title_band(PAD, EDGE)
            + rect(PAD, PAD, EDGE, TOP - PAD, frame))
    element("top", 40, 0, MID, TOP, h_edge(False) + title_band(0, MID))
    element("topright", 60, 0, LEFT, TOP,
            corner(-1, 1, PAD) + side_glow_rows(True) + title_band(0, EDGE)
            + rect(0, PAD, EDGE, TOP - PAD, frame))
    element("left", 0, 60, LEFT, MID, v_edge(False))
    element("center", 40, 60, MID, MID, rect(0, 0, MID, MID, t["panel"]))
    element("right", 60, 60, LEFT, MID, v_edge(True))
    bottom_rows = "".join(rect(0, LEFT - 1 - i, MID, 1, glow, a) for i, a in enumerate(ramp(PAD, peak)))
    element("bottomleft", 0, 80, LEFT, LEFT,
            corner(1, -1, LEFT) + rect(PAD, 0, EDGE, EDGE, frame))
    element("bottom", 40, 80, MID, LEFT, bottom_rows + rect(0, 0, MID, EDGE, frame))
    element("bottomright", 60, 80, LEFT, LEFT,
            corner(-1, -1, LEFT) + rect(0, 0, EDGE, EDGE, frame))
    return "".join(out)


def svg(body: str, size: int = 100) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">{body}</svg>\n')


def diamond(stroke: str, fill: str = "none") -> str:
    return (f'<path d="M9 3.5 14.5 9 9 14.5 3.5 9Z" fill="{fill}" stroke="{stroke}" '
            'stroke-width="1.5"/>')


def button(states: dict[str, str]) -> str:
    return svg("".join(
        f'<g id="{name}" transform="translate({i * 20} 0)">'
        f'<rect width="18" height="18" fill="#000" fill-opacity="0"/>{body}</g>'
        for i, (name, body) in enumerate(states.items())))


def rc(t: dict) -> str:
    return f"""[General]
ActiveTextColor={rgb(t["text"])}
InactiveTextColor={rgb(t["muted"])}
TitleAlignment=Left
TitleVerticalAlignment=Center
Animation=0

[Layout]
BorderLeft={EDGE}
BorderRight={EDGE}
BorderBottom={EDGE}
TitleEdgeTop={EDGE}
TitleEdgeBottom=1
TitleEdgeLeft={EDGE}
TitleEdgeRight={EDGE}
TitleBorderLeft=8
TitleBorderRight=8
TitleHeight={TITLE}
ButtonWidth=18
ButtonHeight=18
ButtonSpacing=4
ButtonMarginTop=5
PaddingTop={PAD}
PaddingBottom={PAD}
PaddingLeft={PAD}
PaddingRight={PAD}
"""


def build(out: Path, themes: dict) -> None:
    for t in themes.values():
        root = out / t["scheme"]
        root.mkdir(parents=True)
        name = t["scheme"]
        (root / "metadata.desktop").write_text(
            f"[Desktop Entry]\nName={t['title']}\nComment=Рамки Когитатора\n"
            f"X-KDE-PluginInfo-Name={name}\nX-KDE-PluginInfo-Version=1.0\n"
            "X-KDE-ServiceTypes=KWin/AuroraeTheme\n")
        (root / f"{name}rc").write_text(rc(t))
        (root / "decoration.svg").write_text(svg(
            slices("decoration-", t["accent"], 0.42, t["accent"], t)
            + f'<g transform="translate(0 110)">{slices("decoration-inactive-", "#000000", 0.35, t["line"], t)}</g>',
            240))
        base = {"active-center": diamond(t["muted"]), "inactive-center": diamond(t["line"]),
                "hover-center": diamond(t["accent2"]), "pressed-center": diamond(t["accent2"], t["accent2"]),
                "deactivated-center": diamond(t["line"])}
        close = dict(base)
        close["active-center"] = diamond(t["accent"], t["accent"])
        close["hover-center"] = diamond(t["err"], t["err"])
        for b in ("minimize", "maximize", "restore"):
            (root / f"{b}.svg").write_text(button(base))
        (root / "close.svg").write_text(button(close))
