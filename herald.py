#!/usr/bin/env python3
"""Вестник Когитатора: уведомления об устройствах, заряде и перегреве."""
import html
import os
import select
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

POWER_ROOT = Path("/sys/class/power_supply")
BAT_LOW = 15
GPU_HOT = 87  # nvidia-smi: GPU Target Temperature Specification типичной карты
GPU_COOL = GPU_HOT - 8
START_GRACE = 10.0
BATCH_WINDOW = 1.5
STORM = 4  # столько устройств разом бывает после пробуждения: не уведомлять
POLL = 10
GPU_EVERY = 3  # видеокарту опрашивать реже: nvidia-smi заметно тяжелее чтения sysfs
CPU_MARGIN = 5  # предупреждать за столько градусов до предела из coretemp
CPU_LIMIT_DEFAULT = 100
COOL_DELTA = 8
OFFLINE_TICKS = 2  # столько опросов подряд без сети: короткие сбои не показывать


def power_paths(root: Path = POWER_ROOT) -> tuple[Path, Path]:
    """Батарея ноутбука и датчик сети; у мыши и наушников scope=Device, их не считаем."""
    battery = root / "absent-battery"
    mains = root / "absent-mains"
    for item in sorted(root.glob("*")):
        kind = read(item / "type")
        if kind == "Battery" and read(item / "scope") != "Device" and battery.name == "absent-battery":
            battery = item
        elif kind == "Mains" and mains.name == "absent-mains":
            mains = item
    return battery, mains / "online"


def notify(title: str, body: str = "", urgency: str = "normal") -> None:
    cmd = ["notify-send", "-a", "Когитатор", "-i", "start-here", "-u", urgency, title]
    if body:
        cmd.append(html.escape(body))
    subprocess.run(cmd, check=False, timeout=10)


def parse_block(lines: list[str]) -> dict[str, str]:
    return dict(line.split("=", 1) for line in lines if "=" in line)


def describe(props: dict[str, str]) -> tuple[str, str] | None:
    """Вернуть (вид, подпись) для подключения или None, если его не показывать."""
    if props.get("ACTION") != "add":
        return None
    if props.get("SUBSYSTEM") == "tty":
        name = props.get("DEVNAME", "")
        return ("tty", name.removeprefix("/dev/")) if name.startswith(("/dev/ttyUSB", "/dev/ttyACM")) else None
    if props.get("SUBSYSTEM") != "usb" or props.get("DEVTYPE") != "usb_device":
        return None
    if props.get("ID_VENDOR_ID") == "1d6b" or props.get("ID_USB_INTERFACES", "").startswith(":09"):
        return None
    model = props.get("ID_MODEL_FROM_DATABASE") or props.get("ID_MODEL") or "устройство USB"
    return ("usb", model.replace("_", " "))


def summary(batch: list[tuple[str, str]]) -> str | None:
    usb = [n for k, n in batch if k == "usb"]
    tty = [n for k, n in batch if k == "tty"]
    if not batch or len(usb) > STORM:
        return None
    return ", ".join(usb + tty)


def watch_devices() -> None:
    proc = subprocess.Popen(
        ["udevadm", "monitor", "--udev", "--property", "--subsystem-match=usb/usb_device", "--subsystem-match=tty"],
        stdout=subprocess.PIPE, text=True, bufsize=1)
    assert proc.stdout is not None
    started = time.monotonic()
    lines: list[str] = []
    batch: list[tuple[str, str]] = []
    while True:
        ready, _, _ = select.select([proc.stdout], [], [], BATCH_WINDOW)
        if not ready:
            text = summary(batch)
            batch = []
            if text and time.monotonic() - started > START_GRACE:
                notify("Новый сосуд", text)
            continue
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("udevadm завершился")
        line = line.strip()
        if line:
            lines.append(line)
        elif lines:
            event = describe(parse_block(lines))
            lines = []
            if event:
                batch.append(event)


def read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def gpu_temperature() -> int | None:
    """Опрашивать только уже проснувшуюся карту, чтобы не будить её ради замера."""
    if not shutil.which("nvidia-smi"):
        return None
    for dev in Path("/sys/bus/pci/devices").iterdir():
        if read(dev / "vendor") == "0x10de" and (read(dev / "class") or "").startswith("0x03"):
            if read(dev / "power/runtime_status") != "active":
                return None
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=10, check=True).stdout
                return round(float(out.split()[0]))
            except (subprocess.SubprocessError, ValueError, IndexError):
                return None
    return None


