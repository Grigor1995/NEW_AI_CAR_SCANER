"""Installer lifecycle and download-boundary regressions without Windows mutations."""
import importlib.util
import hashlib
import subprocess
import urllib.error
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

BASE = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load('windows_installer', BASE / 'installer/windows/windows_installer.py')
builder = load('installer_builder', BASE / 'scripts/build_windows_installer.py')
SHA = 'a' * 40


def snapshot(extra=None, runner_code=None):
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        files = {'runner.py': runner_code or '', 'finalbuild/scripts/local_runner.py': '', 'finalbuild/requirements.txt': ''}
        files.update(extra or {})
        for name, value in files.items():
            archive.writestr(f'AI-CAR-SCANER-{SHA}/{name}', value)
    return stream.getvalue()


class Download(BytesIO):
    def geturl(self):
        return 'https://codeload.github.com/'


def args(tmp_path, with_ai=False):
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'repository': helper.REPOSITORY, 'commit': SHA}), encoding='utf-8')
    return SimpleNamespace(root=tmp_path / 'install', manifest=manifest, with_ai=with_ai)


@pytest.mark.parametrize('repository,commit', [('attacker/repo', SHA), (helper.REPOSITORY, 'main'), (helper.REPOSITORY, '../bad')])
def test_invalid_source_cannot_create_installation(tmp_path, repository, commit):
    config = args(tmp_path)
    config.manifest.write_text(json.dumps({'repository': repository, 'commit': commit}))
    with pytest.raises(ValueError):
        helper.install(config)
    assert not config.root.exists()


def test_existing_personal_directory_is_preserved(tmp_path):
    root = tmp_path / 'work'
    root.mkdir()
    source = root / 'precious.py'
    source.write_text('mine')
    with pytest.raises(ValueError, match='empty'):
        helper.claim_root(root)
    assert source.read_text() == 'mine'
    assert not (root / helper.MARKER).exists()


@pytest.mark.parametrize('entry', ['../escape.py', 'nested/../../escape.py', 'C:/escape.py', '..\\escape.py'])
def test_unsafe_zip_is_rejected_before_extraction(tmp_path, entry):
    archive = tmp_path / 'source.zip'
    archive.write_bytes(snapshot({entry: 'bad'}))
    with pytest.raises(ValueError, match='Unsafe'):
        helper.extract_source(archive, tmp_path / 'stage', SHA)
    assert not (tmp_path / 'stage').exists()


def test_zip_symlink_cannot_escape_staging(tmp_path):
    archive = tmp_path / 'source.zip'
    with zipfile.ZipFile(archive, 'w') as source:
        item = zipfile.ZipInfo(f'AI-CAR-SCANER-{SHA}/link')
        item.external_attr = 0o120777 << 16
        source.writestr(item, '../outside')
    with pytest.raises(ValueError, match='Unsafe'):
        helper.extract_source(archive, tmp_path / 'stage', SHA)


def test_source_upgrade_preserves_local_model_and_environment_but_removes_obsolete_code(tmp_path):
    checkout = tmp_path / 'new'
    checkout.mkdir()
    (checkout / 'runner.py').write_text('new')
    repository = tmp_path / 'repo'
    for name in ('.venv/Scripts/python.exe', 'finalbuild/models/car.gguf', '.runner-state.json', 'obsolete.py'):
        target = repository / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('keep')
    files = helper.promote_source(checkout, repository, ['runner.py', 'obsolete.py'])
    assert files == ['runner.py']
    assert not (repository / 'obsolete.py').exists()
    assert (repository / '.venv/Scripts/python.exe').read_text() == 'keep'
    assert (repository / 'finalbuild/models/car.gguf').read_text() == 'keep'
    assert (repository / '.runner-state.json').read_text() == 'keep'


def test_reclaim_does_not_erase_ownership_manifest(tmp_path):
    root = helper.claim_root(tmp_path / 'install')
    marker = root / helper.MARKER
    marker.write_text(json.dumps({'owner': helper.OWNER, 'files': ['obsolete.py'], 'ready': True}))
    helper.claim_root(root)
    assert json.loads(marker.read_text())['files'] == ['obsolete.py']


@pytest.mark.parametrize('with_ai', [False, True])
def test_real_setup_subprocess_records_selected_ai_and_can_retry_failed_install(tmp_path, monkeypatch, with_ai):
    config = args(tmp_path, with_ai)
    payload = snapshot(runner_code='raise SystemExit(9)')
    monkeypatch.setattr(helper.urllib.request, 'urlopen', lambda *a, **k: Download(payload))
    with pytest.raises(RuntimeError, match='failed'):
        helper.install(config)
    marker = config.root / helper.MARKER
    assert json.loads(marker.read_text())['ready'] is False
    assert list((config.root / 'logs').glob('setup-*.log'))
    # A real subprocess validates setup arguments, without invoking pip/network.
    payload = snapshot(runner_code='''from pathlib import Path
import json, sys
assert sys.argv[1:3] == ['setup', '--skip-android']
ai = '--skip-ai' not in sys.argv
p = Path('.venv/Scripts/pythonw.exe')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_bytes(b'pythonw')
Path('.runner-state.json').write_text(json.dumps({'ai_enabled': ai}))
print('configured')
''')
    assert helper.install(config) == 0
    installed = json.loads(marker.read_text())
    assert installed['ready'] is True and installed['ai_enabled'] is with_ai
    assert json.loads((config.root / 'repo/.runner-state.json').read_text())['ai_enabled'] is with_ai
    assert not list(config.root.glob('ai-car-source-*'))


