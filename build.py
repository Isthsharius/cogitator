#!/usr/bin/env python3
"""Генератор темы Cogitator: один источник палитр, из него все конфиги."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import aurorae
import boot
import cursors
import emblem
import icons
import plasmatheme

OUT = Path("/var/tmp/cogitator-theme")
WALL_SRC = Path(os.environ.get("COGITATOR_WALLPAPER", Path(__file__).parent / "wallpaper.png"))
SIZE = "2560x1440"

THEMES = {
    "forge": {
        "title": "Кузня Марса", "scheme": "CogitatorForge", "arg": "кузня",
        "bg": "#0B0806", "panel": "#15100C", "panel2": "#211712", "line": "#5A3A1C",
        "accent": "#E0281E", "accent2": "#C08A3E", "text": "#E6CFA3", "muted": "#A8926F",
        "ok": "#4FD67A", "link": "#3FB8C4", "err": "#FF5A3C",
        "ansi": ["#15100C", "#E0281E", "#4FD67A", "#C08A3E", "#8A5A2B", "#B0432F", "#3FB8C4", "#E6CFA3",
                 "#8A6E4E", "#FF5A3C", "#7BE89B", "#E0B060", "#B5824A", "#D8694F", "#6FD4DE", "#F5E6C8"],
        "font_title": "Handjet", "font_mono": "JetBrainsMono Nerd Font", "font_ui": "IBM Plex Sans",
        "greet": "Кузня разогрета", "notfound": "Обряд неизвестен", "err_word": "",
        "done_ok": "Дух машины умиротворён", "done_err": "Скрапкод обнаружен",
        "modulate": None, "shader": "forge",
    },
    "scrapcode": {
        "title": "Скрапкод", "scheme": "CogitatorScrapcode", "arg": "скрапкод",
        "bg": "#050A07", "panel": "#0A130D", "panel2": "#102016", "line": "#1E4A2C",
        "accent": "#39E36B", "accent2": "#A8F03A", "text": "#B9F2C6", "muted": "#71A883",
        "ok": "#39E36B", "link": "#7CE8C8", "err": "#FF4A3D",
        "ansi": ["#0A130D", "#FF4A3D", "#39E36B", "#A8F03A", "#2FA06A", "#5FBF8F", "#7CE8C8", "#B9F2C6",
                 "#4F8A63", "#FF7468", "#6CF094", "#C6F86E", "#4FC98D", "#86D9AE", "#A6F2DC", "#E0FBE6"],
        "font_title": "Tektur", "font_mono": "FiraCode Nerd Font", "font_ui": "Exo 2",
        "greet": "Контур заражён. Продолжай", "notfound": "Сегмент повреждён", "err_word": " скрапкод",
        "done_ok": "Заражение завершено", "done_err": "Скрапкод обнаружен",
        "modulate": "82,90,164", "shader": "scrapcode",
    },
}


def w(rel: str, text: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def rgb(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def colors(t: dict) -> str:
    def sec(name, bg, alt, fg, fg_in):
        return f"""[Colors:{name}]
BackgroundAlternate={rgb(alt)}
BackgroundNormal={rgb(bg)}
DecorationFocus={rgb(t['accent'])}
DecorationHover={rgb(t['accent2'])}
ForegroundActive={rgb(t['accent2'])}
ForegroundInactive={rgb(fg_in)}
ForegroundLink={rgb(t['link'])}
ForegroundNegative={rgb(t['err'])}
ForegroundNeutral={rgb(t['accent2'])}
ForegroundNormal={rgb(fg)}
ForegroundPositive={rgb(t['ok'])}
ForegroundVisited={rgb(t['accent2'])}

