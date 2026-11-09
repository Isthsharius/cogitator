"""Заставка Plymouth и установщик оформления загрузки и экрана входа."""
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import emblem

SIZE = 440
PAD = 50  # запас под свечение
FONT = Path.home() / ".local/share/cogitator-theme/fonts/Handjet[ELGR,ELSH,wght].ttf"
BG = "#0A0705"
ACCENT, BRASS, TEXT = "#E0281E", "#C08A3E", "#E6CFA3"
BOOT_LINES = ["Пробуждение духа машины", "Нанесение святых масел", "Литания запуска когитатора",
              "Разогрев реактора", "Сосуд готов принять дух"]
DOWN_LINES = ["Дух машины отходит ко сну"]

SCRIPT = r"""// Кузня Марса: эмблема с пульсирующим свечением, литания и полоса хода.
Window.SetBackgroundTopColor(0.039, 0.027, 0.020);
Window.SetBackgroundBottomColor(0.039, 0.027, 0.020);
cx = Window.GetX() + Window.GetWidth() / 2;
cy = Window.GetY() + Window.GetHeight() / 2;

fun place(image, x, y, z) {
    s = Sprite(image);
    s.SetPosition(x - image.GetWidth() / 2, y - image.GetHeight() / 2, z);
    return s;
}

top = cy - 70;
glow = place(Image("glow.png"), cx, top, 1);
mark = place(Image("emblem.png"), cx, top, 2);

BAR_W = 360;
line_y = top + 262;
bar_y = top + 340;
place(Image("track.png"), cx, bar_y, 3);
fill_image = Image("fill.png");
fill = Sprite();
fill.SetPosition(cx - BAR_W / 2, bar_y - 1, 4);
global.shown_w = 0;

if (Plymouth.GetMode() == "boot" || Plymouth.GetMode() == "updates" || Plymouth.GetMode() == "system-upgrade") {
    count = @BOOT@; prefix = "boot-";
} else {
    count = @DOWN@; prefix = "down-";
}
i = 0;
while (i < count) {
    lines[i] = Image(prefix + i + ".png");
    i++;
}
caption = Sprite(lines[0]);
caption.SetPosition(cx - lines[0].GetWidth() / 2, line_y, 3);

global.tick = 0;
global.current = 0;
fun refresh() {
    global.tick++;
    glow.SetOpacity(0.55 + 0.45 * Math.Sin(global.tick / 22));
    n = Math.Int(global.tick / 110) % count;
    if (n != global.current) {
        global.current = n;
        caption.SetImage(lines[n]);
        caption.SetX(cx - lines[n].GetWidth() / 2);
    }
}
Plymouth.SetRefreshFunction(refresh);

fun progress(duration, value) {
    w = Math.Int(BAR_W * value);
    if (w > global.shown_w && w > 0) {
        global.shown_w = w;
        fill.SetImage(fill_image.Scale(w, 3));
    }
}
Plymouth.SetBootProgressFunction(progress);
"""

SETUP = r"""#!/bin/bash
# Оформление загрузки и экрана входа. Запуск: sudo bash setup.sh [install|revert]
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Нужен sudo' >&2; exit 1; }
src=$(dirname "$(realpath "$0")")
state=/var/lib/cogitator-boot
themes=/usr/share/plymouth/themes
conf=/etc/plasmalogin.conf
greeter=/var/lib/plasmalogin

install_all() {
    mkdir -p "$state"
    [[ -f $state/plymouth-theme ]] || plymouth-set-default-theme > "$state/plymouth-theme"
    [[ -f $state/plasmalogin.conf ]] || cp -a "$conf" "$state/plasmalogin.conf"
    if [[ -f $greeter/.config/kdeglobals && ! -f $state/kdeglobals ]]; then
        cp -a "$greeter/.config/kdeglobals" "$state/kdeglobals"
    fi
    rm -rf "$themes/cogitator"
    cp -r "$src/cogitator" "$themes/cogitator"
    chown -R root:root "$themes/cogitator"
    install -d -o plasmalogin -g plasmalogin "$greeter/wallpapers" "$greeter/.config"
    install -o plasmalogin -g plasmalogin -m 0644 "$src/forge.jpg" "$greeter/wallpapers/cogitator-forge.jpg"
    install -o plasmalogin -g plasmalogin -m 0644 "$src/kdeglobals" "$greeter/.config/kdeglobals"
    sed -i "s|^Image=.*|Image=file://$greeter/wallpapers/cogitator-forge.jpg|" "$conf"
    plymouth-set-default-theme -R cogitator
    echo 'Готово. Заставка появится при следующей загрузке.'
}

revert_all() {
    [[ -f $state/plymouth-theme ]] || { echo 'Нет сохранённого состояния' >&2; exit 1; }
    cp -a "$state/plasmalogin.conf" "$conf"
    if [[ -f $state/kdeglobals ]]; then
        cp -a "$state/kdeglobals" "$greeter/.config/kdeglobals"
    else
        rm -f "$greeter/.config/kdeglobals"
    fi
    rm -f "$greeter/wallpapers/cogitator-forge.jpg"
    plymouth-set-default-theme -R "$(cat "$state/plymouth-theme")"
    rm -rf "$themes/cogitator" "$state"
    echo 'Прежняя загрузка и экран входа возвращены.'
}

case "${1:-install}" in
    install) install_all ;;
    revert) revert_all ;;
    *) echo 'Использование: setup.sh [install|revert]' >&2; exit 2 ;;
esac
"""


