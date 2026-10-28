pragma Singleton
import QtQuick
QtObject {
    readonly property bool light: App.theme === "light" || (App.theme === "system" && Qt.styleHints.colorScheme === Qt.Light)
    readonly property color background: light ? "#EDF7FF" : "#070D18"
    readonly property color secondary: light ? "#E2EDF6" : "#0D1726"
    readonly property color card: light ? "#FFFFFF" : "#122136"
    readonly property color elevated: light ? "#DCEAF5" : "#192B43"
    readonly property color blue: "#00BFFF"
    readonly property color cyan: "#29DFFF"
    readonly property color accent: "#126EFF"
    readonly property color text: light ? "#0D1726" : "#EDF7FF"
    readonly property color muted: light ? "#456078" : "#9CB5CC"
    readonly property color border: light ? "#9CB5CC" : "#25415C"
    readonly property color success: "#20D79A"
    readonly property color warning: "#FFB547"
    readonly property color error: "#FF596D"
}