"""
    out = ""
    out += sec("Button", t["panel2"], t["panel"], t["text"], t["muted"])
    out += sec("Complementary", t["bg"], t["panel"], t["text"], t["muted"])
    out += sec("Header", t["panel2"], t["panel"], t["text"], t["muted"])
    out += sec("Selection", t["accent"], t["accent"], t["bg"], t["panel2"])
    out += sec("Tooltip", t["panel"], t["panel2"], t["text"], t["muted"])
    out += sec("View", t["bg"], t["panel"], t["text"], t["muted"])
    out += sec("Window", t["panel"], t["panel2"], t["text"], t["muted"])
    out += f"""[General]
ColorScheme={t['scheme']}
Name=Cogitator {t['title']}
shadeSortColumn=true

[WM]
activeBackground={rgb(t['panel2'])}
activeBlend={rgb(t['accent'])}
activeForeground={rgb(t['text'])}
inactiveBackground={rgb(t['panel'])}
inactiveBlend={rgb(t['line'])}
inactiveForeground={rgb(t['muted'])}
"""
    return out


def ghostty(t: dict, key: str) -> str:
    lines = [f"palette = {i}={c}" for i, c in enumerate(t["ansi"])]
    return "\n".join([
        'font-family = ""',
        f"font-family = {t['font_mono']}",
        f"background = {t['bg']}",
        f"foreground = {t['text']}",
        f"cursor-color = {t['accent']}",
        f"selection-background = {t['accent']}",
        f"selection-foreground = {t['bg']}",
        "background-opacity = 0.92",
        f"custom-shader = @HOME@/.config/cogitator/shaders/{t['shader']}.glsl",
        "custom-shader-animation = " + ("true" if key == "scrapcode" else "false"),
        *lines, "",
    ])


SHADER_FORGE = """// Мягкое свечение яркого текста
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 px = 1.0 / iResolution.xy;
    vec4 base = texture(iChannel0, uv);
    vec3 glow = vec3(0.0);
    for (int i = 0; i < 8; i++) {
        float a = float(i) * 0.7853981;
        vec2 d = vec2(cos(a), sin(a)) * px * 2.5;
        vec3 s = texture(iChannel0, uv + d).rgb;
        glow += s * smoothstep(0.45, 1.0, max(s.r, max(s.g, s.b)));
    }
    fragColor = vec4(base.rgb + glow / 8.0 * 0.35, base.a);
}
"""

SHADER_SCRAP = """// Лёгкие строки развёртки и редкий короткий сбой
float rnd(float x) { return fract(sin(x * 91.17) * 43758.5453); }
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    float slot = floor(iTime * 2.0);
    if (rnd(slot) > 0.94 && fract(iTime * 2.0) < 0.12) {
        float band = floor(uv.y * 24.0);
        if (rnd(band + slot) > 0.75) uv.x += (rnd(band) - 0.5) * 0.012;
    }
    vec4 c = texture(iChannel0, uv);
    c.rgb *= 0.97 + 0.03 * sin(fragCoord.y * 3.14159);
    fragColor = c;
}
"""


def fastfetch(t: dict) -> str:
    def m(kind, key, **kw):
        return {"type": kind, "key": key, **kw}
    cfg = {
        "logo": {"type": "file", "source": "@HOME@/.local/share/cogitator/sigil.txt",
                 "color": {"1": t["accent"], "2": t["accent2"]}, "padding": {"right": 3}},
        "display": {"separator": "  ", "color": {"keys": t["accent2"]}, "key": {"width": 11}},
        "modules": [
            {"type": "custom", "format": "Манифест сосуда"},
            "break",
            m("os", "Литургия"), m("kernel", "Ядро"), m("de", "Облик"),
            m("cpu", "Потоки"), m("gpu", "Видение"), m("memory", "Память"),
            m("display", "Окуляры"), m("terminal", "Терминал"), "break", "colors",
        ],
    }
    return json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"


def btop(t: dict) -> str:
    m = {
        "main_bg": t["bg"], "main_fg": t["text"], "title": t["accent2"], "hi_fg": t["accent"],
        "selected_bg": t["accent"], "selected_fg": t["bg"], "inactive_fg": t["line"],
        "graph_text": t["muted"], "meter_bg": t["panel2"], "proc_misc": t["link"],
        "cpu_box": t["accent"], "mem_box": t["accent2"], "net_box": t["link"], "proc_box": t["line"],
        "div_line": t["line"],
        "temp_start": t["ok"], "temp_mid": t["accent2"], "temp_end": t["err"],
        "cpu_start": t["accent2"], "cpu_mid": t["accent"], "cpu_end": t["err"],
        "free_start": t["ok"], "free_mid": t["ok"], "free_end": t["ok"],
        "cached_start": t["link"], "cached_mid": t["link"], "cached_end": t["link"],
        "available_start": t["accent2"], "available_mid": t["accent2"], "available_end": t["accent2"],
        "used_start": t["accent"], "used_mid": t["accent"], "used_end": t["err"],
        "download_start": t["link"], "download_mid": t["ok"], "download_end": t["accent2"],
        "upload_start": t["accent2"], "upload_mid": t["accent"], "upload_end": t["err"],
    }
    return "".join(f'theme[{k}]="{v}"\n' for k, v in m.items())


def theme_vars(key: str, t: dict) -> str:
    return "\n".join([
        f"set -g cog_name '{t['title']}'",
        f"set -g cog_scheme {t['scheme']}",
        f"set -g cog_font_ui '{t['font_ui']}'",
        f"set -g cog_font_title '{t['font_title']}'",
        f"set -g cog_font_mono '{t['font_mono']}'",
        f"set -g cog_wall $HOME/.local/share/cogitator/wallpapers/{key}.jpg",
        f"set -g cog_btop cogitator-{key}",
        f"set -g cog_greet '{t['greet']}'",
        f"set -g cog_notfound '{t['notfound']}'",
        f"set -g cog_err_word '{t['err_word']}'",
        f"set -g cog_done_ok '{t['done_ok']}'",
        f"set -g cog_done_err '{t['done_err']}'",
        f"set -g cog_c_user {t['link'][1:]}",
        f"set -g cog_c_muted {t['muted'][1:]}",
        f"set -g cog_c_path {t['accent2'][1:]}",
        f"set -g cog_c_mark {t['accent'][1:]}",
        f"set -g cog_c_err {t['err'][1:]}",
        f"set -g cog_c_ok {t['ok'][1:]}",
        "",
    ])


FISH = {
    "__cog_load": r"""function __cog_load --description 'Загрузить параметры текущей темы'
    set -l t forge
    test -r ~/.config/cogitator/current; and read t < ~/.config/cogitator/current
    source ~/.local/share/cogitator/themes/$t.fish
