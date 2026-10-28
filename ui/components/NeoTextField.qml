import QtQuick
import QtQuick.Controls.Basic as Basic
import CarDiagnostic
Basic.TextField {
    id: control
    implicitHeight: 40; implicitWidth: 240
    leftPadding: 12; rightPadding: 12; topPadding: 8; bottomPadding: 8
    color: Neo.text; placeholderTextColor: Neo.muted
    selectionColor: Neo.accent; selectedTextColor: "#FFFFFF"
    background: Rectangle { radius: 6; color: Neo.secondary; border.color: control.activeFocus ? Neo.blue : Neo.border; border.width: control.activeFocus ? 2 : 1 }
}
