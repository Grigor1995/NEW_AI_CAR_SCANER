"""Cleanup must never reach tracked data, native outputs or linked directories."""
from pathlib import Path
import importlib.util
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('safe_repo_cleanup', Path(__file__).resolve().parents[1] / 'scripts/clean_repository.py')
clean = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = clean
spec.loader.exec_module(clean)


def write(root, relative):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('test')
    return path


def test_cleanup_preserves_user_files_builds_models_envs_and_tracked_caches(tmp_path):
    cache = write(tmp_path, 'apps/__pycache__/module.pyc')
    coverage = write(tmp_path, 'finalbuild/.coverage')
    preserved = [write(tmp_path, relative) for relative in [
        'build/__pycache__/packaged.pyc', '.venv/__pycache__/installed.pyc',
        '.build-tools/desktop-venv/__pycache__/installed.pyc',
        'artifacts/run/.coverage', 'models/.coverage', 'assets/.coverage',
        'desktop-test-reports/summary.json', 'backend.log', 'notes.tmp',
        'fixtures/__pycache__/tracked.pyc',
    ]]
    plan = clean.candidates(tmp_path, frozenset({'fixtures/__pycache__/tracked.pyc'}))
    assert {c.path for c in plan} == {cache.parent, coverage}
    for candidate in plan: clean.remove(tmp_path, candidate)
    assert not cache.exists() and not coverage.exists()
    assert all(path.exists() for path in preserved)


def test_directory_links_and_links_inside_caches_do_not_remove_targets(tmp_path):
    outside = tmp_path / 'external'
    outside.mkdir()
    important = write(outside, 'notes.txt')
    root = tmp_path / 'repo'; root.mkdir()
    try: (root / '__pycache__').symlink_to(outside, target_is_directory=True)
    except OSError: pytest.skip('Symlinks unavailable')
    assert clean.candidates(root, frozenset()) == []
    with pytest.raises(ValueError): clean.remove(root, clean.Candidate(root / '__pycache__', 0))
    (root / '__pycache__').unlink()
    write(root, '__pycache__/module.pyc')
    (root / '__pycache__/linked').symlink_to(outside, target_is_directory=True)
    plan = clean.candidates(root, frozenset())
    assert plan[0].bytes == 4
    clean.remove(root, plan[0])
    assert important.read_text() == 'test'


def test_cleanup_rejects_root_and_external_candidates(tmp_path):
    root = tmp_path / 'repo'; root.mkdir()
    external = write(tmp_path, 'outside.txt')
    for path in (root, external):
        with pytest.raises(ValueError): clean.remove(root, clean.Candidate(path, 4))
    assert external.exists()


def test_preview_is_default_and_apply_removes_only_proposed_cache(monkeypatch, tmp_path, capsys):
    write(tmp_path, '__pycache__/code.pyc')
    monkeypatch.setattr(clean, 'ROOT', tmp_path)
    monkeypatch.setattr(clean, 'tracked_paths', lambda _: frozenset())
    assert clean.main([]) == 0
    assert (tmp_path / '__pycache__').exists()
    assert 'Preview:' in capsys.readouterr().out
    assert clean.main(['--apply']) == 0
    assert not (tmp_path / '__pycache__').exists()
    assert 'Removed:' in capsys.readouterr().out


def test_git_tracked_cache_remains_protected(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    path = write(tmp_path, '.coverage.fixture')
    subprocess.run(['git', '-C', str(tmp_path), 'add', str(path)], check=True)
    assert clean.tracked_paths(tmp_path) == frozenset({'.coverage.fixture'})
    assert clean.candidates(tmp_path, clean.tracked_paths(tmp_path)) == []
