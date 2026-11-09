#!/usr/bin/env python3
"""Проверка темы Когитатор: облачение --проверка. Код выхода 1 — есть поломки."""
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from pathlib import Path

import apps

HOME = Path.home()
STATE = HOME / ".config/cogitator/doctor.json"
CURRENT = HOME / ".config/cogitator/current"
QML_ROOTS = [Path("/usr/lib/qt6/qml"), Path("/usr/lib64/qt6/qml"), Path("/usr/lib/x86_64-linux-gnu/qt6/qml")]
QML_ROOT = next((p for p in QML_ROOTS if p.is_dir()), QML_ROOTS[0])
QML_MODULES = ["org/kde/plasma/plasmoid", "org/kde/plasma/plasma5support", "org/kde/ksysguard/sensors"]
PLASMOIDS = ["org.cogitator.litany", "org.cogitator.vestment"]
ERROR_WORDS = ("error", "is not installed", "is not a type", "cannot ", "failed to load")
OK, WARN, FAIL = "ok", "warn", "fail"
MARK = {OK: "✓", WARN: "!", FAIL: "✖"}
Check = tuple[str, str, str]


def run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def kread(file: str, group: str, key: str) -> str:
    return run("kreadconfig6", "--file", file, "--group", group, "--key", key)


def same(name: str, actual: str, expected: str) -> Check:
    if actual == expected:
        return name, OK, actual
    return name, FAIL, f"сейчас «{actual}», ожидается «{expected}»"


def exists(name: str, path: Path) -> Check:
    return (name, OK, "на месте") if path.exists() else (name, FAIL, f"нет {path}")


def plasmoid_errors(lines: list[str]) -> list[str]:
    found = []
    for line in lines:
        low = line.lower()
        if "org.cogitator" in low and any(word in low for word in ERROR_WORDS):
            found.append(line.strip())
    return found


def version_check(current: str, recorded: str | None) -> Check:
    if not current:
        return "Версия Plasma", WARN, "не удалось определить"
    if recorded is None or recorded == current:
        return "Версия Plasma", OK, current
    return "Версия Plasma", WARN, f"обновлена: {recorded} → {current}, проверьте виджеты на глаз"


def summarize(checks: list[Check]) -> int:
    for name, status, detail in checks:
        print(f" {MARK[status]} {name}: {detail}")
    fails = sum(1 for c in checks if c[1] == FAIL)
    warns = sum(1 for c in checks if c[1] == WARN)
    print(f"Итог: проверок {len(checks)}, поломок {fails}, предупреждений {warns}")
    return 1 if fails else 0


def check_kde(t: dict) -> list[Check]:
    scheme = t["scheme"]
    out = [
        same("Цветовая схема", kread("kdeglobals", "General", "ColorScheme"), scheme),
        same("Значки", kread("kdeglobals", "Icons", "Theme"), scheme),
        same("Курсор", kread("kcminputrc", "Mouse", "cursorTheme"), f"{scheme}Cursor"),
        same("Тема Plasma", kread("plasmarc", "Theme", "name"), "cogitator"),
        same("Рамки окон", kread("kwinrc", "org.kde.kdecoration2", "theme"), f"__aurorae__svg__{scheme}"),
        exists("Файл схемы", HOME / f".local/share/color-schemes/{scheme}.colors"),
        exists("Набор значков", HOME / f".local/share/icons/{scheme}"),
        exists("Набор курсоров", HOME / f".icons/{scheme}Cursor"),
        exists("Рамки Aurorae", HOME / f".local/share/aurorae/themes/{scheme}"),
    ]
    gtk = HOME / ".config/gtk-3.0/colors.css"
    if not gtk.exists():
        out.append(("Цвета GTK", WARN, "нет colors.css"))
    elif t["bg"].lower() in gtk.read_text(encoding="utf-8").lower():
        out.append(("Цвета GTK", OK, "соответствуют теме"))
    else:
        out.append(("Цвета GTK", WARN, "не обновились, помогает повторное облачение"))
    return out


def check_fonts(t: dict) -> list[Check]:
    families = run("fc-list", ":", "family")
    out: list[Check] = []
    for font in (t["font_title"], t["font_ui"], t["font_mono"]):
        out.append((f"Шрифт {font}", OK, "установлен") if font in families else (f"Шрифт {font}", FAIL, "не найден"))
    return out


