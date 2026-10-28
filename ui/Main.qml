import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import CarDiagnostic

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 1360; height: 900; minimumWidth: 360; minimumHeight: 640
    visible: true; title: qsTr("Car Diagnostic Analysis")
    color: Neo.background
    property string page: "home"
    readonly property string workspace: modeSelector.currentText || "USER"
    property string analysisResult: ""
    readonly property bool narrow: width < 720
    font.family: "Segoe UI"
    font.pixelSize: 14
    palette.window: Neo.background
    palette.base: Neo.secondary
    palette.button: Neo.elevated
    palette.buttonText: Neo.text
    palette.text: Neo.text
    palette.windowText: Neo.text
    palette.highlight: Neo.accent
    palette.highlightedText: "#FFFFFF"

    menuBar: MenuBar {
        id: applicationMenuBar
        height: 26
        background: Rectangle { color: Neo.light ? Neo.secondary : "#0A1B31" }
        delegate: MenuBarItem {
            id: barItem
            height: 26; leftPadding: 8; rightPadding: 20
            contentItem: Text { text: barItem.text; color: Neo.text; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: barItem.highlighted ? Neo.elevated : "transparent" }
        }
        Menu {
            objectName: "applicationMenuPopup"
            popupType: Popup.Item
            title: qsTr("Application")
            background: Rectangle { implicitWidth: 280; implicitHeight: 40; color: Neo.card; border.color: Neo.border; radius: 6 }
            MenuItem { text: App.email.length ? qsTr("Account") : qsTr("Sign in"); onTriggered: accountDialog.open() }
            MenuItem { objectName: "settingsMenuItem"; text: qsTr("Settings"); onTriggered: page = "settings" }
            MenuSeparator { }
            MenuItem { text: qsTr("Auto monitoring"); onTriggered: page = "monitoring" }
            MenuItem { text: qsTr("Service centers"); onTriggered: page = "workshop" }
            MenuItem { text: qsTr("MARKET portal"); onTriggered: page = "market" }
            MenuItem { text: qsTr("Administration"); onTriggered: page = "admin" }
            MenuItem { text: qsTr("Online updates"); onTriggered: page = "updates" }
            MenuSeparator { }
            MenuItem { text: qsTr("Exit"); onTriggered: Qt.quit() }
        }
        Menu {
            popupType: Popup.Item
            title: qsTr("Help")
            background: Rectangle { implicitWidth: 280; implicitHeight: 40; color: Neo.card; border.color: Neo.border; radius: 6 }
            MenuItem { text: qsTr("About"); onTriggered: aboutDialog.open() }
        }
        NeoComboBox {
            id: modeSelector; objectName: "modeSelector"
            parent: applicationMenuBar
            anchors.right: parent.right; anchors.rightMargin: 8
            width: 150; height: 24; visible: App.email.length > 0
            model: App.roles.filter(function(role) { return role !== "MARKET" })
            enabled: model.length > 0
            displayText: model.length > 0 ? currentText : qsTr("Sign in")
            onActivated: page = "home"
            Accessible.name: qsTr("Authorized workspace")
        }
    }
    header: Rectangle {
        height: 94; color: Neo.light ? Neo.background : "#061222"
        Label { x: 8; y: 16; text: "AI CAR SCANNER"; color: Neo.text; font.pixelSize: 28; font.bold: true }
        Label { x: 8; y: 65; text: "SMART DIAGNOSTICS  •  AI ANALYSIS  •  BETTER DRIVING"; color: Neo.light ? Neo.blue : "#50CAFF"; font.pixelSize: narrow ? 9 : 12; font.bold: true; font.letterSpacing: narrow ? 0.5 : 1.8 }
    }
    footer: Rectangle {
        visible: page !== "home" || App.message.length > 0
        height: visible ? footerLabel.implicitHeight + 24 : 0; color: Neo.secondary
        Label { id: footerLabel; x: 12; y: 12; width: parent.width - 24; text: App.message.length ? App.message : qsTr("Read-only by default. No hardware connected means no live measurements."); color: Neo.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
    }
    ScrollView {
        id: mainScroll
        anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: mainScroll.availableWidth; spacing: page === "home" ? 0 : 24
            RowLayout {
                visible: page !== "home"
                Layout.fillWidth: true; Layout.margins: 24
                ColumnLayout {
                    Label { text: page === "home" ? qsTr("Your diagnostic workspace") : pageTitle(page); color: Neo.text; font.pixelSize: narrow ? 24 : 32; font.bold: true }
                    Label { text: App.deviceStatus; color: App.connected ? Neo.success : Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
                Item { Layout.fillWidth: true }
                NeoButton { text: qsTr("Main menu"); visible: page !== "home"; onClicked: page = "home" }
            }
            LauncherPage {
                Layout.leftMargin: 6; Layout.rightMargin: 6
                visible: page === "home"
                Layout.fillWidth: true
                minimumSceneHeight: mainScroll.height
                onNavigate: function(key) { page = key }
            }
            ColumnLayout {
                visible: page === "vehicles"; Layout.fillWidth: true; Layout.margins: 24; spacing: 16
                Label { text: qsTr("Vehicles are private to the signed-in account. Entered identity is not ECU-verified."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                GridLayout {
                    columns: narrow ? 1 : 3; Layout.fillWidth: true
                    NeoTextField { id: makeField; objectName: "vehicleMakeField"; placeholderText: qsTr("Make"); Layout.fillWidth: true; maximumLength: 80 }
                    NeoTextField { id: modelField; placeholderText: qsTr("Model"); Layout.fillWidth: true; maximumLength: 80 }
                    NeoSpinBox { id: yearField; from: 1886; to: new Date().getFullYear() + 1; value: new Date().getFullYear(); editable: true }
                    NeoTextField { id: vinField; placeholderText: qsTr("VIN (optional)"); Layout.fillWidth: true; maximumLength: 17 }
                    NeoButton { text: qsTr("Add vehicle"); enabled: App.email.length > 0; onClicked: App.addVehicle(makeField.text, modelField.text, yearField.value, vinField.text) }
                }
                Repeater { model: App.vehicles; delegate: Label { required property var modelData; text: modelData.make + " " + modelData.model + " · " + modelData.year; color: Neo.text; font.pixelSize: 18 } }
                Label { text: qsTr("No vehicles saved"); visible: App.vehicles.length === 0; color: Neo.muted }
            }
            ColumnLayout {
                visible: ["diagnostics","devices","live","dtc","dashboard"].indexOf(page) >= 0; Layout.fillWidth: true; Layout.margins: 24; spacing: 16
                Label { text: qsTr("Connect only an authorized adapter on a trusted local network. TCP is not encrypted."); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
                GridLayout {
                    columns: narrow ? 1 : 4; Layout.fillWidth: true
                    NeoTextField { id: hostField; placeholderText: qsTr("Adapter IP address"); Layout.fillWidth: true }
                    NeoSpinBox { id: portField; from: 1; to: 65535; value: 35000; editable: true }
                    NeoButton { text: qsTr("Connect Wi-Fi"); enabled: App.email.length > 0; onClicked: App.connectTcp(hostField.text, portField.value) }
                    NeoButton { text: qsTr("Disconnect"); onClicked: App.disconnectDevice() }
                    NeoTextField { id: serialField; placeholderText: qsTr("Serial port, e.g. COM3"); Layout.fillWidth: true }
                    NeoButton { text: qsTr("Connect USB / serial"); enabled: App.email.length > 0; onClicked: App.connectSerial(serialField.text) }
                }
                GridLayout {
                    columns: narrow ? 1 : 3; Layout.fillWidth: true; columnSpacing: 16; rowSpacing: 16
                    Repeater { model: App.measurements; delegate: MetricCard { required property var modelData; Layout.fillWidth: true; label: modelData.name === "rpm" ? qsTr("Engine RPM") : modelData.name === "speed" ? qsTr("Vehicle speed") : qsTr("Coolant temperature"); reading: modelData.display; quality: modelData.quality; timestamp: modelData.at; samples: modelData.history || [] } }
                }
                RowLayout {
                    NeoButton { text: qsTr("Read stored DTCs"); enabled: App.connected; onClicked: App.scan() }
                    Label { text: App.dtcs.join(" · "); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
                Label { text: qsTr("ECU writes are locked: no verified operation profile or qualified hardware validation is configured."); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            ColumnLayout {
                visible: page === "ai" || page === "symptoms"; Layout.fillWidth: true; Layout.margins: 24; spacing: 16
                Label { text: qsTr("Evidence-based rules; no LLM provider is configured. Recommendations do not establish a defective component."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                NeoTextArea { id: symptomField; placeholderText: qsTr("Describe symptoms"); Layout.fillWidth: true; Layout.preferredHeight: 140; wrapMode: TextEdit.Wrap }
                NeoButton { text: qsTr("Analyze available evidence"); onClicked: analysisResult = App.analyze(symptomField.text) }
                Label { text: analysisResult; color: Neo.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            ColumnLayout {
                visible: page === "reports"; Layout.fillWidth: true; Layout.margins: 24
                Label { text: qsTr("Export current measurements with timestamps, provenance and availability. No performed scan is inferred."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                NeoTextField { id: exportPath; placeholderText: qsTr("Absolute JSON report path"); Layout.fillWidth: true }
                NeoButton { text: qsTr("Export JSON report"); onClicked: App.exportReport(exportPath.text) }
            }
            GridLayout {
                visible: page === "settings"; columns: narrow ? 1 : 2; Layout.fillWidth: true; Layout.margins: 24; rowSpacing: 16
                Label { text: qsTr("Language"); color: Neo.text }
                NeoComboBox { objectName: "settingsLanguageCombo"; model: ["English", "Հայերեն", "Русский", "Français"]; currentIndex: ["en","hy","ru","fr"].indexOf(App.language); onActivated: App.language = ["en","hy","ru","fr"][currentIndex] }
                Label { text: qsTr("Measurement units"); color: Neo.text }
                NeoComboBox { objectName: "settingsUnitsCombo"; model: [qsTr("Metric"),qsTr("Imperial")]; currentIndex: App.units === "metric" ? 0 : 1; onActivated: App.units = currentIndex === 0 ? "metric" : "imperial" }
                Label { text: qsTr("Appearance"); color: Neo.text }
                NeoComboBox { objectName: "settingsThemeCombo"; model: [qsTr("Dark"),qsTr("Light"),qsTr("System")]; currentIndex: ["dark","light","system"].indexOf(App.theme); onActivated: App.theme = ["dark","light","system"][currentIndex] }
                Label { text: qsTr("Read-only safety"); color: Neo.text }
                Label { objectName: "readOnlySafetyStatus"; text: qsTr("Enabled — vehicle writes locked"); color: Neo.success }
                Label { text: qsTr("Notifications"); color: Neo.text }
                Label { text: qsTr("Unavailable — provider not configured"); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                NeoButton { objectName: "savePreferencesButton"; text: qsTr("Save account preferences"); onClicked: App.savePreferences() }
            }
            ColumnLayout {
                visible: ["home","vehicles","diagnostics","devices","live","dtc","dashboard","ai","symptoms","reports","settings"].indexOf(page) < 0
                Layout.fillWidth: true; Layout.margins: 24
                Label { text: qsTr("Not implemented in this milestone"); color: Neo.warning; font.pixelSize: 22; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Label { text: page === "updates" ? qsTr("Version 0.1.0. Signature verification primitives exist; no update feed or installer is configured.") : page === "market" ? qsTr("Merchant listings and quotations are planned. Payment processing is disabled and not implemented.") : page === "monitoring" ? qsTr("Daily is the planned default. No unattended scan has been scheduled or performed.") : qsTr("This area requires a later implementation phase. No production data or service integration is claimed."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            Item { visible: page !== "home"; Layout.preferredHeight: 24 }
        }
    }
    NeoDialog {
        id: accountDialog; title: qsTr("Account"); modal: true; anchors.centerIn: parent; width: Math.min(window.width - 32, 440)
        ColumnLayout {
            width: parent.width; spacing: 16
            Label { text: App.email.length ? App.email : qsTr("Local account — no contact verification provider"); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            NeoTextField { id: emailField; placeholderText: qsTr("Email"); Layout.fillWidth: true; visible: !App.email.length; maximumLength: 254; inputMethodHints: Qt.ImhEmailCharactersOnly }
            NeoTextField { id: passwordField; placeholderText: qsTr("Password (12–256 UTF-8 bytes)"); echoMode: TextInput.Password; Layout.fillWidth: true; maximumLength: 256; visible: !App.email.length }
            RowLayout {
                visible: !App.email.length
                NeoButton { text: qsTr("Sign in"); enabled: !App.busy; onClicked: { App.login(emailField.text,passwordField.text); passwordField.clear() } }
                NeoButton { text: qsTr("Register"); enabled: !App.busy; onClicked: { App.registerAccount(emailField.text,passwordField.text); passwordField.clear() } }
                BusyIndicator { running: App.busy; implicitWidth: 24; implicitHeight: 24 }
            }
            NeoButton { text: qsTr("Sign out"); visible: App.email.length > 0; onClicked: { App.logout(); accountDialog.close() } }
            Label { text: App.message; color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }
    NeoDialog {
        id: aboutDialog; title: qsTr("About"); modal: true; anchors.centerIn: parent
        width: Math.min(window.width - 32,480)
        Label { width: parent.width; text: qsTr("AI Car Scanner · C++ / Qt. Read-only diagnostics; unimplemented workflows are labeled in their pages."); color: Neo.text; wrapMode: Text.Wrap }
    }
    function pageTitle(key) {
        const names = { vehicles:qsTr("Vehicles"), devices:qsTr("VCI / Devices"), symptoms:qsTr("Symptoms"), guided:qsTr("Guided Tests"), dtc:qsTr("DTC"), teach:qsTr("Teach AI"), dashboard:qsTr("Dashboard"), network:qsTr("ECU Network"), diagnostics:qsTr("Diagnostics"), live:qsTr("Live data"), ai:qsTr("AI analysis"), reports:qsTr("Reports"), settings:qsTr("Settings"), monitoring:qsTr("Auto monitoring"), workshop:qsTr("Service centers"), repair:qsTr("Repair guidance"), admin:qsTr("Administration"), market:qsTr("MARKET portal"), updates:qsTr("Online updates") }
        return names[key] || key
    }
}
