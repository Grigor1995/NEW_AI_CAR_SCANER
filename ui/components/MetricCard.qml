import QtQuick
import QtQuick.Controls
import CarDiagnostic
Rectangle {
    required property string label
    property string reading: qsTr("Unavailable")
    property string quality: "unavailable"
    property string timestamp: ""
    property var samples: []
    radius: 16
    color: Neo.card
    border.color: quality === "valid" ? Neo.blue : Neo.border
    implicitHeight: 220
    Column {
        anchors.fill: parent; anchors.margins: 24; spacing: 8
        Label { text: label; color: Neo.muted; font.pixelSize: 14 }
        Label { text: reading; color: quality === "valid" ? Neo.text : Neo.muted; font.pixelSize: 26; font.bold: true }
        Label { text: quality === "valid" ? qsTr("Measured") : quality === "unsupported" ? qsTr("Unsupported") : quality === "stale" ? qsTr("Stale") : quality === "invalid" ? qsTr("Invalid") : qsTr("Unavailable"); color: quality === "valid" ? Neo.success : Neo.warning; font.pixelSize: 12 }
        TelemetryTrace { width: parent.width; height: 48; samples: quality === "valid" ? parent.parent.samples : [] }
        Label { text: timestamp; color: Neo.muted; font.pixelSize: 10; width: parent.width; elide: Text.ElideRight }
    }
    Accessible.role: Accessible.StaticText
    Accessible.name: label + ": " + reading + ", " + quality
}
