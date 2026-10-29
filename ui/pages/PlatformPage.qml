import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import CarDiagnostic

ColumnLayout {
    id: panel
    spacing: 12
    property bool narrow: width < 720
    Label {
        text: qsTr("Source platform services · local companion on port 8001 · separate diagnostic sessions")
        color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true
    }
    Flow {
        Layout.fillWidth: true; spacing: 8
        NeoButton { text: qsTr("API documentation / file upload"); onClicked: Qt.openUrlExternally("http://127.0.0.1:8001/docs") }
        NeoButton { text: qsTr("Check service"); enabled: !Platform.busy; onClicked: Platform.request("GET", "/api/v1/migration/runtime", "") }
        NeoButton { text: qsTr("New diagnostic session"); enabled: !Platform.busy; onClicked: Platform.request("POST", "/api/v1/sessions", "{}") }
        NeoButton { text: qsTr("Analyze session"); enabled: !Platform.busy && Platform.sessionId.length > 0; onClicked: Platform.request("POST", "/api/v1/intelligence/sessions/" + Platform.sessionId + "/analyze", "{}") }
        NeoButton { text: qsTr("Guided test plan"); enabled: !Platform.busy && Platform.sessionId.length > 0; onClicked: Platform.request("GET", "/api/v1/decision/sessions/" + Platform.sessionId + "/plan", "") }
        NeoButton {
            text: qsTr("Attach live measurements"); enabled: !Platform.busy && App.connected && Platform.sessionId.length > 0
            onClicked: {
                var samples = []
                App.measurements.forEach(function(m) {
                    if (m.quality === "valid" && m.value !== null)
                        samples.push({session_id: Platform.sessionId, timestamp_ms: Date.parse(m.at), pid: ({speed: "vehicle_speed", coolant: "coolant_temp"}[m.name] || m.name), value: m.value, unit: m.unit, source: "OBD", quality: "GOOD"})
                })
                Platform.request("POST", "/api/v1/telemetry/sessions/" + Platform.sessionId + "/samples", JSON.stringify({samples: samples}))
            }
        }
        NeoButton { text: qsTr("Analyze telemetry"); enabled: !Platform.busy && Platform.sessionId.length > 0; onClicked: Platform.request("POST", "/api/v1/telemetry/sessions/" + Platform.sessionId + "/analyze", "{}") }
        NeoButton { text: qsTr("ECU network map"); enabled: !Platform.busy && Platform.sessionId.length > 0; onClicked: Platform.request("GET", "/api/v1/network-discovery/sessions/" + Platform.sessionId + "/map", "") }
    }
    Label { text: qsTr("Session: ") + (Platform.sessionId || qsTr("Create or load a session")); color: Neo.cyan; wrapMode: Text.Wrap; Layout.fillWidth: true }
    RowLayout {
        Layout.fillWidth: true
        NeoTextField { id: symptom; placeholderText: qsTr("Describe the observed symptom"); Layout.fillWidth: true }
        NeoButton {
            text: qsTr("Add symptom"); enabled: !Platform.busy && Platform.sessionId.length > 0 && symptom.text.trim().length > 0
            onClicked: Platform.request("POST", "/api/v1/sessions/" + Platform.sessionId + "/symptoms", JSON.stringify({raw_text: symptom.text}))
        }
    }
    RowLayout {
        Layout.fillWidth: true
        NeoTextField { id: dtc; placeholderText: "DTC · P0302"; Layout.fillWidth: true; maximumLength: 5 }
        NeoButton {
            text: qsTr("Add reported DTC"); enabled: !Platform.busy && Platform.sessionId.length > 0 && /^[PCBU][0-3][0-9A-Fa-f]{3}$/.test(dtc.text)
            onClicked: Platform.request("POST", "/api/v1/sessions/" + Platform.sessionId + "/dtcs", JSON.stringify({code: dtc.text.toUpperCase(), source: "USER_REPORTED"}))
        }
    }
    Repeater {
        model: Platform.analysis.hypotheses || []
        delegate: Label {
            required property var modelData
            text: modelData.statement + " · " + modelData.status
            color: Neo.text; wrapMode: Text.Wrap; Layout.fillWidth: true
        }
    }
    Repeater {
        model: Platform.analysis.recommendations || []
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true; spacing: 6
            Label { text: modelData.name; font.bold: true; color: Neo.cyan; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: modelData.purpose; color: Neo.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: (modelData.safety_notes || []).join(" · "); color: Neo.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout {
                Repeater {
                    model: ["PASS", "FAIL", "INCOMPLETE"]
                    delegate: NeoButton {
                        required property string modelData
                        property var test: parent.parent.modelData
                        text: modelData; enabled: !Platform.busy
                        onClicked: Platform.request("POST", "/api/v1/intelligence/sessions/" + Platform.sessionId + "/test-results", JSON.stringify({test_id: test.id, result: modelData, measurements: {}}))
                    }
                }
            }
        }
    }
    Label { text: qsTr("Teach AI — local knowledge"); color: Neo.text; font.bold: true }
    NeoTextField { id: knowledgeTitle; placeholderText: qsTr("Document title"); Layout.fillWidth: true }
    NeoTextArea { id: knowledgeText; placeholderText: qsTr("Paste technical knowledge with its source in the text"); Layout.fillWidth: true; Layout.preferredHeight: 100; wrapMode: TextEdit.Wrap }
    RowLayout {
        NeoButton {
            text: qsTr("Index knowledge"); enabled: !Platform.busy && knowledgeTitle.text.trim().length > 0 && knowledgeText.text.trim().length > 0
            onClicked: Platform.request("POST", "/api/v1/ai/knowledge", JSON.stringify({document_id: "doc-" + Date.now(), title: knowledgeTitle.text, text: knowledgeText.text, metadata: {source: "USER_REPORTED"}}))
        }
        NeoTextField { id: search; placeholderText: qsTr("Search knowledge"); Layout.fillWidth: true }
        NeoButton { text: qsTr("Search"); enabled: !Platform.busy && search.text.trim().length > 0; onClicked: Platform.request("POST", "/api/v1/ai/knowledge/search", JSON.stringify({query: search.text, top_k: 5})) }
    }
    Repeater {
        model: Platform.searchResults
        delegate: Label {
            required property var modelData
            text: (modelData.title || "") + "\n" + (modelData.text || "")
            color: Neo.text; wrapMode: Text.Wrap; Layout.fillWidth: true
        }
    }
    Label { text: qsTr("All source API operations"); color: Neo.text; font.bold: true }
    NeoComboBox {
        id: operation; objectName: "platformOperationSelector"
        Layout.fillWidth: true; model: Platform.operations; textRole: "label"
        onActivated: {
            var item = Platform.operations[currentIndex]
            route.text = item.path.replace(/\{session_id\}/g, Platform.sessionId || "{session_id}")
            method.currentIndex = ["GET", "POST", "PUT", "DELETE", "PATCH"].indexOf(item.method)
        }
    }
    RowLayout {
        Layout.fillWidth: true
        NeoComboBox { id: method; model: ["GET", "POST", "PUT", "DELETE", "PATCH"]; Layout.preferredWidth: 100 }
        NeoTextField { id: route; text: "/api/v1/migration/runtime"; Layout.fillWidth: true; placeholderText: qsTr("API path; replace parameter placeholders") }
        NeoButton { text: Platform.busy ? qsTr("Loading…") : qsTr("Send"); enabled: !Platform.busy && route.text.indexOf("{") < 0; onClicked: Platform.request(method.currentText, route.text, body.text) }
    }
    NeoTextArea { id: body; text: "{}"; Layout.fillWidth: true; Layout.preferredHeight: 120; wrapMode: TextEdit.Wrap; Accessible.name: qsTr("JSON request body") }
    Label { text: qsTr("Response"); color: Neo.text; font.bold: true }
    NeoTextArea { text: Platform.response; readOnly: true; Layout.fillWidth: true; Layout.preferredHeight: 360; wrapMode: TextEdit.Wrap; selectByMouse: true; Accessible.name: qsTr("Platform response") }
    Label { text: qsTr("LLM models, provider credentials and physical adapters must be configured separately. Simulation is not a vehicle measurement."); color: Neo.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
}
