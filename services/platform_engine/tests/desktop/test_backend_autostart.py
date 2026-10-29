from __future__ import annotations

from types import SimpleNamespace

import apps.desktop.main as desktop_main


def test_start_backend_reuses_healthy_backend(monkeypatch):
    monkeypatch.setattr(desktop_main, "_backend_healthy", lambda: True)
    monkeypatch.setattr(desktop_main, "_is_port_open", lambda _host, _port: False)

    assert desktop_main.start_backend() is None


def test_start_backend_skips_local_process_for_remote_backend(monkeypatch):
    monkeypatch.setattr(desktop_main, "LOCAL_BACKEND", False)
    monkeypatch.setattr(desktop_main.subprocess, "Popen", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not spawn local backend")))
    assert desktop_main.start_backend() is None


def test_start_backend_uses_current_python_and_backend_path(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_main, "LOCAL_BACKEND", True)
    calls = {}
    log_path = tmp_path / "backend.log"

    monkeypatch.setattr(desktop_main, "_backend_healthy", lambda: False)
    monkeypatch.setattr(desktop_main, "_is_port_open", lambda _host, _port: False)
    monkeypatch.setattr(desktop_main, "_log_path", lambda: log_path)
    monkeypatch.setattr(desktop_main, "_STARTUP_TIMEOUT", 0.1)

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=None,
            poll=lambda: 0,
            terminate=lambda: None,
            wait=lambda **_k: None,
            kill=lambda: None,
        )

    monkeypatch.setattr(desktop_main.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(desktop_main.time, "sleep", lambda _seconds: None)

    try:
        desktop_main.start_backend()
    except RuntimeError:
        pass

    # A child that exits during startup must not leave its file handle open.
    assert desktop_main._backend_log is None
    assert desktop_main._backend_process is None

    assert calls["command"] == [
        desktop_main.sys.executable,
        "-m",
        "apps.desktop.backend_worker",
    ]
    env = calls["kwargs"]["env"]
    assert str(desktop_main.ROOT / "backend") in env["PYTHONPATH"].split(desktop_main.os.pathsep)
    assert calls["kwargs"]["cwd"] == str(desktop_main.ROOT)