def check_plasmoids() -> list[Check]:
    out: list[Check] = []
    root = HOME / ".local/share/plasma/plasmoids"
    panel = HOME / ".config/plasma-org.kde.plasma.desktop-appletsrc"
    layout = panel.read_text(encoding="utf-8") if panel.exists() else ""
    for pid in PLASMOIDS:
        name = f"Виджет {pid.rsplit('.', 1)[1]}"
        try:
            json.loads((root / pid / "metadata.json").read_text(encoding="utf-8"))
            (root / pid / "contents/ui/main.qml").stat()
        except (OSError, json.JSONDecodeError) as err:
            out.append((name, FAIL, f"повреждён: {err}"))
            continue
        if f"plugin={pid}" in layout:
            out.append((name, OK, "установлен и размещён"))
        else:
            out.append((name, WARN, "установлен, но не добавлен на рабочий стол"))
    for module in QML_MODULES:
        out.append(exists(f"Модуль QML {module.rsplit('/', 1)[1]}", QML_ROOT / module))
    invocation = run("systemctl", "--user", "show", "plasma-plasmashell", "-p", "InvocationID", "--value")
    if invocation:
        log = run("journalctl", "--user", "--no-pager", "-o", "cat", f"_SYSTEMD_INVOCATION_ID={invocation}")
        errors = plasmoid_errors(log.splitlines())
        out.append(("Журнал виджетов", FAIL, errors[-1][:160]) if errors else ("Журнал виджетов", OK, "ошибок нет"))
    return out


def check_services() -> list[Check]:
    active = run("systemctl", "--user", "is-active", "cogitator-herald.service")
    out = [same("Вестник", active, "active")]
    state = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "cogitator/state"
    if not state.exists():
        out.append(("Живые состояния", FAIL, "вестник не пишет состояние"))
    else:
        age = time.time() - state.stat().st_mtime
        out.append(("Живые состояния", OK, "обновляются") if age < 60
                   else ("Живые состояния", FAIL, f"файл не обновлялся {round(age)} с"))
    return out


def check_terminal(key: str, t: dict) -> list[Check]:
    out = [
        exists("Команды fish", HOME / ".local/share/fish/vendor_functions.d/облачение.fish"),
        exists("Настройки fish", HOME / ".local/share/fish/vendor_conf.d/cogitator.fish"),
        exists("Тема btop", HOME / f".config/btop/themes/cogitator-{key}.theme"),
    ]
    ghostty = HOME / ".config/ghostty/config"
    current = HOME / ".config/cogitator/ghostty-current"
    if ghostty.exists() and "cogitator/ghostty-current" in ghostty.read_text(encoding="utf-8") and current.exists():
        tone = t["bg"] in current.read_text(encoding="utf-8")
        out.append(("Ghostty", OK if tone else FAIL, "соответствует теме" if tone else "другая палитра"))
    else:
        out.append(("Ghostty", FAIL, "тема не подключена"))
    return out


def check_apps(t: dict) -> list[Check]:
    out: list[Check] = []
    if apps.ALACRITTY.exists():
        try:
            cfg = tomllib.loads(apps.ALACRITTY.read_text(encoding="utf-8"))
            bg = cfg.get("colors", {}).get("primary", {}).get("background", "")
            out.append(same("Alacritty", bg.lower(), "0x" + t["bg"][1:].lower()))
        except tomllib.TOMLDecodeError as err:
            out.append(("Alacritty", FAIL, f"конфиг повреждён: {err}"))
    if shutil.which("konsole"):
        profile = apps.KONSOLE_DIR / apps.PROFILE
        text = profile.read_text(encoding="utf-8") if profile.exists() else ""
        out.append(("Konsole", OK, "соответствует теме") if f"ColorScheme={t['scheme']}" in text
                   else ("Konsole", FAIL, "профиль не подключён"))
    data = apps.load_vscode()
    if data is not None:
        applied = data.get(apps.VSCODE_KEY) == apps.vscode_colors(t)
        out.append(("VS Code", OK if applied else FAIL, "соответствует теме" if applied else "другие цвета"))
    return out


def load_state() -> dict:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    try:
        palette = json.loads(apps.PALETTE.read_text(encoding="utf-8"))
        key = CURRENT.read_text(encoding="utf-8").strip()
        t = palette[key]
    except (OSError, json.JSONDecodeError, KeyError) as err:
        print(f" ✖ Тема не определена: {err!r}")
        return 1
    print(f"Проверка облачения: {t['title']}")
    groups: list[Callable[[], list[Check]]] = [
        lambda: check_kde(t), lambda: check_fonts(t), check_plasmoids, check_services,
        lambda: check_terminal(key, t), lambda: check_apps(t),
    ]
    checks = [c for group in groups for c in group()]
    plasma = run("plasmashell", "--version").rsplit(" ", 1)[-1]
    checks.append(version_check(plasma, load_state().get("plasma")))
    code = summarize(checks)
    if code == 0 and plasma:
        apps.atomic_write(STATE, json.dumps({"plasma": plasma}) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
