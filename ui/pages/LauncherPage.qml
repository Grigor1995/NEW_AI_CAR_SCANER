import QtQuick
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts
import CarDiagnostic
Item {
    id: launcher
    objectName: "referenceLauncher"
    property real minimumSceneHeight: 620
    readonly property int columns: width < 720 ? 2 : 4
    readonly property int rows: Math.ceil(App.launcherOrder.length / columns)
    property int dragSource: -1
    property int dragDestination: -1
    property point dragPoint: Qt.point(0,0)
    property bool suppressClick: false
    implicitHeight: Math.max(minimumSceneHeight, 74 + rows * 160 + (rows-1) * 14 + 16)
    signal navigate(string key)
    Image {
        objectName: "launcherBackground"
        anchors.fill: parent; source: "../../assets/launcher/background.png"
        fillMode: Image.Stretch; opacity: Neo.light ? 0.22 : 0.78
    }
    Rectangle { anchors.fill: parent; color: Neo.light ? "#40EDF7FF" : "#18020A15" }
    Basic.Label { x: 20; y: 16; text: qsTr("Main menu"); color: Neo.text; font.pixelSize: 23; font.bold: true }
    Basic.Label { x: 20; y: 49; text: launcher.width < 720 ? qsTr("Swipe to browse") : qsTr("Drag tiles to reorder"); color: Neo.muted; font.pixelSize: 12 }
    GridLayout {
        id: tiles
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: parent.bottom; leftMargin: 20; rightMargin: 20; topMargin: 74; bottomMargin: 16 }
        columns: launcher.columns; uniformCellWidths: true; uniformCellHeights: true
        columnSpacing: 14; rowSpacing: 14
        Repeater {
            model: App.launcherOrder
            delegate: Basic.AbstractButton {
                id: tile
                required property string modelData
                required property int index
                objectName: "launcherTile_" + modelData
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.minimumWidth: 0; Layout.minimumHeight: 160
                Accessible.name: launcher.titleFor(modelData)
                opacity: launcher.dragSource === index ? 0.5 : 1
                onClicked: if(!launcher.suppressClick) launcher.navigate(modelData)
                background: Rectangle {
                    radius: 18
                    border.width: tile.activeFocus || launcher.dragDestination === tile.index ? 2 : 1
                    border.color: tile.activeFocus || tile.hovered || launcher.dragDestination === tile.index ? "#53C8FF" : Neo.light ? Neo.border : "#42728D"
                    gradient: Gradient {
                        GradientStop { position: 0; color: Neo.light ? "#DAEDF7FF" : tile.hovered ? "#D221405A" : "#BA16334A" }
                        GradientStop { position: 1; color: Neo.light ? "#EFFFFFFF" : "#E003101F" }
                    }
                }
                contentItem: Item {
                    Image {
                        objectName: "launcherIcon_" + tile.modelData
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: Math.max(12, parent.height * (tile.modelData === "vehicles" ? 0.14 : 0.07))
                        width: 136; height: tile.modelData === "vehicles" ? 104 : 128
                        source: tile.modelData === "vehicles" ? "../../assets/launcher/brand-car.png" : "../../assets/launcher/icons-3d.png"
                        sourceClipRect: tile.modelData === "vehicles" ? Qt.rect(0,0,0,0) : launcher.atlasRect(tile.modelData)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                    Basic.Label {
                        objectName: "launcherLabel_" + tile.modelData
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 12; rightMargin: 12; bottomMargin: 14 }
                        text: launcher.titleFor(tile.modelData)
                        color: Neo.text; font.pixelSize: 13; font.weight: Font.Normal
                        horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                    }
                }
                DragHandler {
                    id: handler
                    target: null
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    onActiveChanged: {
                        if(active) {
                            launcher.dragSource = tile.index; launcher.dragDestination = tile.index
                            launcher.suppressClick = true
                            launcher.dragPoint = launcher.mapFromItem(null, centroid.scenePosition.x, centroid.scenePosition.y)
                        } else if(launcher.dragSource >= 0) {
                            launcher.finishDrag(launcher.dragSource,launcher.dragDestination)
                        }
                    }
                    onActiveTranslationChanged: {
                        if(!active) return
                        launcher.dragPoint = launcher.mapFromItem(null, centroid.scenePosition.x, centroid.scenePosition.y)
                        const point = tiles.mapFromItem(launcher, launcher.dragPoint.x, launcher.dragPoint.y)
                        if(point.x >= 0 && point.y >= 0 && point.x < tiles.width && point.y < tiles.height) {
                            const column = Math.min(launcher.columns-1,Math.floor(point.x / ((tiles.width+14)/launcher.columns)))
                            const row = Math.min(launcher.rows-1,Math.floor(point.y / ((tiles.height+14)/launcher.rows)))
                            launcher.dragDestination = row * launcher.columns + column
                        } else launcher.dragDestination = -1
                    }
                }
            }
        }
    }
    Rectangle {
        visible: launcher.dragSource >= 0
        x: launcher.dragPoint.x - width/2; y: launcher.dragPoint.y - height/2
        width: 180; height: 48; z: 10; radius: 8; color: Neo.elevated; border.color: Neo.blue
        Basic.Label { anchors.centerIn: parent; text: launcher.dragSource >= 0 ? launcher.titleFor(App.launcherOrder[launcher.dragSource]) : ""; color: Neo.text }
    }
    function finishDrag(from,to) {
        dragSource = -1; dragDestination = -1
        Qt.callLater(function() {
            suppressClick = false
            if(to >= 0 && from !== to) App.moveLauncherTile(from,to)
        })
    }
    function atlasRect(key) {
        const cells = {diagnostics:1, devices:2, symptoms:0, live:4, guided:5, ai:6, dtc:7, reports:8, teach:9, dashboard:10, network:11}
        const cell = cells[key] === undefined ? 0 : cells[key]
        return Qt.rect((cell%4)*362,Math.floor(cell/4)*362,key === "devices" ? 348 : 362,362)
    }
    function titleFor(key) {
        const titles = {vehicles:qsTr("Vehicles"), diagnostics:qsTr("Diagnostics"), devices:qsTr("VCI / Devices"), symptoms:qsTr("Symptoms"), live:qsTr("Live Data"), guided:qsTr("Guided Tests"), ai:qsTr("AI Analysis"), dtc:qsTr("DTC"), reports:qsTr("Reports"), teach:qsTr("Teach AI"), dashboard:qsTr("Dashboard"), network:qsTr("ECU Network")}
        return titles[key] || key
    }
}
