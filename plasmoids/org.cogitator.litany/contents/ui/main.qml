import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as P5Support
import org.kde.ksysguard.sensors as Sensors

PlasmoidItem {
    id: root
    property string current: "forge"
    // Без сети датчики ГП выключены: их опрос не даёт дискретной карте уснуть.
    property bool onMains: true
    // Состояние машины от Вестника: ok, warn или crit, и подпись.
    property string stateLevel: "ok"
    property string stateText: ""
    property bool pulse: false
    readonly property color gearTone: stateLevel === "crit" && pulse ? pal.text
        : stateLevel === "crit" ? pal.err : stateLevel === "warn" ? pal.c : pal.a
    readonly property var pal: current === "scrapcode"
        ? ({ track: "#102016", line: "#1E4A2C", a: "#39E36B", b: "#7CE8C8", c: "#A8F03A", text: "#B9F2C6", muted: "#71A883", err: "#FF4A3D", title: "Tektur", mono: "FiraCode Nerd Font" })
        : ({ track: "#211712", line: "#5A3A1C", a: "#E0281E", b: "#3FB8C4", c: "#C08A3E", text: "#E6CFA3", muted: "#A8926F", err: "#FF5A3C", title: "Handjet", mono: "JetBrainsMono Nerd Font" })

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: "NoBackground"

    readonly property string readCmd: "cat $HOME/.config/cogitator/current; m=$(grep -lx Mains /sys/class/power_supply/*/type 2>/dev/null | head -n1); cat \"${m%type}online\" 2>/dev/null || echo 1; cat $XDG_RUNTIME_DIR/cogitator/state 2>/dev/null"
    P5Support.DataSource {
        id: shell
        engine: "executable"
        onNewData: (source, data) => {
            disconnectSource(source);
            const lines = (data.stdout || "").trim().split("\n");
            if (lines[0] === "forge" || lines[0] === "scrapcode") root.current = lines[0];
            if (lines[1] === "0" || lines[1] === "1") root.onMains = lines[1] === "1";
            root.stateLevel = lines[2] === "warn" || lines[2] === "crit" ? lines[2] : "ok";
            root.stateText = root.stateLevel === "ok" ? "" : (lines[3] || "");
        }
    }
    Timer {
        interval: 3000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: shell.connectSource(root.readCmd)
    }

    component S: Sensors.Sensor { updateRateLimit: 1000 }
    S { id: cpu; sensorId: "cpu/all/usage" }
    S { id: cpuTemp; sensorId: "cpu/all/maximumTemperature" }
    S { id: mem; sensorId: "memory/physical/usedPercent" }
    S { id: memUsed; sensorId: "memory/physical/used" }
    S { id: gpu; sensorId: "gpu/gpu0/usage"; enabled: root.onMains }
    S { id: gpu0Temp; sensorId: "gpu/gpu0/temperature"; enabled: root.onMains }
    S { id: disk; sensorId: "disk/all/usedPercent" }
    S { id: down; sensorId: "network/all/download" }
    S { id: up; sensorId: "network/all/upload" }

    function num(s) { const v = Number(s.value); return isFinite(v) ? v : 0; }
    function hot(pct) { return pct >= 90; }
    readonly property real gpuTemp: num(gpu0Temp)

    fullRepresentation: Item {
        id: face
        Layout.minimumWidth: 360
        Layout.minimumHeight: 200
        Layout.preferredWidth: 460
        Layout.preferredHeight: 250
        readonly property real unit: Math.min(width / 460, height / 250)

        Canvas {
            id: dial
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            width: 240 * face.unit
            height: width
            onWidthChanged: requestPaint()
            Connections {
                target: root
                function onPalChanged() { dial.requestPaint(); }
            }
            Timer {
                interval: 1000; running: true; repeat: true
                onTriggered: { root.pulse = !root.pulse; dial.requestPaint(); }
            }
            function arc(c, r, pct, col) {
                const start = -Math.PI / 2;
                const end = start + Math.PI * 2 * Math.min(pct, 100) / 100;
                const tone = root.hot(pct) ? root.pal.err : col;
                c.lineWidth = 7;
                c.strokeStyle = root.pal.track;
                c.beginPath(); c.arc(0, 0, r, 0, Math.PI * 2); c.stroke();
                c.lineWidth = 12;
                c.strokeStyle = Qt.alpha(tone, 0.22);
                c.beginPath(); c.arc(0, 0, r, start, end); c.stroke();
                c.lineWidth = 7;
                c.strokeStyle = tone;
                c.beginPath(); c.arc(0, 0, r, start, end); c.stroke();
            }
            onPaint: {
                const c = getContext("2d");
                c.reset();
                c.scale(width / 200, width / 200);
                c.translate(100, 100);
                c.strokeStyle = root.pal.c;
                c.lineWidth = 1.5;
                for (let i = 0; i < 72; i++) {
                    const a = i * 5 * Math.PI / 180, l = i % 6 === 0 ? 90 : 94;
                    c.beginPath();
                    c.moveTo(l * Math.sin(a), -l * Math.cos(a));
                    c.lineTo(98 * Math.sin(a), -98 * Math.cos(a));
                    c.stroke();
                }
                arc(c, 86, root.num(cpu), root.pal.a);
                arc(c, 74, root.onMains ? root.num(gpu) : 0, root.pal.b);
                arc(c, 62, root.num(mem), root.pal.c);
                c.scale(0.64, 0.64);
                c.strokeStyle = root.gearTone;
                c.fillStyle = root.gearTone;
                c.beginPath(); c.arc(0, 0, 47, 0, Math.PI * 2); c.lineWidth = 1.4; c.stroke();
                c.lineWidth = 2.2;
                c.beginPath(); c.arc(0, 0, 15, 0, Math.PI * 2); c.stroke();
                for (let i = 0; i < 8; i++) {
                    c.save(); c.rotate(i * Math.PI / 4);
                    c.beginPath();
                    c.moveTo(0, -15); c.lineTo(0, -43);
                    c.moveTo(-5, -36); c.lineTo(0, -44); c.lineTo(5, -36);
                    c.stroke(); c.restore();
                }
                for (let j = 0; j < 12; j++) {
                    c.save(); c.rotate((j * 30 + 15) * Math.PI / 180);
                    c.fillRect(-2.5, -21, 5, 6); c.restore();
                }
                c.beginPath(); c.arc(0, 0, 4, 0, Math.PI * 2); c.fill();
            }
        }
        Column {
            anchors { left: dial.right; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 14 * face.unit }
            spacing: 2 * face.unit
            component Big: Text {
                style: Text.Outline; styleColor: "#000000"
                font { family: root.pal.mono; pixelSize: 20 * face.unit; bold: true }
            }
            component Small: Text {
                style: Text.Outline; styleColor: "#000000"
                color: root.pal.text
                font { family: root.pal.mono; pixelSize: 14 * face.unit }
            }
            Small {
                visible: root.stateLevel !== "ok"
                width: parent.width
                elide: Text.ElideRight
                color: root.stateLevel === "crit" ? root.pal.err : root.pal.c
                font.bold: true
                text: root.stateText
            }
            Big { color: root.pal.a; text: "ЦП  " + Math.round(root.num(cpu)) + "%" }
            Big { color: root.pal.b; text: root.onMains ? "ГП  " + Math.round(root.num(gpu)) + "%" : "ГП  сон" }
            Big { color: root.pal.c; text: "ОЗУ " + Math.round(root.num(mem)) + "%" }
            Item { width: 1; height: 8 * face.unit }
            Small { text: "ЦП " + Math.round(root.num(cpuTemp)) + "°" + (root.onMains ? "  ГП " + Math.round(root.gpuTemp) + "°" : "") }
            Small { text: "ОЗУ  " + memUsed.formattedValue }
            Small { text: "ДИСК " + Math.round(root.num(disk)) + "%" }
            Small { text: "↓ " + down.formattedValue }
            Small { text: "↑ " + up.formattedValue }
        }
    }
}
