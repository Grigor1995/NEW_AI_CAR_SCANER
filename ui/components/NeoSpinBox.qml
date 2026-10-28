import QtQuick
import QtQuick.Controls.Basic as Basic
import CarDiagnostic
Basic.SpinBox {
    id: control
    implicitWidth: 144; implicitHeight: 40
    leftPadding: 12; rightPadding: 36
    contentItem: TextInput {
        text: control.textFromValue(control.value, control.locale)
        font: control.font; color: Neo.text
        selectionColor: Neo.accent; selectedTextColor: "#FFFFFF"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        readOnly: !control.editable; validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        onEditingFinished: control.value = control.valueFromText(text, control.locale)
    }
    background: Rectangle { radius: 6; color: Neo.secondary; border.color: control.activeFocus ? Neo.blue : Neo.border }
    up.indicator: Rectangle {
        x: control.width - width; width: 32; height: control.height / 2
        color: control.up.pressed ? Neo.elevated : Neo.card
        Text { anchors.centerIn: parent; text: "+"; color: control.up.enabled ? Neo.text : Neo.muted }
    }
    down.indicator: Rectangle {
        x: control.width - width; y: control.height / 2; width: 32; height: control.height / 2
        color: control.down.pressed ? Neo.elevated : Neo.card
        Text { anchors.centerIn: parent; text: "−"; color: control.down.enabled ? Neo.text : Neo.muted }
    }
}
