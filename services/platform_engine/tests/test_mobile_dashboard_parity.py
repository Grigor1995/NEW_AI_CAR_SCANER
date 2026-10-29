"""Guard live mobile dashboard routing and presentation against Desktop labels."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "apps/mobile-ios/AICarScanner/DiagnosticScreen.swift"
ANDROID = ROOT / "apps/mobile-android/app/src/main/java/com/aicarscaner/mobile/presentation/DiagnosticScreen.kt"


def test_android_toolbar_uses_desktop_page_names():
    src = ANDROID.read_text(encoding="utf-8")
    title = src.split('title=if(state.session==null', 1)[1].split('hasSession=', 1)[0]
    for name in ('"Vehicles"', '"VCI / Devices"', '"Diagnostic"', '"Live Data"', '"AI Analysis"'):
        assert name in title


def test_ios_dashboard_status_is_server_backed():
    src = IOS.read_text(encoding="utf-8")
    dashboard = src.split("private var demoHome:", 1)[1].split("private func demoMetric", 1)[0]
    assert "viewModel.session?.state" in dashboard
    assert "viewModel.session?.dtcs.count" in dashboard
    assert "viewModel.session?.hypotheses.count" in dashboard


def test_ios_dashboard_diagnostics_and_vci_shortcuts_route_to_existing_screens():
    src = IOS.read_text(encoding="utf-8")
    dashboard = src.split("private var demoHome:", 1)[1].split("private func demoMetric", 1)[0]
    assert "tab = 1" in dashboard
    assert "tab = 3" in dashboard
    assert "case 1: diagnosticView" in src
    assert "viewModel.identifyObdWifi" in src
    assert "case 11: inputsView" in src
    assert "case 3: obdView" in src