end
""",
    "__cog_greeting": r"""function __cog_greeting
    __cog_load
    set_color $cog_c_mark; echo $cog_greet; set_color normal
end
""",
    "__cog_prompt": r"""function __cog_prompt
    set -l st $status
    __cog_load
    set_color $cog_c_user; printf '%s' $USER
    set_color $cog_c_muted; printf '@когитатор '
    set_color $cog_c_path; printf '%s ' (prompt_pwd)
    if test $st -ne 0
        set_color $cog_c_err; printf '✖ %s%s ' $st $cog_err_word
    else
        set_color $cog_c_mark; printf '⚙ '
    end
    set_color normal
end
""",
    "вернуть-облик": r"""function вернуть-облик --description 'Вернуть вид системы до темы'
    set -l pre ~/.local/share/cogitator-theme/pre-state
    if not test -f $pre/colorscheme
        echo 'Нет сохранённого состояния, откат невозможен' >&2
        return 1
    end
    __cog_confirm 'Вернуть прежний вид системы?'; or return 1
    read -l scheme < $pre/colorscheme
    plasma-apply-colorscheme $scheme
    test -f $pre/icontheme; and read icons < $pre/icontheme; and /usr/lib/plasma-changeicons $icons
    test -f $pre/cursor; and read cursor < $pre/cursor; and plasma-apply-cursortheme $cursor
    test -f $pre/plasmatheme; and read ptheme < $pre/plasmatheme; and plasma-apply-desktoptheme $ptheme
    python3 ~/.local/share/cogitator/apps.py revert
    systemctl --user disable --now cogitator-herald.service
    command rm -f ~/.config/systemd/user/cogitator-herald.service
    sudo rm -f /etc/sudoers.d/cogitator
    command rm -rf ~/.config/fastfetch
    test -f $pre/neofetch.conf; and command cp $pre/neofetch.conf ~/.config/neofetch/config.conf
    command rm -f ~/.local/share/locale/ru/LC_MESSAGES/kscreenlocker_greet.mo
    if string match -q 'Number=1' < $pre/desktops
        for id in (string match -rg '^Id_(?:[2-9]|[1-9][0-9]+)=(.+)$' < ~/.config/kwinrc)
            qdbus6 org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager.removeDesktop $id
        end
        qdbus6 org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager.setDesktopName (kreadconfig6 --file kwinrc --group Desktops --key Id_1) 'Рабочий стол 1'
    end
    kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.breeze
    kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme Breeze
    dbus-send --session --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure
    for key in font menuFont toolBarFont fixed
        kwriteconfig6 --file kdeglobals --group General --key $key --delete
    end
    kwriteconfig6 --file kdeglobals --group WM --key activeFont --delete
    systemctl --user stop plasma-plasmashell.service
    command cp $pre/plasma-org.kde.plasma.desktop-appletsrc ~/.config/
    systemctl --user start plasma-plasmashell.service
    sed -i '/\.config\/cogitator\/ghostty-current/d' ~/.config/ghostty/config
    pkill -USR2 -x ghostty
    test -f $pre/btop-created; and command rm -f ~/.config/btop/btop.conf
    command rm -f ~/.config/btop/themes/cogitator-forge.theme ~/.config/btop/themes/cogitator-scrapcode.theme
    command rm -f ~/.local/share/color-schemes/CogitatorForge.colors ~/.local/share/color-schemes/CogitatorScrapcode.colors
    command rm -rf ~/.local/share/fonts/cogitator ~/.local/share/cogitator ~/.config/cogitator
    command rm -rf ~/.local/share/icons/CogitatorForge ~/.local/share/icons/CogitatorScrapcode
    command rm -rf ~/.local/share/aurorae/themes/CogitatorForge ~/.local/share/aurorae/themes/CogitatorScrapcode
    command rm -rf ~/.icons/CogitatorForgeCursor ~/.icons/CogitatorScrapcodeCursor ~/.local/share/plasma/desktoptheme/cogitator
    command rm -rf ~/.local/share/plasma/plasmoids/org.cogitator.vestment ~/.local/share/plasma/plasmoids/org.cogitator.litany
    command rm -f ~/.local/share/fish/vendor_conf.d/cogitator.fish
    for name in (command cat $pre/fish-functions)
        command rm -f ~/.local/share/fish/vendor_functions.d/$name.fish
    end
    dbus-send --session --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure
    fc-cache -f
    echo 'Прежний вид возвращён. Открой новый терминал; лучше один раз перезайти в сессию.'
