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

    header: ToolBar {
        background: Rectangle { color: Neo.secondary; border.color: Neo.border }
        RowLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 12
            Image { source: "../assets/app_icon/canonical.svg"; sourceSize.width: 40; sourceSize.height: 40; Layout.preferredWidth: 40; Layout.preferredHeight: 40 }
            Column {
                Label { text: narrow ? "CDA" : "CAR DIAGNOSTIC ANALYSIS"; color: Neo.text; font.bold: true; font.pixelSize: narrow ? 15 : 19 }
                Label { text: "NEO AUTOMOTIVE DIAGNOSTIC"; color: Neo.blue; font.pixelSize: 10; visible: !narrow }
            }
            Item { Layout.fillWidth: true }
            ComboBox {
                id: modeSelector; objectName: "modeSelector"
                model: App.roles.filter(function(role) { return role !== "MARKET" })
                enabled: model.length > 0
                displayText: model.length > 0 ? currentText : qsTr("Sign in")
                onActivated: page = "home"
                Accessible.name: qsTr("Authorized workspace")
            }
            Button { text: App.email.length ? qsTr("Account") : qsTr("Sign in"); onClicked: accountDialog.open() }
        }
    }
    footer: Rectangle {
        height: footerLabel.implicitHeight + 24; color: Neo.secondary
        Label { id: footerLabel; anchors.fill: parent; anchors.margins: 12; text: App.message.length ? App.message : qsTr("Read-only by default. No hardware connected means no live measurements."); color: Neo.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
    }
    ScrollView {
        anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: window.width; spacing: 24
            RowLayout {
                Layout.fillWidth: true; Layout.margins: 24
                ColumnLayout {
                    Label { text: page === "home" ? qsTr("Your diagnostic workspace") : pageTitle(page); color: Neo.text; font.pixelSize: narrow ? 24 : 32; font.bold: true }
                    Label { text: App.deviceStatus; color: App.connected ? Neo.success : Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
                Item { Layout.fillWidth: true }
                Button { text: qsTr("Main menu"); visible: page !== "home"; onClicked: page = "home" }
            }
            GridLayout {
                id: homeGrid
                uniformCellWidths: true
                visible: page === "home"; columns: narrow ? 2 : 4; rowSpacing: 16; columnSpacing: 16
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24
                Repeater {
                    model: [
                        {key:"vehicles", label:qsTr("My vehicles"), glyph:"vehicle", status:""},
                        {key:"diagnostics", label:qsTr("Diagnostics"), glyph:"diagnostics", status:""},
                        {key:"live", label:qsTr("Live data"), glyph:"telemetry", status:""},
                        {key:"ai", label:qsTr("AI analysis"), glyph:"analysis", status:qsTr("Deterministic rules")},
                        {key:"reports", label:qsTr("Reports"), glyph:"reports", status:""},
                        {key:"settings", label:qsTr("Settings"), glyph:"settings", status:""},
                        {key:"monitoring", label:qsTr("Auto monitoring"), glyph:"monitoring", status:qsTr("Planned")},
                        {key:"workshop", label:workspace === "CUSTOMER" ? qsTr("Work orders") : qsTr("Service centers"), glyph:"workshop", status:qsTr("Planned")},
                        {key:"repair", label:qsTr("Repair guidance"), glyph:"repair", status:qsTr("Licensed provider required")},
                        {key:"admin", label:qsTr("Administration"), glyph:"admin", status:workspace === "ADMIN" ? qsTr("Planned") : qsTr("ADMIN permission required")},
                        {key:"market", label:qsTr("MARKET portal"), glyph:"market", status:qsTr("Planned — no payments")},
                        {key:"updates", label:qsTr("Online updates"), glyph:"updates", status:qsTr("Distribution not configured")}
                    ]
                    delegate: AbstractButton {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: narrow ? 144 : 184
                        Accessible.name: modelData.label
                        onClicked: page = modelData.key
                        background: Rectangle { radius: 16; color: parent.hovered ? Neo.elevated : Neo.card; border.color: parent.hovered ? Neo.blue : Neo.border; Behavior on color { ColorAnimation { duration: 120 } } }
                        contentItem: Item {
                            Column {
                                anchors.centerIn: parent; width: parent.width - 24; spacing: 12
                                Image { source: "icons/" + modelData.glyph + ".svg"; width: 48; height: 48; anchors.horizontalCenter: parent.horizontalCenter }
                                Label { text: modelData.label; color: Neo.text; font.bold: true; font.pixelSize: narrow ? 13 : 16; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                                Label { text: modelData.status; color: Neo.muted; font.pixelSize: 10; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                            }
                        }
                    }
                }
            }
            ColumnLayout {
                visible: page === "vehicles"; Layout.fillWidth: true; Layout.margins: 24; spacing: 16
                Label { text: qsTr("Vehicles are private to the signed-in account. Entered identity is not ECU-verified."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                GridLayout {
                    columns: narrow ? 1 : 3; Layout.fillWidth: true
                    TextField { id: makeField; placeholderText: qsTr("Make"); Layout.fillWidth: true; maximumLength: 80 }
                    TextField { id: modelField; placeholderText: qsTr("Model"); Layout.fillWidth: true; maximumLength: 80 }
                    SpinBox { id: yearField; from: 1886; to: new Date().getFullYear() + 1; value: new Date().getFullYear(); editable: true }
                    TextField { id: vinField; placeholderText: qsTr("VIN (optional)"); Layout.fillWidth: true; maximumLength: 17 }
                    Button { text: qsTr("Add vehicle"); enabled: App.email.length > 0; onClicked: App.addVehicle(makeField.text, modelField.text, yearField.value, vinField.text) }
                }
                Repeater { model: App.vehicles; delegate: Label { required property var modelData; text: modelData.make + " " + modelData.model + " · " + modelData.year; color: Neo.text; font.pixelSize: 18 } }
                Label { text: qsTr("No vehicles saved"); visible: App.vehicles.length === 0; color: Neo.muted }
            }
            ColumnLayout {
                visible: page === "diagnostics" || page === "live"; Layout.fillWidth: true; Layout.margins: 24; spacing: 16
                Label { text: qsTr("Connect only an authorized adapter on a trusted local network. TCP is not encrypted."); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
                GridLayout {
                    columns: narrow ? 1 : 4; Layout.fillWidth: true
                    TextField { id: hostField; placeholderText: qsTr("Adapter IP address"); Layout.fillWidth: true }
                    SpinBox { id: portField; from: 1; to: 65535; value: 35000; editable: true }
                    Button { text: qsTr("Connect Wi-Fi"); enabled: App.email.length > 0; onClicked: App.connectTcp(hostField.text, portField.value) }
                    Button { text: qsTr("Disconnect"); onClicked: App.disconnectDevice() }
                    TextField { id: serialField; placeholderText: qsTr("Serial port, e.g. COM3"); Layout.fillWidth: true }
                    Button { text: qsTr("Connect USB / serial"); enabled: App.email.length > 0; onClicked: App.connectSerial(serialField.text) }
                }
                GridLayout {
                    columns: narrow ? 1 : 3; Layout.fillWidth: true; columnSpacing: 16; rowSpacing: 16
                    Repeater { model: App.measurements; delegate: MetricCard { required property var modelData; Layout.fillWidth: true; label: modelData.name === "rpm" ? qsTr("Engine RPM") : modelData.name === "speed" ? qsTr("Vehicle speed") : qsTr("Coolant temperature"); reading: modelData.display; quality: modelData.quality; timestamp: modelData.at; samples: modelData.history || [] } }
                }
                RowLayout {
                    Button { text: qsTr("Read stored DTCs"); enabled: App.connected; onClicked: App.scan() }
                    Label { text: App.dtcs.join(" · "); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
                Label { text: qsTr("ECU writes are locked: no verified operation profile or qualified hardware validation is configured."); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            ColumnLayout {
                visible: page === "ai"; Layout.fillWidth: true; Layout.margins: 24; spacing: 16
                Label { text: qsTr("Evidence-based rules; no LLM provider is configured. Recommendations do not establish a defective component."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                TextArea { id: symptomField; placeholderText: qsTr("Describe symptoms"); Layout.fillWidth: true; Layout.preferredHeight: 140; wrapMode: TextEdit.Wrap }
                Button { text: qsTr("Analyze available evidence"); onClicked: analysisResult = App.analyze(symptomField.text) }
                Label { text: analysisResult; color: Neo.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            ColumnLayout {
                visible: page === "reports"; Layout.fillWidth: true; Layout.margins: 24
                Label { text: qsTr("Export current measurements with timestamps, provenance and availability. No performed scan is inferred."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                TextField { id: exportPath; placeholderText: qsTr("Absolute JSON report path"); Layout.fillWidth: true }
                Button { text: qsTr("Export JSON report"); onClicked: App.exportReport(exportPath.text) }
            }
            GridLayout {
                visible: page === "settings"; columns: narrow ? 1 : 2; Layout.fillWidth: true; Layout.margins: 24; rowSpacing: 16
                Label { text: qsTr("Language"); color: Neo.text }
                ComboBox { model: ["English", "Հայերեն", "Русский", "Français"]; currentIndex: ["en","hy","ru","fr"].indexOf(App.language); onActivated: App.language = ["en","hy","ru","fr"][currentIndex] }
                Label { text: qsTr("Measurement units"); color: Neo.text }
                ComboBox { model: [qsTr("Metric"),qsTr("Imperial")]; currentIndex: App.units === "metric" ? 0 : 1; onActivated: App.units = currentIndex === 0 ? "metric" : "imperial" }
                Label { text: qsTr("Appearance"); color: Neo.text }
                ComboBox { model: [qsTr("Dark"),qsTr("Light"),qsTr("System")]; currentIndex: ["dark","light","system"].indexOf(App.theme); onActivated: App.theme = ["dark","light","system"][currentIndex] }
                Label { text: qsTr("Read-only safety"); color: Neo.text }
                Label { text: qsTr("Enabled — vehicle writes locked"); color: Neo.success }
                Label { text: qsTr("Notifications"); color: Neo.text }
                Label { text: qsTr("Unavailable — provider not configured"); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Button { text: qsTr("Save account preferences"); onClicked: App.savePreferences() }
            }
            ColumnLayout {
                visible: ["home","vehicles","diagnostics","live","ai","reports","settings"].indexOf(page) < 0
                Layout.fillWidth: true; Layout.margins: 24
                Label { text: qsTr("Not implemented in this milestone"); color: Neo.warning; font.pixelSize: 22; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Label { text: page === "updates" ? qsTr("Version 0.1.0. Signature verification primitives exist; no update feed or installer is configured.") : page === "market" ? qsTr("Merchant listings and quotations are planned. Payment processing is disabled and not implemented.") : page === "monitoring" ? qsTr("Daily is the planned default. No unattended scan has been scheduled or performed.") : qsTr("This area requires a later implementation phase. No production data or service integration is claimed."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            Item { Layout.preferredHeight: 24 }
        }
    }
    Dialog {
        id: accountDialog; title: qsTr("Account"); modal: true; anchors.centerIn: parent; width: Math.min(window.width - 32, 440)
        ColumnLayout {
            width: parent.width; spacing: 16
            Label { text: App.email.length ? App.email : qsTr("Local account — no contact verification provider"); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            TextField { id: emailField; placeholderText: qsTr("Email"); Layout.fillWidth: true; visible: !App.email.length; maximumLength: 254; inputMethodHints: Qt.ImhEmailCharactersOnly }
            TextField { id: passwordField; placeholderText: qsTr("Password (12–256 UTF-8 bytes)"); echoMode: TextInput.Password; Layout.fillWidth: true; maximumLength: 256; visible: !App.email.length }
            RowLayout {
                visible: !App.email.length
                Button { text: qsTr("Sign in"); enabled: !App.busy; onClicked: { App.login(emailField.text,passwordField.text); passwordField.clear() } }
                Button { text: qsTr("Register"); enabled: !App.busy; onClicked: { App.registerAccount(emailField.text,passwordField.text); passwordField.clear() } }
                BusyIndicator { running: App.busy; implicitWidth: 24; implicitHeight: 24 }
            }
            Button { text: qsTr("Sign out"); visible: App.email.length > 0; onClicked: { App.logout(); accountDialog.close() } }
            Label { text: App.message; color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }
    function pageTitle(key) {
        const names = { vehicles:qsTr("My vehicles"), diagnostics:qsTr("Diagnostics"), live:qsTr("Live data"), ai:qsTr("AI analysis"), reports:qsTr("Reports"), settings:qsTr("Settings"), monitoring:qsTr("Auto monitoring"), workshop:qsTr("Service centers"), repair:qsTr("Repair guidance"), admin:qsTr("Administration"), market:qsTr("MARKET portal"), updates:qsTr("Online updates") }
        return names[key] || key
    }
}