def layers() -> tuple[Image.Image, Image.Image]:
    png = subprocess.run(["rsvg-convert", "-w", str(SIZE), "-h", str(SIZE)],
                         input=emblem.art().encode(), capture_output=True, check=True).stdout
    red, green, _ = Image.open(io.BytesIO(png)).convert("RGB").split()
    alpha = ImageChops.lighter(red, green)
    star = red.point([255 if v > 127 else 0 for v in range(256)])
    color = Image.composite(Image.new("RGB", (SIZE, SIZE), ACCENT), Image.new("RGB", (SIZE, SIZE), BRASS), star)
    color.putalpha(alpha)
    full = (SIZE + 2 * PAD, SIZE + 2 * PAD)
    mark = Image.new("RGBA", full, (0, 0, 0, 0))
    mark.paste(color, (PAD, PAD))
    wide = Image.new("L", full, 0)
    wide.paste(alpha, (PAD, PAD))
    halo = Image.new("RGB", full, ACCENT)
    halo.putalpha(wide.filter(ImageFilter.GaussianBlur(14)).point([min(255, v * 2) for v in range(256)]))
    return mark, halo


def caption(text: str) -> Image.Image:
    font = ImageFont.truetype(str(FONT), 42)
    font.set_variation_by_axes([600, 1, 2])  # Weight, Element Grid, Element Shape
    left, top, right, bottom = font.getbbox(text)
    image = Image.new("RGBA", (int(right - left) + 8, int(bottom - top) + 8), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((4 - left, 4 - top), text, font=font, fill=TEXT)
    return image


def build(out: Path, kdeglobals: str, wallpaper: Path) -> None:
    theme = out / "cogitator"
    theme.mkdir(parents=True, exist_ok=True)
    mark, halo = layers()
    mark.save(theme / "emblem.png")
    halo.save(theme / "glow.png")
    Image.new("RGB", (360, 1), "#5A3A1C").save(theme / "track.png")
    Image.new("RGB", (4, 3), ACCENT).save(theme / "fill.png")
    for prefix, lines in (("boot-", BOOT_LINES), ("down-", DOWN_LINES)):
        for i, text in enumerate(lines):
            caption(text).save(theme / f"{prefix}{i}.png")
    script = SCRIPT.replace("@BOOT@", str(len(BOOT_LINES))).replace("@DOWN@", str(len(DOWN_LINES)))
    (theme / "cogitator.script").write_text(script, encoding="utf8")
    base = "/usr/share/plymouth/themes/cogitator"
    (theme / "cogitator.plymouth").write_text(
        f"[Plymouth Theme]\nName=Cogitator\nDescription=Кузня Марса\nModuleName=script\n\n"
        f"[script]\nImageDir={base}\nScriptFile={base}/cogitator.script\n", encoding="utf8")
    (out / "setup.sh").write_text(SETUP, encoding="utf8")
    (out / "kdeglobals").write_text(kdeglobals, encoding="utf8")
    (out / "forge.jpg").write_bytes(wallpaper.read_bytes())
