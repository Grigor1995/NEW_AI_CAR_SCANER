pragma Singleton
import QtQuick
QtObject {
    readonly property bool light: App.theme === "light" || (App.theme === "system" && Qt.styleHints.colorScheme === Qt.Light)
    readonly property color background: light ? "#EDF7FF" : "#070D18"
    readonly property color secondary: light ? "#E2EDF6" : "#0D1726"
    readonly property color card: light ? "#FFFFFF" : "#122136"
    readonly property color elevated: light ? "#DCEAF5" : "#192B43"
    readonly property color blue: light ? "#0069AD" : "#00BFFF"
    readonly property color cyan: light ? "#006B85" : "#29DFFF"
    readonly property color accent: "#126EFF"
    readonly property color text: light ? "#0D1726" : "#EDF7FF"
    readonly property color muted: light ? "#456078" : "#9CB5CC"
    readonly property color border: light ? "#9CB5CC" : "#25415C"
    readonly property color success: light ? "#087A53" : "#20D79A"
    readonly property color warning: light ? "#925500" : "#FFB547"
    readonly property color error: light ? "#C5223D" : "#FF596D"
}