def cpu_reading() -> tuple[int | None, int]:
    """Вернуть (температура корпуса ЦП, предел) из датчика coretemp."""
    for mon in Path("/sys/class/hwmon").iterdir():
        if read(mon / "name") == "coretemp":
            temp = read(mon / "temp1_input")
            crit = read(mon / "temp1_crit")
            limit = int(crit) // 1000 if crit and crit.isdigit() else CPU_LIMIT_DEFAULT
            return (int(temp) // 1000 if temp and temp.isdigit() else None), limit
    return None, CPU_LIMIT_DEFAULT


def network_state() -> str | None:
    try:
        out = subprocess.run(["nmcli", "-t", "-f", "STATE", "general"], capture_output=True, text=True,
                             timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out or None


@dataclass
class Readings:
    ac: str | None = None
    capacity: int | None = None
    discharging: bool = False
    cpu: int | None = None
    cpu_limit: int = CPU_LIMIT_DEFAULT
    gpu: int | None = None
    network: str | None = None


class Vigil:
    """Состояние машины без ввода-вывода: что сообщить и что показать в Литании."""

    def __init__(self, ac: str | None = None) -> None:
        self.ac = ac
        self.capacity: int | None = None
        self.weak = self.cpu_hot = self.gpu_hot = self.offline = False
        self.cpu: int | None = None
        self.gpu: int | None = None
        self.offline_ticks = 0

    def update(self, r: Readings) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        if self.ac == "0" and r.ac == "1":
            out.append(("Подношение принято", "Питание подключено", "normal"))
        self.ac = r.ac
        low = r.capacity is not None and r.capacity <= BAT_LOW and r.discharging
        if low and not self.weak:
            out.append(("Дух слабеет", f"Заряд {r.capacity}%", "critical"))
        self.weak, self.capacity = low, r.capacity
        self.cpu_hot, note = self._heat(self.cpu_hot, r.cpu, r.cpu_limit - CPU_MARGIN, "Процессор")
        out += note
        self.gpu_hot, note = self._heat(self.gpu_hot, r.gpu, GPU_HOT, "Видеокарта")
        out += note
        self.cpu, self.gpu = r.cpu, r.gpu
        out += self._network(r.network)
        return out

    @staticmethod
    def _heat(active: bool, temp: int | None, limit: int, name: str) -> tuple[bool, list[tuple[str, str, str]]]:
        if temp is None or temp <= limit - COOL_DELTA:
            return False, []
        if temp >= limit and not active:
            return True, [("Реактор на пределе", f"{name} {temp} °C", "critical")]
        return active, []

    def _network(self, state: str | None) -> list[tuple[str, str, str]]:
        if state is None:
            return []
        if state != "disconnected":
            self.offline_ticks = 0
            restored = self.offline
            self.offline = False
            return [("Связь восстановлена", "Сеть снова доступна", "normal")] if restored else []
        self.offline_ticks += 1
        if self.offline_ticks >= OFFLINE_TICKS and not self.offline:
            self.offline = True
            return [("Связь утрачена", "Сеть недоступна", "normal")]
        return []

    def state(self) -> tuple[str, str]:
        if self.cpu_hot:
            return "crit", f"Реактор на пределе: ЦП {self.cpu}°"
        if self.gpu_hot:
            return "crit", f"Реактор на пределе: ГП {self.gpu}°"
        if self.weak:
            return "crit", f"Дух слабеет: заряд {self.capacity}%"
        if self.offline:
            return "warn", "Связь утрачена"
        return "ok", ""


def state_path() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "cogitator/state"


def write_state(path: Path, level: str, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(f"{level}\n{text}\n", encoding="utf-8")
    tmp.replace(path)


def watch_power() -> None:
    bat, ac = power_paths()
    vigil = Vigil(read(ac))
    path = state_path()
    tick = 0
    gpu = None
    while True:
        if tick % GPU_EVERY == 0:
            gpu = gpu_temperature()
        tick += 1
        cap = read(bat / "capacity")
        cpu, limit = cpu_reading()
        readings = Readings(ac=read(ac), capacity=int(cap) if cap and cap.isdigit() else None,
                            discharging=read(bat / "status") == "Discharging", cpu=cpu, cpu_limit=limit,
                            gpu=gpu, network=network_state())
        for title, body, urgency in vigil.update(readings):
            notify(title, body, urgency)
        write_state(path, *vigil.state())
        time.sleep(POLL)


def main() -> None:
    threading.Thread(target=watch_power, daemon=True).start()
    watch_devices()


if __name__ == "__main__":
    main()
