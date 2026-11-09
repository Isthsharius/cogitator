#!/usr/bin/env python3
"""Палитра Когитатора вне KDE: Alacritty, Konsole, VS Code.

Запуск: apps.py apply forge|scrapcode или apps.py revert.
Прежние значения сохраняются один раз в pre-state/apps и возвращаются при откате.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HOME = Path.home()
PALETTE = HOME / ".local/share/cogitator/palette.json"
PRE = HOME / ".local/share/cogitator-theme/pre-state/apps"
ALACRITTY = HOME / ".config/alacritty/alacritty.toml"
KONSOLE_DIR = HOME / ".local/share/konsole"
VSCODE = HOME / ".config/Code/User/settings.json"
PROFILE = "Cogitator.profile"
VSCODE_KEY = "workbench.colorCustomizations"
ANSI_NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
VSCODE_ANSI = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]
HEADER = re.compile(r"^\s*\[([^\[\]]+)\]\s*(#.*)?$")


def rgb(color: str) -> str:
    c = color.lstrip("#")
    return ",".join(str(int(c[i:i + 2], 16)) for i in (0, 2, 4))


def atomic_write(path: Path, text: str) -> None:
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def split_color_sections(text: str) -> tuple[str, str]:
    """Разделить TOML на (всё прочее, секции [colors.*]); секция [colors] остаётся в прочем."""
    rest: list[str] = []
    colors: list[str] = []
    target = rest
    for line in text.splitlines(keepends=True):
        match = HEADER.match(line)
        if match:
            target = colors if match.group(1).strip().startswith("colors.") else rest
        target.append(line)
    return "".join(rest), "".join(colors)


def alacritty_colors(t: dict) -> str:
    def hx(c: str) -> str:
        return f'"0x{c.lstrip("#")}"'

    def block(name: str, offset: int) -> str:
        rows = "".join(f"{n} = {hx(t['ansi'][offset + i])}\n" for i, n in enumerate(ANSI_NAMES))
        return f"[colors.{name}]\n{rows}\n"

    return (f"[colors.primary]\nbackground = {hx(t['bg'])}\nforeground = {hx(t['text'])}\n\n"
            f"[colors.cursor]\ntext = {hx(t['bg'])}\ncursor = {hx(t['accent'])}\n\n"
            f"[colors.selection]\ntext = {hx(t['bg'])}\nbackground = {hx(t['accent'])}\n\n"
            + block("normal", 0) + block("bright", 8))


def konsole_scheme(t: dict) -> str:
    def sec(name: str, color: str) -> str:
        return f"[{name}]\nColor={rgb(color)}\n\n"

    out = sec("Background", t["bg"]) + sec("BackgroundFaint", t["bg"]) + sec("BackgroundIntense", t["panel"])
    for i in range(8):
        out += sec(f"Color{i}", t["ansi"][i]) + sec(f"Color{i}Faint", t["ansi"][i])
        out += sec(f"Color{i}Intense", t["ansi"][i + 8])
    out += sec("Foreground", t["text"]) + sec("ForegroundFaint", t["muted"])
    out += sec("ForegroundIntense", t["ansi"][15])
    return out + f"[General]\nDescription=Cogitator {t['title']}\nOpacity=0.92\nWallpaper=\n"


def konsole_profile(t: dict) -> str:
    return f"[Appearance]\nColorScheme={t['scheme']}\n\n[General]\nName=Cogitator\nParent=FALLBACK/\n"


def vscode_colors(t: dict) -> dict[str, str]:
    colors = {
        "foreground": t["text"], "errorForeground": t["err"], "focusBorder": t["accent"],
        "textLink.foreground": t["link"], "editor.background": t["bg"], "editor.foreground": t["text"],
        "editor.selectionBackground": t["accent"] + "66", "editorCursor.foreground": t["accent"],
        "editorLineNumber.foreground": t["line"], "editorLineNumber.activeForeground": t["accent2"],
        "editorGroupHeader.tabsBackground": t["panel"], "editorWidget.background": t["panel"],
        "activityBar.background": t["panel"], "activityBar.foreground": t["accent2"],
        "activityBar.inactiveForeground": t["muted"],
        "activityBarBadge.background": t["accent"], "activityBarBadge.foreground": t["bg"],
        "sideBar.background": t["panel"], "sideBar.foreground": t["text"],
        "sideBarTitle.foreground": t["accent2"],
        "statusBar.background": t["panel2"], "statusBar.foreground": t["text"],
        "titleBar.activeBackground": t["panel2"], "titleBar.activeForeground": t["text"],
        "titleBar.inactiveBackground": t["panel"], "titleBar.inactiveForeground": t["muted"],
        "tab.activeBackground": t["bg"], "tab.activeForeground": t["text"],
        "tab.activeBorderTop": t["accent"], "tab.inactiveBackground": t["panel"],
        "tab.inactiveForeground": t["muted"], "panel.background": t["bg"], "panel.border": t["line"],
        "button.background": t["accent"], "button.foreground": t["bg"],
        "input.background": t["panel2"], "input.foreground": t["text"], "dropdown.background": t["panel2"],
        "list.activeSelectionBackground": t["accent"], "list.activeSelectionForeground": t["bg"],
        "list.hoverBackground": t["panel2"],
        "terminal.background": t["bg"], "terminal.foreground": t["text"],
    }
    for i, name in enumerate(VSCODE_ANSI):
        colors[f"terminal.ansi{name}"] = t["ansi"][i]
        colors[f"terminal.ansiBright{name}"] = t["ansi"][i + 8]
    return colors


def apply_alacritty(t: dict) -> None:
    if not ALACRITTY.exists():
        print("Alacritty: конфига нет, пропущено")
        return
    text = ALACRITTY.read_text(encoding="utf-8")
    saved = PRE / "alacritty.toml"
    if not saved.exists():
        saved.write_text(text, encoding="utf-8")
    rest, _ = split_color_sections(text)
    updated = rest.rstrip("\n") + "\n\n" + alacritty_colors(t)
    tomllib.loads(updated)
    atomic_write(ALACRITTY, updated)


def revert_alacritty() -> None:
    saved = PRE / "alacritty.toml"
    if not (saved.exists() and ALACRITTY.exists()):
        return
    rest, _ = split_color_sections(ALACRITTY.read_text(encoding="utf-8"))
    _, colors = split_color_sections(saved.read_text(encoding="utf-8"))
    updated = rest.rstrip("\n") + "\n\n" + colors
    tomllib.loads(updated)
    atomic_write(ALACRITTY, updated)


def konsole_default(*extra: str) -> list[str]:
    return ["--file", "konsolerc", "--group", "Desktop Entry", "--key", "DefaultProfile", *extra]


def apply_konsole(palette: dict, key: str) -> None:
    KONSOLE_DIR.mkdir(parents=True, exist_ok=True)
    saved = PRE / "konsole-default"
    if not saved.exists():
        current = subprocess.run(["kreadconfig6", *konsole_default()], capture_output=True, text=True,
                                 timeout=10, check=True).stdout.strip()
        saved.write_text(current, encoding="utf-8")
    for t in palette.values():
        atomic_write(KONSOLE_DIR / f"{t['scheme']}.colorscheme", konsole_scheme(t))
    atomic_write(KONSOLE_DIR / PROFILE, konsole_profile(palette[key]))
    subprocess.run(["kwriteconfig6", *konsole_default(PROFILE)], timeout=10, check=True)


def revert_konsole(palette: dict) -> None:
    saved = PRE / "konsole-default"
    if not saved.exists():
        return
    previous = saved.read_text(encoding="utf-8").strip()
    args = konsole_default(previous) if previous else konsole_default("--delete")
    subprocess.run(["kwriteconfig6", *args], timeout=10, check=True)
    (KONSOLE_DIR / PROFILE).unlink(missing_ok=True)
    for t in palette.values():
        (KONSOLE_DIR / f"{t['scheme']}.colorscheme").unlink(missing_ok=True)


def load_vscode() -> dict | None:
    if not VSCODE.exists():
        return None
    try:
        data = json.loads(VSCODE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("VS Code: settings.json содержит комментарии или ошибку, пропущено")
        return None
    return data if isinstance(data, dict) else None


def apply_vscode(t: dict) -> None:
    data = load_vscode()
    if data is None:
        return
    saved = PRE / "vscode-colors.json"
    if not saved.exists():
        saved.write_text(json.dumps({"value": data.get(VSCODE_KEY)}, ensure_ascii=False), encoding="utf-8")
    data[VSCODE_KEY] = vscode_colors(t)
    atomic_write(VSCODE, json.dumps(data, ensure_ascii=False, indent=4) + "\n")


def revert_vscode() -> None:
    saved = PRE / "vscode-colors.json"
    data = load_vscode()
    if data is None or not saved.exists():
        return
    value = json.loads(saved.read_text(encoding="utf-8"))["value"]
    if value is None:
        data.pop(VSCODE_KEY, None)
    else:
        data[VSCODE_KEY] = value
    atomic_write(VSCODE, json.dumps(data, ensure_ascii=False, indent=4) + "\n")


def main(argv: list[str]) -> int:
    palette = json.loads(PALETTE.read_text(encoding="utf-8"))
    PRE.mkdir(parents=True, exist_ok=True)
    if len(argv) == 3 and argv[1] == "apply" and argv[2] in palette:
        t = palette[argv[2]]
        apply_alacritty(t)
        apply_konsole(palette, argv[2])
        apply_vscode(t)
        return 0
    if len(argv) == 2 and argv[1] == "revert":
        revert_alacritty()
        revert_konsole(palette)
        revert_vscode()
        shutil.rmtree(PRE, ignore_errors=True)
        return 0
    print("Использование: apps.py apply forge|scrapcode | apps.py revert", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
