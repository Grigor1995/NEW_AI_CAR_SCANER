import QtQuick
import QtQuick.Controls.Basic as Basic
import CarDiagnostic
Basic.TextArea {
    id: control
    padding: 12; color: Neo.text; placeholderTextColor: Neo.muted
    selectionColor: Neo.accent; selectedTextColor: "#FFFFFF"
    background: Rectangle { radius: 8; color: Neo.secondary; border.color: control.activeFocus ? Neo.blue : Neo.border }
}
