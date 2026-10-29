import pytest
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("backend_check", Path(__file__).resolve().parents[2] / "scripts/check_local_backend.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
from apps.desktop import main
from unittest.mock import Mock


def test_temporary_log_lock_is_retried(monkeypatch, tmp_path):
    folder = tmp_path / 'check'
    folder.mkdir()
    monkeypatch.setattr(check.tempfile, 'mkdtemp', lambda **kwargs: str(folder))
    original = check.shutil.rmtree
    calls = []
    def locked_then_closed(path):
        calls.append(path)
        if len(calls) < 3:
            raise PermissionError('file handle still closing')
        original(path)
    monkeypatch.setattr(check.shutil, 'rmtree', locked_then_closed)
    monkeypatch.setattr(check.time, 'sleep', lambda _: None)
    with check.check_directory():
        (folder / 'backend.log').write_text('check')
    assert len(calls) == 3
    assert not folder.exists()


def test_cleanup_lock_preserves_original_check_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(check.tempfile, 'mkdtemp', lambda **kwargs: str(tmp_path))
    monkeypatch.setattr(check.shutil, 'rmtree', Mock(side_effect=PermissionError('locked')))
    monkeypatch.setattr(check.time, 'sleep', lambda _: None)
    with pytest.raises(ValueError, match='real check failed'):
        with check.check_directory():
            raise ValueError('real check failed')
    assert 'diagnostics retained' in capsys.readouterr().err
    assert tmp_path.exists()


def test_windows_stop_targets_only_owned_process_tree_and_closes_log(monkeypatch):
    process = Mock(pid=12345)
    process.poll.return_value = None
    log = Mock()
    taskkill = Mock()
    monkeypatch.setattr(main.sys, 'platform', 'win32')
    monkeypatch.setattr(main.subprocess, 'run', taskkill)
    monkeypatch.setattr(main, '_backend_process', process)
    monkeypatch.setattr(main, '_backend_log', log)
    main.stop_backend()
    assert taskkill.call_args.args[0] == ['taskkill', '/PID', '12345', '/T', '/F']
    process.wait.assert_called_once_with(timeout=5)
    log.close.assert_called_once()
    assert main._backend_log is None
