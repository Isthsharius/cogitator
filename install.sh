#!/usr/bin/env bash
# Установка Cogitator одной командой. Флаги: --no-deps, --look кузня|скрапкод, --no-apply
set -euo pipefail
cd "$(dirname "$(realpath "$0")")"

look=кузня apply=1 deps=1
while (($#)); do
    case "$1" in
        --no-deps) deps=0 ;;
        --no-apply) apply=0 ;;
        --look) look=${2:?укажите кузня или скрапкод}; shift ;;
        *) echo "Неизвестный флаг: $1" >&2; exit 2 ;;
    esac
    shift
done
[[ $look == кузня || $look == скрапкод ]] || { echo 'Оформление: кузня или скрапкод' >&2; exit 2; }
[[ $EUID -ne 0 ]] || { echo 'Запускайте от своего пользователя, без sudo' >&2; exit 1; }

major=$(plasmashell --version 2>/dev/null | grep -oE '[0-9]+' | head -n1 || true)
[[ $major == 6 ]] || { echo "Нужен KDE Plasma 6, найдено: ${major:-нет Plasma}" >&2; exit 1; }

arch_pkgs=(fish imagemagick gettext librsvg python-pillow libnotify networkmanager
           ghostty btop fastfetch ttf-jetbrains-mono-nerd ttf-firacode-nerd ttf-ibm-plex)
if ((deps)) && command -v pacman >/dev/null; then
    missing=()
    for p in "${arch_pkgs[@]}"; do pacman -Q "$p" >/dev/null 2>&1 || missing+=("$p"); done
    if ((${#missing[@]})); then
        echo "Будут установлены пакеты: ${missing[*]}"
        sudo pacman -S --needed "${missing[@]}"
    fi
fi

problems=()
for tool in fish magick rsvg-convert python3 notify-send kreadconfig6 kwriteconfig6 plasma-apply-colorscheme; do
    command -v "$tool" >/dev/null || problems+=("программа $tool")
done
python3 -c 'import PIL' 2>/dev/null || problems+=('модуль Python Pillow')
if ((${#problems[@]})); then
    printf 'Не хватает:\n'; printf '  - %s\n' "${problems[@]}"
    echo 'Установите их средствами своего дистрибутива и запустите снова.' >&2
    exit 1
fi
for font in 'JetBrainsMono Nerd Font' 'FiraCode Nerd Font' 'IBM Plex Sans'; do
    fc-list "$font" | grep -q . || echo "Предупреждение: нет шрифта $font, текст будет другим"
done
for tool in ghostty btop fastfetch nmcli; do
    command -v "$tool" >/dev/null || echo "Предупреждение: нет $tool, его оформление не будет видно"
done

python3 build.py
out=${XDG_CACHE_HOME:-$HOME/.cache}/cogitator-theme/build
fish "$out/install.fish"
if ((apply)); then
    fish -c "облачение $look"
fi
cat <<MSG

Готово. Откройте новый терминал fish.
Смена оформления: облачение кузня | облачение скрапкод
Проверка: облачение --проверка
Откат: вернуть-облик
Виджеты «Литания» и «Облачение» добавляются вручную: правый клик по панели → «Добавить виджеты».
MSG