def test_launch_uses_saved_runner_and_no_console_and_propagates_failure(tmp_path, monkeypatch):
    root = helper.claim_root(tmp_path / 'install')
    (root / helper.MARKER).write_text(json.dumps({'owner': helper.OWNER, 'ready': True}))
    (root / 'logs').mkdir()
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=7)
    monkeypatch.setattr(helper.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='code 7'):
        helper.launch(SimpleNamespace(root=root))
    command, options = calls[0]
    assert command[-1] == 'desktop' and command[1].endswith('runner.py')
    assert options['cwd'] == root / 'repo'
    assert options['env']['PYTHONUTF8'] == '1'
    assert 'creationflags' in options


def fake_export(commit, destination):
    data = snapshot()
    destination.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_prepared_payload_pins_source_and_includes_real_app_icon(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'export_snapshot', fake_export)
    payload = builder.prepare(tmp_path, SHA)
    assert helper.manifest_data(payload / 'manifest.json')['commit'] == SHA
    assert (payload / 'app.ico').read_bytes().startswith(b'\x00\x00\x01\x00')
    assert (payload / 'bootstrap.ps1').is_file()
    assert (payload / 'windows_installer.py').is_file()
    assert (payload / 'AI-Car-Scanner.iss').is_file()


def test_builder_rejects_unpinned_commit_without_output(tmp_path):
    with pytest.raises(ValueError):
        builder.prepare(tmp_path / 'output', 'main')
    assert not (tmp_path / 'output').exists()


def test_linked_checkout_is_not_modified(tmp_path):
    config = args(tmp_path)
    root = helper.claim_root(config.root)
    outside = tmp_path / 'development'
    outside.mkdir()
    try:
        (root / 'repo').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Symlink creation is unavailable')
    with pytest.raises(ValueError, match='linked repository'):
        helper.install(config)
    assert not list(outside.iterdir())


def test_compiled_artifact_has_verified_checksum_and_pinned_arguments(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'export_snapshot', fake_export)
    compiler = tmp_path / 'ISCC.exe'
    compiler.write_bytes(b'compiler')
    monkeypatch.setattr(builder.platform, 'system', lambda: 'Windows')
    calls = []
    def compile_installer(command, check):
        calls.append(command)
        output = tmp_path / 'output/dist/AI-Car-Scanner-Setup.exe'
        output.write_bytes(b'MZ fake test executable')
    monkeypatch.setattr(builder.subprocess, 'run', compile_installer)
    assert builder.main(['--commit', SHA, '--iscc', str(compiler), '--output', str(tmp_path / 'output')]) == 0
    checksum = (tmp_path / 'output/dist/AI-Car-Scanner-Setup.exe.sha256').read_text()
    import hashlib
    assert checksum.startswith(hashlib.sha256(b'MZ fake test executable').hexdigest())
    assert '/DAppVersion=1.0-' + SHA[:8] in calls[0]
    assert json.loads((tmp_path / 'output/payload/manifest.json').read_text())['commit'] == SHA


@pytest.mark.parametrize('payload', [b'', b'not a model'])
def test_invalid_local_model_rejected_before_download(tmp_path, monkeypatch, payload):
    config = args(tmp_path, True)
    config.model = tmp_path / 'bad.gguf'
    config.model.write_bytes(payload)
    def forbidden(*a, **kw):
        raise AssertionError('No download for an invalid local model')
    monkeypatch.setattr(helper.urllib.request, 'urlopen', forbidden)
    with pytest.raises(ValueError, match='GGUF'):
        helper.install(config)
    assert not config.root.exists()


