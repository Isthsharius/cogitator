"""Тесты логики темы. Запуск из src: python3 -m unittest discover -s tests."""
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from PIL import ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import apps
import boot
import build
import doctor
import herald
import wallpaper

FORGE = {
    "title": "Кузня", "scheme": "CogitatorForge", "bg": "#0B0806", "panel": "#15100C", "panel2": "#211712",
    "line": "#5A3A1C", "accent": "#E0281E", "accent2": "#C08A3E", "text": "#E6CFA3", "muted": "#A8926F",
    "ok": "#4FD67A", "link": "#3FB8C4", "err": "#FF5A3C",
    "ansi": [f"#0000{i:02X}" for i in range(16)],
}


class Colors(unittest.TestCase):
    def test_rgb_hand_computed(self):
        self.assertEqual(apps.rgb("#E0281E"), "224,40,30")

    def test_alacritty_block_is_valid_toml(self):
        cfg = tomllib.loads(apps.alacritty_colors(FORGE))
        self.assertEqual(cfg["colors"]["primary"]["background"], "0x0B0806")
        self.assertEqual(cfg["colors"]["normal"]["black"], "0x000000")
        self.assertEqual(cfg["colors"]["bright"]["white"], "0x00000F")

    def test_split_keeps_other_sections_and_plain_colors(self):
        src = "[font]\nsize = 12\n\n[colors]\nx = true\n\n[colors.primary]\nbackground = \"1\"\n\n[env]\nA = \"b\"\n"
        rest, colors = apps.split_color_sections(src)
        self.assertEqual(colors, "[colors.primary]\nbackground = \"1\"\n\n")
        self.assertEqual(rest, "[font]\nsize = 12\n\n[colors]\nx = true\n\n[env]\nA = \"b\"\n")

    def test_konsole_scheme_intense_uses_bright_ansi(self):
        text = apps.konsole_scheme(FORGE)
        self.assertIn("[Color1Intense]\nColor=0,0,9\n", text)
        self.assertIn("[Background]\nColor=11,8,6\n", text)

    def test_vscode_has_all_terminal_colors(self):
        colors = apps.vscode_colors(FORGE)
        self.assertEqual(colors["terminal.ansiBlack"], "#000000")
        self.assertEqual(colors["terminal.ansiBrightWhite"], "#00000F")


class VigilTests(unittest.TestCase):
    def test_quiet_state(self):
        v = herald.Vigil("1")
        self.assertEqual(v.update(herald.Readings(ac="1", capacity=100, cpu=58, network="connected")), [])
        self.assertEqual(v.state(), ("ok", ""))

    def test_cpu_alerts_once_at_95_and_clears_at_87(self):
        v = herald.Vigil("1")
        self.assertEqual(v.update(herald.Readings(ac="1", cpu=94)), [])
        self.assertEqual(v.update(herald.Readings(ac="1", cpu=95)),
                         [("Реактор на пределе", "Процессор 95 °C", "critical")])
        self.assertEqual(v.state(), ("crit", "Реактор на пределе: ЦП 95°"))
        self.assertEqual(v.update(herald.Readings(ac="1", cpu=96)), [])
        v.update(herald.Readings(ac="1", cpu=88))
        self.assertEqual(v.state()[0], "crit")
        v.update(herald.Readings(ac="1", cpu=87))
        self.assertEqual(v.state(), ("ok", ""))

    def test_sleeping_gpu_does_not_stay_hot(self):
        v = herald.Vigil("1")
        v.update(herald.Readings(ac="1", gpu=87))
        self.assertEqual(v.state()[0], "crit")
        v.update(herald.Readings(ac="1", gpu=None))
        self.assertEqual(v.state(), ("ok", ""))

    def test_battery_low_only_when_discharging(self):
        v = herald.Vigil("0")
        self.assertEqual(v.update(herald.Readings(ac="1", capacity=10, discharging=False))[0][0],
                         "Подношение принято")
        self.assertEqual(v.state(), ("ok", ""))
        self.assertEqual(v.update(herald.Readings(ac="0", capacity=15, discharging=True)),
                         [("Дух слабеет", "Заряд 15%", "critical")])
        self.assertEqual(v.state(), ("crit", "Дух слабеет: заряд 15%"))

    def test_short_network_blip_is_silent(self):
        v = herald.Vigil("1")
        self.assertEqual(v.update(herald.Readings(ac="1", network="disconnected")), [])
        self.assertEqual(v.update(herald.Readings(ac="1", network="connected")), [])
        self.assertEqual(v.state(), ("ok", ""))

    def test_network_loss_and_restore(self):
        v = herald.Vigil("1")
        v.update(herald.Readings(ac="1", network="disconnected"))
        self.assertEqual(v.update(herald.Readings(ac="1", network="disconnected")),
                         [("Связь утрачена", "Сеть недоступна", "normal")])
        self.assertEqual(v.state(), ("warn", "Связь утрачена"))
        self.assertEqual(v.update(herald.Readings(ac="1", network="disconnected")), [])
        self.assertEqual(v.update(herald.Readings(ac="1", network="connected")),
                         [("Связь восстановлена", "Сеть снова доступна", "normal")])

    def test_crit_outranks_network_warning(self):
        v = herald.Vigil("1")
        for _ in range(2):
            v.update(herald.Readings(ac="1", cpu=96, network="disconnected"))
        self.assertEqual(v.state()[0], "crit")


