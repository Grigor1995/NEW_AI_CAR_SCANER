from pathlib import Path


def test_standalone_specs_exist():
    root = Path(__file__).resolve().parents[2]
    assert (root / "apps" / "desktop" / "specs" / "AICarScanner.spec").exists()
    assert (root / "apps" / "desktop" / "specs" / "backend_service.spec").exists()


def test_desktop_main_references_backend_service():
    root = Path(__file__).resolve().parents[2]
    text = (root / "apps" / "desktop" / "main.py").read_text()
    assert "backend_service.exe" in text
    assert 'getattr(sys, "frozen", False)' in text


def test_build_script_is_present():
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "build_windows_standalone.ps1"
    text = script.read_text()
    assert script.exists()
    assert "backend_service.spec" in text
    assert "AICarScanner.spec" in text



def test_canonical_gui_spec_loads_early_qtcore_before_pyinstaller_qt_hook():
    """Regression guard for the Windows Python 3.14 frozen startup crash."""
    root = Path(__file__).resolve().parents[2]
    spec = (root / "apps" / "desktop" / "specs" / "AICarScanner.spec").read_text(encoding="utf-8")
    hook = root / "apps" / "desktop" / "qt_early_runtime_hook.py"

    assert hook.is_file()
    assert "qt_early_runtime_hook.py" in spec
    assert "from PySide6 import QtCore" in hook.read_text(encoding="utf-8")



def test_windows_spec_consumes_staged_icon_assets_without_overwriting_tracked_png():
    root = Path(__file__).resolve().parents[2]
    spec = (root / "apps" / "desktop" / "specs" / "AICarScanner.spec").read_text(encoding="utf-8")
    bash = (root / "scripts" / "build_desktop_git_bash.sh").read_text(encoding="utf-8")

    assert "AI_CAR_ICON_STAGE_DIR" in spec
    assert "stage_windows_icons.py" in bash
    assert "AI_CAR_VERIFY_ASSET_DIR" in bash
    assert "prepare_windows_icon.py" not in spec
    assert "prepare_windows_icon.py" not in bash
