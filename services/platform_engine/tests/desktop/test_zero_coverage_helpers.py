from __future__ import annotations

import sys
from types import SimpleNamespace

from PIL import Image

from apps.desktop import backend_worker, prepare_windows_icon


def test_backend_worker_uses_source_root_and_environment(monkeypatch, tmp_path):
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    monkeypatch.setattr(backend_worker, "__file__", str(tmp_path / "apps" / "desktop" / "backend_worker.py"))
    monkeypatch.setattr(backend_worker.sys, "frozen", False, raising=False)
    monkeypatch.setenv("AI_CAR_BACKEND_HOST", "0.0.0.0")
    monkeypatch.setenv("AI_CAR_BACKEND_PORT", "8123")
    monkeypatch.setenv("AI_CAR_BACKEND_LOG_LEVEL", "warning")
    calls = {}
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda *args, **kwargs: calls.update(args=args, kwargs=kwargs)))
    backend_worker.main()
    assert calls["args"] == ("api.main:app",)
    assert calls["kwargs"] == {"host": "0.0.0.0", "port": 8123, "log_level": "warning", "workers": 1}
    assert str(backend_dir) in sys.path


def test_backend_worker_uses_frozen_extraction_root(monkeypatch, tmp_path):
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    monkeypatch.setattr(backend_worker.sys, "frozen", True, raising=False)
    monkeypatch.setattr(backend_worker.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setenv("AI_CAR_BACKEND_PORT", "8001")
    calls = {}
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda *args, **kwargs: calls.update(kwargs=kwargs)))
    backend_worker.main()
    assert calls["kwargs"]["port"] == 8001
    assert str(backend_dir) in sys.path


def test_prepare_windows_icon_generates_and_validates_formats(monkeypatch, tmp_path, capsys):
    source = tmp_path / "launcher.webp"
    Image.effect_noise((512, 512), 80).convert("RGB").save(source, format="WEBP")
    webp = tmp_path / "desktop.webp"
    png = tmp_path / "desktop.png"
    ico = tmp_path / "desktop.ico"
    monkeypatch.setattr(prepare_windows_icon, "ANDROID_ICON", source)
    monkeypatch.setattr(prepare_windows_icon, "DESKTOP_WEBP", webp)
    monkeypatch.setattr(prepare_windows_icon, "DESKTOP_PNG", png)
    monkeypatch.setattr(prepare_windows_icon, "DESKTOP_ICO", ico)
    prepare_windows_icon.main()
    assert all(path.is_file() and path.stat().st_size >= 128 for path in (webp, png, ico))
    with Image.open(ico) as result:
        assert result.format == "ICO"
        assert result.width >= 16
    assert "Generated Desktop PNG" in capsys.readouterr().out


def test_prepare_windows_icon_fails_when_source_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(prepare_windows_icon, "ANDROID_ICON", tmp_path / "missing.webp")
    try:
        prepare_windows_icon.main()
    except FileNotFoundError as exc:
        assert "Android launcher icon not found" in str(exc)
    else:
        raise AssertionError("missing launcher icon must fail clearly")
