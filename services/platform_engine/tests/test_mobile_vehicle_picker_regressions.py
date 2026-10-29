"""Guard vehicle picker filtering and session cleanup behavior across native apps."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "apps/mobile-android/app/src/main/java/com/aicarscaner/mobile/presentation/DiagnosticScreen.kt"
IOS = ROOT / "apps/mobile-ios/AICarScanner/DiagnosticScreen.swift"
IOS_VM = ROOT / "apps/mobile-ios/AICarScanner/DiagnosticViewModel.swift"

def test_android_engine_selection_accepts_unknown_ecu():
    source = ANDROID.read_text(encoding="utf-8")
    body = source.split("fun applyRemoteEngine(value: String): Boolean {", 1)[1].split("\n    }", 1)[0]
    assert "if (ecus.isEmpty()) return false" not in body
    assert "ecu = ecus.firstOrNull().orEmpty()" in body

def test_ios_ecu_choices_follow_selected_year():
    source = IOS.read_text(encoding="utf-8")
    line = next(line for line in source.splitlines() if "private var ecus:[String]" in line)
    assert "String($0.year)==year" in line

def test_ios_clear_session_drops_stale_error():
    source = IOS_VM.read_text(encoding="utf-8")
    body = source.split("func clearSession() {", 1)[1].split("\n    }", 1)[0]
    assert "session = nil" in body
    assert "error = nil" in body