end
""",
    "__cog_notfound_handler": r"""function __cog_notfound_handler
    __cog_load
    set_color $cog_c_err; echo "$cog_notfound: $argv[1]" >&2; set_color normal
end
""",
    "обряд": r"""function обряд --description 'Обновить систему'
    __cog_load
    set_color $cog_c_path; echo ':: Обряд Обновления начат'; set_color normal
    sudo pacman -Syu $argv
    set -l st $status
    if test $st -eq 0
        set_color $cog_c_ok; echo $cog_done_ok
    else
        set_color $cog_c_err; echo "$cog_done_err: код $st"
    end
    set_color normal
    return $st
end
""",
    "__cog_confirm": r"""function __cog_confirm --argument-names question
    read -l -P "$question [да/нет] " ans
    contains -- (string lower -- "$ans") да д y yes
end
""",
    "бдение": r"""function бдение --description 'Выключить компьютер'
    __cog_confirm 'Начать бдение и выключить компьютер?'; or return 1
    systemctl poweroff
end
""",
    "перерождение": r"""function перерождение --description 'Перезагрузить компьютер'
    __cog_confirm 'Перезагрузить компьютер?'; or return 1
    systemctl reboot
end
""",
    "манифест": r"""function манифест --description 'Манифест сосуда'
    set -l t forge
    test -r ~/.config/cogitator/current; and read t < ~/.config/cogitator/current
    fastfetch -c ~/.config/cogitator/fastfetch/$t.jsonc $argv
