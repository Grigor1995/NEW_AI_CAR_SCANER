"""Check launcher database selection without importing servers or contacting a DB."""
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/run_platform_engine.py'


def launch(arguments, database_url):
    environ = dict(os.environ)
    environ.pop('DATABASE_URL', None)
    if database_url is not None:
        environ['DATABASE_URL'] = database_url
    code = '''import json, os, runpy, sys, types
sys.argv = [sys.argv[1]] + sys.argv[2:]
sys.modules['uvicorn'] = types.SimpleNamespace(run=lambda *a, **k: print(json.dumps({'database':os.environ.get('DATABASE_URL')})))
runpy.run_path(sys.argv[0], run_name='__main__')
'''
    return subprocess.run([sys.executable, '-c', code, str(SCRIPT), *arguments],
                          env=environ, capture_output=True, text=True)


def test_explicit_local_database_overrides_unavailable_inherited_postgres():
    result = launch(['--local-database'], 'postgresql://localhost/unavailable')
    assert result.returncode == 0, result.stderr
    selected = json.loads(result.stdout.splitlines()[-1])['database']
    assert selected.startswith('sqlite:///') and selected.endswith('/local/platform-engine.sqlite')
    assert 'this process only' in result.stdout


def test_default_preserves_configured_database():
    result = launch([], 'postgresql://localhost/unavailable')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['database'] == 'postgresql://localhost/unavailable'


def test_default_without_database_uses_local_sqlite():
    result = launch([], None)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['database'].endswith('/local/platform-engine.sqlite')


def test_local_and_ephemeral_are_mutually_exclusive():
    result = launch(['--local-database', '--ephemeral'], None)
    assert result.returncode == 2
    assert 'not allowed with argument' in result.stderr
