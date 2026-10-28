import QtQuick
import QtQuick.Controls.Basic as Basic
import CarDiagnostic
Basic.Dialog {
    id: control
    popupType: Basic.Popup.Item
    padding: 20
    background: Rectangle { color: Neo.card; radius: 12; border.color: Neo.border }
    header: Basic.Label {
        text: control.title; color: Neo.text; font.pixelSize: 20; font.bold: true
        leftPadding: 20; rightPadding: 20; topPadding: 20; bottomPadding: 8
    }
}