def test_local_model_forwarded_without_copy_and_global_config_written(tmp_path, monkeypatch):
    config = args(tmp_path, True)
    config.model = tmp_path / 'իմ մոդել with spaces.gguf'
    config.model.write_bytes(b'GGUF owned original')
    code = '''import json,sys
from pathlib import Path
assert '--skip-ai' not in sys.argv
model = sys.argv[sys.argv.index('--model')+1]
assert Path(model).read_bytes() == b'GGUF owned original'
p = Path('.venv/Scripts/pythonw.exe')
p.parent.mkdir(parents=True,exist_ok=True)
p.write_bytes(b'pythonw')
Path('.runner-state.json').write_text(json.dumps({'model':model,'llama':'runtime/llama-server.exe','ai_enabled':True}))
'''
    data = snapshot(runner_code=code)
    monkeypatch.setattr(helper.urllib.request, 'urlopen', lambda *a, **kw: Download(data))
    assert helper.install(config) == 0
    values = json.loads((config.root / 'environment.json').read_text(encoding='utf-8'))['environment']
    assert values['LOCAL_LLM_MODEL_PATH'] == str(config.model.resolve())
    assert values['AI_CAR_DISABLE_LLM_AUTOSTART'] is False
    assert not list((config.root / 'repo').rglob('*.gguf'))
    assert config.model.read_bytes() == b'GGUF owned original'


def test_global_config_preserves_custom_env_when_ai_choice_changes(tmp_path):
    root = tmp_path / 'install'
    root.mkdir()
    config = root / 'environment.json'
    config.write_text(json.dumps({'version': 1, 'environment': {'LOCAL_LLM_SERVER_THREADS': 4, 'API_KEY': 'private'}}))
    helper.save_global_config(root, root / 'repo', {}, False)
    values = json.loads(config.read_text())['environment']
    assert values['LOCAL_LLM_SERVER_THREADS'] == 4 and values['API_KEY'] == 'private'
    assert values['AI_CAR_DISABLE_LLM_AUTOSTART'] is True


def bundled_config(tmp_path, contents):
    config = args(tmp_path)
    config.source_archive = tmp_path / 'source.zip'
    config.source_archive.write_bytes(contents)
    config.manifest.write_text(json.dumps({'repository': helper.REPOSITORY, 'commit': SHA,
        'source_mode': 'bundled', 'source_sha256': hashlib.sha256(contents).hexdigest()}))
    return config


def test_bundled_source_installs_without_github_access(tmp_path, monkeypatch):
    code = '''from pathlib import Path
p = Path('.venv/Scripts/pythonw.exe')
p.parent.mkdir(parents=True,exist_ok=True)
p.write_bytes(b'pythonw')
Path('.runner-state.json').write_text('{"ai_enabled":false}')
'''
    config = bundled_config(tmp_path, snapshot(runner_code=code))
    def forbidden(*a, **kw):
        raise AssertionError('Bundled installer must not request the private GitHub repository')
    monkeypatch.setattr(helper.urllib.request, 'urlopen', forbidden)
    assert helper.install(config) == 0
    assert json.loads((config.root / helper.MARKER).read_text())['ready'] is True


def test_damaged_bundled_source_cannot_be_promoted(tmp_path):
    config = bundled_config(tmp_path, snapshot())
    config.source_archive.write_bytes(b'damaged')
    with pytest.raises(ValueError, match='checksum mismatch'):
        helper.install(config)
    assert not (config.root / 'repo').exists()


def test_online_404_has_actionable_error_for_wizard(tmp_path, monkeypatch):
    config = args(tmp_path)
    def unavailable(request, **kwargs):
        raise urllib.error.HTTPError(request.full_url, 404, 'Not Found', {}, None)
    monkeypatch.setattr(helper.urllib.request, 'urlopen', unavailable)
    status = tmp_path / 'installer-error.txt'
    assert helper.main(['install', '--root', str(config.root), '--manifest', str(config.manifest), '--error-file', str(status)]) == 1
    text = status.read_text(encoding='utf-8')
    assert 'HTTP 404' in text and 'private' in text and 'python installer.py' in text
    assert (config.root / 'logs/bootstrap-errors.log').is_file()


def test_online_only_rebuild_removes_stale_bundled_source(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'export_snapshot', fake_export)
    payload = builder.prepare(tmp_path, SHA)
    assert (payload / 'source.zip').is_file()
    builder.prepare(tmp_path, SHA, online_only=True)
    assert not (payload / 'source.zip').exists()
    assert json.loads((payload / 'manifest.json').read_text())['source_mode'] == 'online'


def test_real_git_archive_excludes_untracked_files_and_git_metadata(tmp_path, monkeypatch):
    repository = tmp_path / 'checkout'
    repository.mkdir()
    def git(*arguments):
        return subprocess.check_output(['git', *arguments], cwd=repository, stderr=subprocess.DEVNULL, text=True).strip()
    git('init')
    (repository / 'source.py').write_text('tracked source')
    (repository / 'private.env').write_text('untracked private value')
    git('add', 'source.py')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--no-gpg-sign', '-m', 'Fixture')
    commit = git('rev-parse', 'HEAD')
    monkeypatch.setattr(builder, 'ROOT', repository)
    archive = tmp_path / 'snapshot.zip'
    digest = builder.export_snapshot(commit, archive)
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        assert 'AI-CAR-SCANER-' + commit + '/source.py' in names
        assert not any('private.env' in name or '/.git/' in name for name in names)
