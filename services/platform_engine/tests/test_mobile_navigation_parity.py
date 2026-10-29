"""Guard the mobile navigation labels against drifting from the Desktop sidebar."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "apps/mobile-ios/AICarScanner/DiagnosticScreen.swift"
ANDROID = ROOT / "apps/mobile-android/app/src/main/java/com/aicarscaner/mobile/presentation/DashboardNavigation.kt"

ORDER = ["Symptoms", "Diagnostic", "VCI / Devices", "Vehicles", "Live Data",
         "Tests", "AI Analysis", "DTC", "Reports", "Teach AI", "Dashboard"]


def test_android_dashboard_sections_follow_desktop_order():
    source = ANDROID.read_text(encoding="utf-8")
    section = source.split("val sections=listOf(", 1)[1].split("sections.chunked", 1)[0]
    positions = [section.index('"' + label + '"') for label in ORDER]
    assert positions == sorted(positions)
    assert section.index('"Symptoms"') < section.index('"Vehicles"')


def test_ios_navigation_has_stable_tab_ids_and_desktop_labels():
    source = IOS.read_text(encoding="utf-8")
    import re
    titles = dict((int(i), label) for i, label in re.findall(r'case (\d+):return t.tr\("([^"]+)"', source))
    titles[6] = "DTC"
    titles[7] = "Tests"  # iOS uses the expanded native label "Guided Tests".
    menu = source.split("private var desktopMenu:", 1)[1].split("private var demoHome:", 1)[0]
    defaults = source.split("private var orderedLauncherPages:", 1)[1].split("private func moveLauncherPage", 1)[0]
    ids = [int(i) for i in re.search(r'defaults:\[([\d,]+)\]', defaults).group(1).split(",")]
    assert "ForEach(orderedLauncherPages" in menu
    assert [titles[i] for i in ids[:len(ORDER)]] == ORDER
    assert "titles[index]" not in source
    assert "symbols[index]" not in source
