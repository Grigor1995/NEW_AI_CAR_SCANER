"""Regression tests for Windows SQLite file-lock handling in the API probe."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "test_fastapi_startup.py"
spec = importlib.util.spec_from_file_location("fastapi_startup_cleanup_under_test", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_temp_cleanup_retries_transient_windows_file_lock(tmp_path, monkeypatch):
    folder = tmp_path / "temporary_sqlite"
    folder.mkdir()
    (folder / "diagnostic.sqlite").write_bytes(b"sqlite")
    real_remove = probe.shutil.rmtree
    calls = []

    def intermittently_locked(path):
        calls.append(path)
        if len(calls) < 3:
            raise PermissionError(32, "SQLite file still open", str(path))
        return real_remove(path)

    monkeypatch.setattr(probe.shutil, "rmtree", intermittently_locked)
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    probe.cleanup_temporary_database(folder)
    assert len(calls) == 3
    assert not folder.exists()


def test_temp_cleanup_exposes_persistent_lock(tmp_path, monkeypatch):
    folder = tmp_path / "locked"
    folder.mkdir()
    monkeypatch.setattr(probe.shutil, "rmtree", lambda path: (_ for _ in ()).throw(PermissionError(32, "still locked", str(path))))
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    with pytest.raises(PermissionError):
        probe.cleanup_temporary_database(folder, attempts=3)
    assert folder.exists()


def test_startup_probe_records_failure_instead_of_traceback_on_cleanup_lock(
    monkeypatch, tmp_path,
):
    report_folder = tmp_path / "report"
    monkeypatch.setattr(probe, "OUT", report_folder)
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    temp_folder = tmp_path / "owned_temp"
    temp_folder.mkdir()
    monkeypatch.setattr(probe.tempfile, "mkdtemp", lambda **_kwargs: str(temp_folder))
    monkeypatch.setattr(probe, "ephemeral_port", lambda: 39811)
    monkeypatch.setattr(probe, "is_healthy", lambda port: True)
    monkeypatch.setattr(probe, "stop_child", lambda process, frozen: None)
    monkeypatch.setattr(probe, "cleanup_temporary_database", lambda folder: (_ for _ in ()).throw(PermissionError(32, "locked", str(folder))))

    class FakePopen:
        def __init__(self, *_args, **_kwargs):
            self.pid = 12345

        def poll(self):
            return None

    monkeypatch.setattr(probe.subprocess, "Popen", FakePopen)
    result = probe.run_probe("source", None, 5)
    saved = json.loads((report_folder / "source.json").read_text(encoding="utf-8"))
    assert result == saved
    assert result["status"] == "FAIL"
    assert result["cleanup"] == "FAIL"
    assert result["health"] is True  # /health succeeded; only cleanup failed
    assert "locked" in result["error"]
    assert result["temporary_directory_if_locked"] == str(temp_folder)


@pytest.mark.skipif(probe.sys.platform != "win32", reason="Windows process tree only")
def test_windows_cleanup_targets_owned_pid_and_descendants(monkeypatch):
    calls = []
    class StubProcess:
        pid = 42125
        def poll(self):
            return None
        def wait(self, timeout):
            calls.append(("wait", timeout))
        def kill(self):
            raise AssertionError("taskkill should have handled the tree")

    def fake_run(cmd, **kwargs):
        calls.append(("taskkill", cmd))
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(probe.subprocess, "run", fake_run)
    probe.stop_child(StubProcess(), frozen=False)
    assert calls[0] == ("taskkill", ["taskkill", "/PID", "42125", "/T", "/F"])
    assert calls[1] == ("wait", 12)
