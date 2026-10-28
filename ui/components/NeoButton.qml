import QtQuick
import QtQuick.Controls.Basic as Basic
import CarDiagnostic
Basic.Button {
    id: control
    implicitHeight: 38
    implicitWidth: Math.max(96, implicitContentWidth + leftPadding + rightPadding)
    leftPadding: 14; rightPadding: 14; topPadding: 8; bottomPadding: 8
    font.pixelSize: 14
    contentItem: Text {
        text: control.text; font: control.font
        color: control.enabled ? Neo.text : Neo.muted
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 6
        color: control.down ? Neo.elevated : control.hovered ? Neo.elevated : Neo.secondary
        border.color: control.activeFocus || control.hovered ? Neo.blue : Neo.border
        border.width: control.activeFocus ? 2 : 1
    }
}
