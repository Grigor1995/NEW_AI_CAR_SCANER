"""Global JSON ENV precedence and direct entrypoint integration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from shared import environment


def write(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'version': 1, 'environment': values}, ensure_ascii=False), encoding='utf-8')
    return path


def test_json_layers_and_process_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(environment, 'PROJECT', tmp_path)
    write(tmp_path / 'config/environment.json', {'PORT': 8001, 'LOCAL_ONLY': True, 'TEXT': 'Հայերեն'})
    write(tmp_path / 'config/environment.local.json', {'PORT': 9001})
    explicit = write(tmp_path / 'custom.json', {'PORT': 9002, 'FLAG': False})
    env = {'AI_CAR_ENV_CONFIG': str(explicit), 'PORT': '9999'}
    assert environment.environment_values(environ=env)['PORT'] == '9002'
    environment.apply_environment(env)
    assert env['PORT'] == '9999' and env['FLAG'] == '0' and env['LOCAL_ONLY'] == '1'
    assert env['TEXT'] == 'Հայերեն'


@pytest.mark.parametrize('data', [[], {'version': 2, 'environment': {}}, {'version': 1, 'environment': []},
                                  {'version': 1, 'environment': {'bad-name': 'x'}},
                                  {'version': 1, 'environment': {'BAD': ['nested']}}])
def test_invalid_config_does_not_mutate_environment(tmp_path, monkeypatch, data):
    monkeypatch.setattr(environment, 'PROJECT', tmp_path)
    config = tmp_path / 'config/environment.json'
    config.parent.mkdir()
    config.write_text(json.dumps(data), encoding='utf-8')
    env = {'EXISTING': 'keep'}
    with pytest.raises(ValueError, match='Invalid environment'):
        environment.apply_environment(env)
    assert env == {'EXISTING': 'keep'}


def test_missing_explicit_file_fails(tmp_path):
    with pytest.raises(ValueError, match='not found'):
        environment.environment_values(environ={'AI_CAR_ENV_CONFIG': str(tmp_path / 'missing.json')})


@pytest.mark.parametrize('entry', ['desktop', 'backend'])
def test_direct_entrypoints_load_json_before_service_configuration(tmp_path, entry):
    config = write(tmp_path / 'environment.json', {'AI_CAR_BACKEND_PORT': 9231, 'LOCAL_LLM_SERVER_PORT': 9232})
    env = os.environ.copy()
    env.pop('AI_CAR_BACKEND_PORT', None)
    env.pop('LOCAL_LLM_SERVER_PORT', None)
    env['AI_CAR_ENV_CONFIG'] = str(config)
    script = ('from apps.desktop import main; assert main.PORT == 9231; assert main.LLM_PORT == 9232' if entry == 'desktop'
              else 'import backend.api; import os; assert os.environ["AI_CAR_BACKEND_PORT"] == "9231"')
    subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1], env=env, check=True)
