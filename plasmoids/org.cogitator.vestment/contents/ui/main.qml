import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    property string current: "forge"
    property bool busy: false
    readonly property color tint: current === "scrapcode" ? "#39E36B" : "#E0281E"
    readonly property string readCmd: "cat $HOME/.config/cogitator/current"
    readonly property string switchCmd: "fish -c облачение"

    preferredRepresentation: fullRepresentation
    toolTipMainText: current === "scrapcode" ? "Скрапкод" : "Кузня Марса"
    toolTipSubText: "Щелчок: сменить облачение"
    Plasmoid.backgroundHints: "NoBackground"

    P5Support.DataSource {
        id: shell
        engine: "executable"
        onNewData: (source, data) => {
            disconnectSource(source);
            if (source === root.readCmd) {
                const v = (data.stdout || "").trim();
                if (v === "forge" || v === "scrapcode") root.current = v;
            } else if (source === root.switchCmd) {
                root.busy = false;
                connectSource(root.readCmd);
            }
        }
    }
    Timer {
        interval: 3000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: shell.connectSource(root.readCmd)
    }

    fullRepresentation: MouseArea {
        Layout.minimumWidth: Kirigami.Units.iconSizes.smallMedium
        Layout.preferredWidth: Math.min(height, Kirigami.Units.iconSizes.medium)
        Layout.fillHeight: true
        hoverEnabled: true
        onClicked: {
            if (root.busy) return;
            root.busy = true;
            shell.connectSource(root.switchCmd);
        }
        Canvas {
            id: gear
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height) * (parent.containsMouse ? 0.92 : 0.8)
            height: width
            onWidthChanged: requestPaint()
            Connections { target: root; function onTintChanged() { gear.requestPaint(); } }
            RotationAnimator on rotation {
                running: root.busy; from: 0; to: 360; duration: 900; loops: Animation.Infinite
            }
            onPaint: {
                const c = getContext("2d");
                const s = width / 24;
                c.reset();
                c.scale(s, s);
                c.translate(12, 12);
                c.fillStyle = root.tint;
                for (let i = 0; i < 8; i++) {
                    c.save();
                    c.rotate(i * Math.PI / 4);
                    c.fillRect(-1.8, -11, 3.6, 4);
                    c.restore();
                }
                c.strokeStyle = root.tint;
                c.lineWidth = 2.6;
                c.beginPath(); c.arc(0, 0, 6.8, 0, Math.PI * 2); c.stroke();
                c.beginPath(); c.arc(0, 0, 2.2, 0, Math.PI * 2); c.fill();
            }
        }
    }
}