class DoctorTests(unittest.TestCase):
    def test_filters_only_own_qml_errors(self):
        lines = ["file:///x/org.cogitator.litany/main.qml:5: module \"org.kde.foo\" is not installed",
                 "kde.plasmashell: error in org.kde.panel", "org.cogitator.litany loaded"]
        self.assertEqual(doctor.plasmoid_errors(lines), [lines[0]])

    def test_version_change_is_warning(self):
        self.assertEqual(doctor.version_check("6.9.0", "6.8.2")[1], doctor.WARN)
        self.assertEqual(doctor.version_check("6.8.2", "6.8.2")[1], doctor.OK)
        self.assertEqual(doctor.version_check("6.8.2", None)[1], doctor.OK)

    def test_exit_code_fail_only(self):
        self.assertEqual(doctor.summarize([("a", doctor.WARN, "x")]), 0)
        self.assertEqual(doctor.summarize([("a", doctor.FAIL, "x")]), 1)


class PortabilityTests(unittest.TestCase):
    def supply(self, root, name, kind, scope=None):
        d = root / name
        d.mkdir()
        (d / "type").write_text(kind + "\n")
        if scope:
            (d / "scope").write_text(scope + "\n")

    def test_power_paths_use_real_names_and_skip_mouse_battery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.supply(root, "hidpp_battery_0", "Battery", "Device")
            self.supply(root, "BAT1", "Battery")
            self.supply(root, "ACAD", "Mains")
            bat, ac = herald.power_paths(root)
            self.assertEqual(bat, root / "BAT1")
            self.assertEqual(ac, root / "ACAD/online")

    def test_power_paths_on_desktop_read_as_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat, ac = herald.power_paths(Path(tmp))
            self.assertIsNone(herald.read(bat / "capacity"))
            self.assertIsNone(herald.read(ac))

    def test_build_is_not_in_shared_tmp_and_fonts_ship_with_repo(self):
        self.assertFalse(str(build.OUT).startswith("/var/tmp"))
        self.assertTrue(boot.FONT.is_file())
        self.assertEqual(boot.FONT.parent, ROOT / "fonts")

    def test_generated_wallpaper_is_dark_full_size_and_repeatable(self):
        first = wallpaper.render(320, 180)
        self.assertEqual(first.size, (320, 180))
        self.assertEqual(first.tobytes(), wallpaper.render(320, 180).tobytes())
        self.assertLess(ImageStat.Stat(first.convert("L")).mean[0], 70)

    def test_widget_does_not_assume_adapter_name(self):
        qml = (ROOT / "plasmoids/org.cogitator.litany/contents/ui/main.qml").read_text(encoding="utf8")
        self.assertNotIn("ADP1", qml)


if __name__ == "__main__":
    unittest.main()
