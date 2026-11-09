# Cogitator

A KDE Plasma 6 theme with two looks that switch with one command:

- **Кузня Марса** (Forge of Mars): red, brass and parchment on soot black
- **Скрапкод** (Scrapcode): acid green on near-black, with a light glitch shader in the terminal

Everything is generated from one palette in `build.py`.

The interface and the commands are in Russian.

## What it themes

| Area | Details |
|---|---|
| Plasma | color schemes, desktop theme, icons, cursors, Aurorae window decorations, fonts, wallpapers |
| Widgets | `Литания`: circular CPU/GPU/RAM monitor; `Облачение`: theme switcher |
| Terminals | Ghostty (with shaders), Alacritty, Konsole |
| Tools | VS Code colors, btop, fastfetch, fish prompt |
| Boot and login | optional, Plasma Login Manager only (`boot.py`) |

`cogitator-herald` is a small user service. It sends in-theme notifications about new USB devices, low battery,
overheating and network loss, and the `Литания` widget shows the same alerts.

## Requirements

Developed and tested on one machine only: CachyOS, Plasma 6.8.2, 2560x1440 wallpapers. Other Arch-based setups
may work; anything else probably needs changes.

```sh
sudo pacman -S --needed fish imagemagick gettext librsvg python-pillow libnotify networkmanager \
    ghostty btop fastfetch ttf-jetbrains-mono-nerd ttf-firacode-nerd ttf-ibm-plex
```

Hardware-specific defaults, safe to leave but silent when they do not match:

- battery and charger paths are `BAT0` and `ADP1` in `herald.py` and the `Литания` widget
- GPU temperature comes from `nvidia-smi`

## Install

The wallpaper is not included. Provide your own image:

```sh
COGITATOR_WALLPAPER=/path/to/image.png python3 build.py
fish /var/tmp/cogitator-theme/install.fish
```

Then open a new terminal and run `облачение кузня` or `облачение скрапкод`.

**Read before installing.** The installer changes your profile. It saves the previous state once in
`~/.local/share/cogitator-theme/pre-state`, then:

- replaces the color sections of `~/.config/alacritty/alacritty.toml`
- sets `workbench.colorCustomizations` in VS Code settings
- makes `Cogitator.profile` the default Konsole profile
- asks for `sudo` to add `/etc/sudoers.d/cogitator`, which only changes the wrong-password message

## Commands

| Command | Action |
|---|---|
| `облачение [кузня\|скрапкод]` | switch theme; with no argument, toggle |
| `облачение --проверка` | check that the theme is intact, useful after Plasma updates |
| `вернуть-облик` | restore the look from before installation and remove the theme |
| `манифест` / `литания` | fastfetch / btop in theme colors |

## Tests

```sh
python3 -m unittest discover -s tests
```

## Credits and license

- Fonts: Handjet, Tektur and Exo 2 are under the SIL Open Font License; see `fonts/OFL-*.txt`.
- Fan-made. Not affiliated with or endorsed by Games Workshop.
- License for the code: not chosen yet.