end
""",
    "литания": r"""function литания --description 'Монитор системы'
    btop $argv
end
""",
    "очищение": r"""function очищение --description 'Почистить кэш пакетов и ненужные пакеты'
    echo ':: Устаревшие версии в кэше (останутся 2 последние):'
    paccache -dk2
    if __cog_confirm 'Удалить их?'
        sudo paccache -rk2
    end
    set -l orphans (pacman -Qdtq)
    if test (count $orphans) -eq 0
        echo ':: Ненужных пакетов нет'
        return 0
    end
    echo ':: Ненужные пакеты:'
    printf '  %s\n' $orphans
    if __cog_confirm 'Удалить эти пакеты?'
        sudo pacman -Rns $orphans
    end
end
""",
    "облачение": r"""function облачение --description 'Сменить тему: кузня или скрапкод'
    set -l t
    switch (string lower -- "$argv[1]")
        case кузня forge
            set t forge
        case скрапкод scrapcode
            set t scrapcode
        case проверка --проверка
            python3 ~/.local/share/cogitator/doctor.py
            return $status
        case ''
            set -l cur forge
            test -r ~/.config/cogitator/current; and read cur < ~/.config/cogitator/current
            test $cur = forge; and set t scrapcode; or set t forge
        case '*'
            echo 'Использование: облачение [кузня|скрапкод|--проверка]' >&2
            return 2
    end
    source ~/.local/share/cogitator/themes/$t.fish

    function __cog_run --no-scope-shadowing
        if set -q COGITATOR_DRY
            echo "[план] $argv"
        else
            $argv
        end
    end

    __cog_run plasma-apply-colorscheme $cog_scheme
    __cog_run plasma-apply-wallpaperimage $cog_wall
    __cog_run /usr/lib/plasma-changeicons $cog_scheme
    __cog_run plasma-apply-cursortheme {$cog_scheme}Cursor
    __cog_run plasma-apply-desktoptheme cogitator
    __cog_run cp ~/.config/cogitator/fastfetch/logo-$t.jsonc ~/.config/fastfetch/config.jsonc
    if test -f ~/.config/neofetch/config.conf
        set -l nf_color 1
        test $t = scrapcode; and set nf_color 2
        __cog_run sed -i "s|^ascii_colors=.*|ascii_colors=($nf_color 3)|" ~/.config/neofetch/config.conf
    end
    __cog_run kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.kwin.aurorae
    __cog_run kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme __aurorae__svg__$cog_scheme
    set -l tail ',10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1'
    for key in font menuFont toolBarFont
        __cog_run kwriteconfig6 --file kdeglobals --group General --key $key "$cog_font_ui$tail"
    end
    __cog_run kwriteconfig6 --file kdeglobals --group General --key fixed "$cog_font_mono$tail"
    __cog_run kwriteconfig6 --file kdeglobals --group WM --key activeFont "$cog_font_title,12,-1,5,500,0,0,0,0,0,0,0,0,0,0,1"
    __cog_run cp ~/.config/cogitator/ghostty/$t ~/.config/cogitator/ghostty-current
    __cog_run pkill -USR2 -x ghostty
    __cog_run python3 ~/.local/share/cogitator/apps.py apply $t
    if test -f ~/.config/btop/btop.conf
        __cog_run sed -i "s|^color_theme = .*|color_theme = \"$cog_btop\"|" ~/.config/btop/btop.conf
    end
    __cog_run dbus-send --session --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure
    # Значок меню задаётся настройкой виджета: сигнала о смене значков панель не слушает вовремя
    if not set -q COGITATOR_DRY
        qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "panels().forEach(function(p){p.widgets('org.kde.plasma.kickoff').forEach(function(w){w.currentConfigGroup=['General'];w.writeConfig('icon','$HOME/.local/share/icons/$cog_scheme/scalable/apps/start-here-kde.svg');w.reloadConfig();});});" >/dev/null
    end
    if not set -q COGITATOR_DRY
        echo $t > ~/.config/cogitator/current
    end
    functions -e __cog_run
    echo "Облачение: $cog_name"
