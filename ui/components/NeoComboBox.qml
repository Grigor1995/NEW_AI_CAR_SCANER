import QtQuick
import QtQuick.Controls.Basic as Basic
import CarDiagnostic
Basic.ComboBox {
    id: control
    implicitWidth: 216; implicitHeight: 38
    leftPadding: 12; rightPadding: 34; topPadding: 8; bottomPadding: 8
    font.pixelSize: 14
    contentItem: Text {
        text: control.displayText; font: control.font
        color: control.enabled ? Neo.text : Neo.muted
        verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Text {
        x: control.width - width - 12; y: (control.height-height)/2
        text: "▾"; font.pixelSize: 16; color: control.enabled ? Neo.blue : Neo.muted
    }
    background: Rectangle {
        radius: 6; color: Neo.secondary
        border.color: control.activeFocus || control.hovered ? Neo.blue : Neo.border
        border.width: control.activeFocus ? 2 : 1
    }
    delegate: Basic.ItemDelegate {
        required property var modelData
        required property int index
        width: control.width - 16; height: 38
        text: String(modelData)
        highlighted: control.highlightedIndex === index
        contentItem: Text { text: parent.text; font: control.font; color: Neo.text; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        background: Rectangle { radius: 4; color: parent.highlighted || parent.hovered ? Neo.elevated : Neo.secondary }
    }
    popup: Basic.Popup {
        popupType: Basic.Popup.Item
        y: control.height + 4; width: control.width; padding: 8
        implicitHeight: Math.min(contentItem.implicitHeight + topPadding + bottomPadding, 320)
        contentItem: ListView {
            clip: true; implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            Basic.ScrollIndicator.vertical: Basic.ScrollIndicator { }
        }
        background: Rectangle { radius: 8; color: Neo.secondary; border.color: Neo.border }
    }
}