end
""",
}

CONF_NOTIFY = r"""# config.fish загружается позже и задаёт starship, поэтому тема подключается перед первым приглашением
status is-interactive; and function __cog_late --on-event fish_prompt
    functions -e __cog_late
    functions -e fish_prompt
    functions -c __cog_prompt fish_prompt
    functions -e fish_command_not_found
    functions -c __cog_notfound_handler fish_command_not_found
    __cog_greeting
end

# Уведомление о завершении долгой команды
function __cog_postexec --on-event fish_postexec
    set -l st $status
    test "$CMD_DURATION" -ge 30000; or return
    set -l first (string split -f1 ' ' -- $argv[1])
    contains -- $first btop литания vim nvim nano less man ssh htop; and return
    __cog_load
    if test $st -eq 0
        notify-send -a Когитатор $cog_done_ok $first
    else
        notify-send -a Когитатор -u critical $cog_done_err "$first: код $st"
    end
end
"""

INSTALL = r"""#!/usr/bin/env fish
# Установка в профиль. Файлы fish кладутся вне ~/.config/fish: там репозиторий пользователя.
set -l src (status dirname)
set -l pre ~/.local/share/cogitator-theme/pre-state
mkdir -p ~/.local/share/color-schemes ~/.local/share/fonts/cogitator ~/.local/share/cogitator/themes \
    ~/.local/share/cogitator/wallpapers ~/.config/cogitator/fastfetch ~/.config/cogitator/ghostty \
    ~/.config/cogitator/shaders ~/.config/ghostty ~/.config/btop/themes \
    ~/.local/share/fish/vendor_functions.d ~/.local/share/fish/vendor_conf.d
if not test -f $pre/colorscheme
    mkdir -p $pre
    kreadconfig6 --file kdeglobals --group General --key ColorScheme > $pre/colorscheme
    command cp ~/.config/plasma-org.kde.plasma.desktop-appletsrc $pre/
    if not test -f ~/.config/btop/btop.conf
        touch $pre/btop-created
    end
    for f in $src/fish/functions/*.fish
        basename $f .fish
    end > $pre/fish-functions
end
if not test -f $pre/cursor
    kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme > $pre/cursor
end
if not test -f $pre/plasmatheme
    set -l ptheme (kreadconfig6 --file plasmarc --group Theme --key name)
    test -n "$ptheme"; or set ptheme default
    echo $ptheme > $pre/plasmatheme
end
if test -f ~/.config/neofetch/config.conf; and not test -f $pre/neofetch.conf
    command cp ~/.config/neofetch/config.conf $pre/neofetch.conf
end
if not test -f $pre/icontheme
    kreadconfig6 --file kdeglobals --group Icons --key Theme > $pre/icontheme
end
mkdir -p ~/.local/share/icons ~/.local/share/plasma/plasmoids ~/.local/share/aurorae/themes
mkdir -p ~/.local/share/plasma/desktoptheme ~/.local/share/locale/ru/LC_MESSAGES ~/.config/systemd/user
mkdir -p ~/.icons
for d in $src/cursors/*
    rm -rf ~/.icons/(basename $d)
    cp -a $d ~/.icons/
end
rm -rf ~/.local/share/plasma/desktoptheme/cogitator
cp -r $src/desktoptheme/cogitator ~/.local/share/plasma/desktoptheme/
cp $src/locale/kscreenlocker_greet.mo ~/.local/share/locale/ru/LC_MESSAGES/
cp $src/cogitator-herald.service ~/.config/systemd/user/
for d in $src/aurorae/*
    rm -rf ~/.local/share/aurorae/themes/(basename $d)
    cp -r $d ~/.local/share/aurorae/themes/
end
for d in $src/icons/* $src/plasmoids/*
    set -l target ~/.local/share/(string match -q '*/icons/*' $d; and echo icons; or echo plasma/plasmoids)/(basename $d)
    rm -rf $target
    cp -r $d $target
end
cp $src/color-schemes/* ~/.local/share/color-schemes/
cp $src/themes/* ~/.local/share/cogitator/themes/
cp $src/sigil.txt $src/sigil-neofetch.txt $src/herald.py $src/apps.py $src/doctor.py $src/palette.json ~/.local/share/cogitator/
mkdir -p ~/.config/fastfetch
if test -f ~/.config/neofetch/config.conf
    sed -i "s|^image_source=.*|image_source=\"$HOME/.local/share/cogitator/sigil-neofetch.txt\"|" ~/.config/neofetch/config.conf
end
if visudo -cf $src/sudoers-cogitator >/dev/null
    sudo install -o root -g root -m 0440 $src/sudoers-cogitator /etc/sudoers.d/cogitator
else
    echo 'Файл sudoers не прошёл проверку, пропущен' >&2
end
cp $src/wallpapers/* ~/.local/share/cogitator/wallpapers/
cp $src/shaders/* ~/.config/cogitator/shaders/
cp $src/btop/* ~/.config/btop/themes/
cp $src/fish/functions/* ~/.local/share/fish/vendor_functions.d/
cp $src/fish/conf.d/* ~/.local/share/fish/vendor_conf.d/
for f in $src/ghostty/*
    string replace -a @HOME@ $HOME < $f > ~/.config/cogitator/ghostty/(basename $f)
end
for f in $src/fastfetch/*
    string replace -a @HOME@ $HOME < $f > ~/.config/cogitator/fastfetch/(basename $f)
end
# Переустановка не должна сбрасывать выбранную тему
set -l cur forge
test -r ~/.config/cogitator/current; and read cur < ~/.config/cogitator/current
contains -- $cur forge scrapcode; or set cur forge
cp ~/.config/cogitator/ghostty/$cur ~/.config/cogitator/ghostty-current
cp ~/.config/cogitator/fastfetch/logo-$cur.jsonc ~/.config/fastfetch/config.jsonc
echo $cur > ~/.config/cogitator/current
python3 ~/.local/share/cogitator/apps.py apply $cur
if not grep -q cogitator/ghostty-current ~/.config/ghostty/config
    printf '\nconfig-file = %s/.config/cogitator/ghostty-current\n' $HOME >> ~/.config/ghostty/config
end
if not test -f ~/.config/btop/btop.conf
    echo 'color_theme = "cogitator-forge"' > ~/.config/btop/btop.conf
end
cp $src/fonts/*.ttf ~/.local/share/fonts/cogitator/
fc-cache -f ~/.local/share/fonts
systemctl --user daemon-reload
systemctl --user enable cogitator-herald.service
systemctl --user restart cogitator-herald.service
echo "Установлено. Новый терминал, затем: облачение $cur"
"""


FASTFETCH_MODULES = ["title", "separator", "os", "host", "kernel", "uptime", "packages", "shell", "display",
                     "de", "wm", "wmtheme", "theme", "icons", "font", "cursor", "terminal", "terminalfont",
                     "cpu", "gpu", "memory", "swap", "disk", "localip", "battery", "poweradapter", "locale",
                     "break", "colors"]

HERALD_UNIT = """[Unit]
Description=Вестник Когитатора
PartOf=graphical-session.target
After=graphical-session.target

[Service]
ExecStart=/usr/bin/python3 %h/.local/share/cogitator/herald.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
"""


def main() -> None:
    if not WALL_SRC.is_file():
        sys.exit(f"Нет обоев: {WALL_SRC}. Укажите картинку в COGITATOR_WALLPAPER.")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "wallpapers").mkdir()
    for key, t in THEMES.items():
        w(f"color-schemes/{t['scheme']}.colors", colors(t))
        w(f"ghostty/{key}", ghostty(t, key))
        w(f"fastfetch/{key}.jsonc", fastfetch(t))
        w(f"fastfetch/logo-{key}.jsonc", json.dumps({"logo": {
            "type": "file", "source": "@HOME@/.local/share/cogitator/sigil.txt",
            "color": {"1": t["accent"], "2": t["accent2"]}, "padding": {"right": 3}},
            "modules": FASTFETCH_MODULES}, indent=2) + "\n")
        w(f"btop/cogitator-{key}.theme", btop(t))
        w(f"themes/{key}.fish", theme_vars(key, t))
        cmd = ["magick", str(WALL_SRC), "-filter", "Lanczos", "-resize", SIZE + "^",
               "-gravity", "center", "-extent", SIZE]
        if t["modulate"]:
            cmd += ["-modulate", t["modulate"]]
        cmd += ["-quality", "92", str(OUT / f"wallpapers/{key}.jpg")]
        subprocess.run(cmd, check=True)
    w("shaders/forge.glsl", SHADER_FORGE)
    w("shaders/scrapcode.glsl", SHADER_SCRAP)
    w("sigil.txt", emblem.text("$1", "$2"))
    w("sigil-neofetch.txt", emblem.text("${c1}", "${c2}"))
    for name, body in FISH.items():
        w(f"fish/functions/{name}.fish", body)
    w("fish/conf.d/cogitator.fish", CONF_NOTIFY)
    icons.build(OUT / "icons", THEMES)
    aurorae.build(OUT / "aurorae", THEMES)
    cursors.build(OUT / "cursors", THEMES)
    plasmatheme.build(OUT / "desktoptheme")
    boot.build(OUT / "boot", (OUT / "color-schemes/CogitatorForge.colors").read_text(encoding="utf8"),
               OUT / "wallpapers/forge.jpg")
    for module in ("herald.py", "apps.py", "doctor.py"):
        shutil.copy(Path(__file__).parent / module, OUT / module)
    w("palette.json", json.dumps(THEMES, ensure_ascii=False, indent=2) + "\n")
    w("sudoers-cogitator", 'Defaults badpass_message="Подпись отвергнута"\n')
    w("cogitator-herald.service", HERALD_UNIT)
    w("locale/.keep", "")
    po = subprocess.run(["msgunfmt", "/usr/share/locale/ru/LC_MESSAGES/kscreenlocker_greet.mo"],
                        capture_output=True, text=True, check=True).stdout
    assert 'msgstr "Ошибка разблокировки"' in po
    subprocess.run(["msgfmt", "-o", str(OUT / "locale/kscreenlocker_greet.mo"), "-"],
                   input=po.replace('msgstr "Ошибка разблокировки"', 'msgstr "Подпись отвергнута"'),
                   text=True, check=True)
    shutil.copytree(Path(__file__).parent / "plasmoids", OUT / "plasmoids")
    shutil.copytree(Path(__file__).parent / "fonts", OUT / "fonts")
    w("install.fish", INSTALL)
    (OUT / "install.fish").chmod(0o755)
    print("OK", OUT)


if __name__ == "__main__":
    main()
