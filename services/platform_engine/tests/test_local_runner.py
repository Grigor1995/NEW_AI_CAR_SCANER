"""Clone-to-run contracts: no live installers, model downloads or device resets."""
import argparse
import hashlib
import importlib.util
from io import BytesIO
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import zipfile

import pytest

spec = importlib.util.spec_from_file_location('native_local_runner', Path(__file__).resolve().parents[1] / 'scripts/local_runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture
def local(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'PROJECT', tmp_path / 'finalbuild')
    monkeypatch.setattr(runner, 'TOOLS', tmp_path / '.build-tools/setup')
    monkeypatch.setattr(runner, 'STATE', tmp_path / '.runner-state.json')
    return tmp_path


class Response(BytesIO):
    def __init__(self, value, status=200, headers=None):
        super().__init__(value); self.status=status;self.headers=headers or {}
    def geturl(self): return 'https://downloads.test/artifact'


def write(path, data=b'test'):
    path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(data);return path


@pytest.mark.parametrize('url', ['file:///tmp/model', 'http://user:pass@host', 'http://host:0', 'http://[broken', 'http://host/?key=secret', 'http://host/#fragment'])
def test_api_url_rejects_non_backend_or_credential_urls(url):
    with pytest.raises(argparse.ArgumentTypeError):runner.api_url(url)


def test_download_resumes_and_checks_full_sha256(monkeypatch,tmp_path):
    target=tmp_path/'model.gguf';payload=b'GGUF verified model'
    write(target.with_name(target.name+'.part'),payload[:4])
    def opened(request,timeout):
        assert request.get_header('Range')=='bytes=4-'
        return Response(payload[4:],206,{'Content-Range':f'bytes 4-{len(payload)-1}/{len(payload)}'})
    monkeypatch.setattr(runner.urllib.request,'urlopen',opened)
    runner.download('https://downloads.test/model',target,hashlib.sha256(payload).hexdigest(),size=len(payload))
    assert target.read_bytes()==payload
    assert not target.with_name(target.name+'.part').exists()


def test_server_ignoring_range_restarts_instead_of_appending(monkeypatch,tmp_path):
    target=tmp_path/'runtime.zip';write(target.with_name('runtime.zip.part'),b'partial')
    monkeypatch.setattr(runner.urllib.request,'urlopen',lambda *a,**k:Response(b'complete',200))
    runner.download('https://downloads.test/a',target,hashlib.sha256(b'complete').hexdigest(),size=8)
    assert target.read_bytes()==b'complete'


def test_corrupt_complete_partial_restarts_and_existing_user_file_is_kept(monkeypatch,tmp_path):
    target=tmp_path/'sdk.zip';write(target.with_name('sdk.zip.part'),b'bad')
    def opened(request,timeout):
        assert request.get_header('Range') is None
        return Response(b'new')
    monkeypatch.setattr(runner.urllib.request,'urlopen',opened)
    runner.download('https://downloads.test/a',target,hashlib.sha256(b'new').hexdigest(),size=3)
    with pytest.raises(runner.SetupError,match='kept'):
        runner.download('https://downloads.test/a',target,'0'*64,size=3)
    assert target.read_bytes()==b'new'


def test_checksum_failure_never_promotes_download(monkeypatch,tmp_path):
    target=tmp_path/'jdk.zip'
    monkeypatch.setattr(runner.urllib.request,'urlopen',lambda *a,**k:Response(b'corrupt'))
    with pytest.raises(runner.SetupError,match='Checksum mismatch'):
        runner.download('https://downloads.test/a',target,'0'*64)
    assert not target.exists() and not target.with_name('jdk.zip.part').exists()


@pytest.mark.parametrize('name',['../outside','C:/outside','..\\outside'])
def test_archive_extraction_rejects_external_paths(tmp_path,name):
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as file:file.writestr(name,b'bad')
    with pytest.raises(runner.SetupError,match='Unsafe archive'):runner.extract_zip(archive,tmp_path/'extract')


def test_archive_preserves_complete_runtime_directory(tmp_path):
    archive=tmp_path/'runtime.zip'
    with zipfile.ZipFile(archive,'w') as file:
        file.writestr('runtime/llama-server.exe',b'exe');file.writestr('runtime/ggml.dll',b'dll')
    runner.extract_zip(archive,tmp_path/'extract')
    assert (tmp_path/'extract/runtime/ggml.dll').read_bytes()==b'dll'


def test_existing_model_is_reused_without_network_or_copy(local,monkeypatch):
    model=write(local/'existing model.gguf',b'GGUFweights')
    fetch=Mock();monkeypatch.setattr(runner,'fetch_json',fetch)
    assert runner.ensure_model(model)==model
    fetch.assert_not_called()
    assert not (runner.PROJECT/'models').exists()


def test_unverifiable_model_metadata_cannot_report_success(local,monkeypatch):
    monkeypatch.setattr(runner,'fetch_json',lambda *a:{'sha':'a'*40,'siblings':[{'rfilename':runner.MODEL_NAME}]})
    with pytest.raises(runner.SetupError,match='verifiable'):runner.ensure_model()


def test_sdk_archive_selection_uses_known_java_tools_and_checksum():
    raw=b'<sdk><remotePackage path="cmdline-tools;19.0"><archives><archive><host-os>windows</host-os><complete><url>tools.zip</url><checksum>aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</checksum><size>123</size></complete></archive></archives></remotePackage></sdk>'
    assert runner.sdk_tools_metadata(raw,'windows')==('https://dl.google.com/android/repository/tools.zip','a'*40,123)
    with pytest.raises(runner.SetupError):runner.sdk_tools_metadata(raw,'linux')


@pytest.mark.parametrize('accept',[True,False])
def test_sdk_license_acceptance_is_explicit_and_incomplete_install_fails(local,accept):
    sdk=local/'sdk';write(sdk/'cmdline-tools/19.0/lib/sdkmanager-classpath.jar')
    tool=Mock()
    with pytest.raises(runner.SetupError,match='incomplete'):
        runner.ensure_sdk(sdk,local/'jdk',accept,tool)
    assert len(tool.run.call_args_list)==2
    assert tool.run.call_args_list[0].kwargs['input_text']==('y\n'*100 if accept else None)
    assert '--licenses' in tool.run.call_args_list[0].args[0]


def test_setup_lock_is_exclusive_and_released_after_error(local):
    with pytest.raises(RuntimeError,match='interrupted'):
        with runner.setup_lock():
            with pytest.raises(runner.SetupError,match='lock exists'):
                with runner.setup_lock():pass
            raise RuntimeError('interrupted')
    assert not (runner.TOOLS/'setup.lock').exists()


def setup_args(**changes):
    args=dict(port=8001,api_url=None,skip_ai=False,skip_android=False,model=None,llama_dir=None,java_home=None,android_sdk=None,accept_android_licenses=True,skip_android_build=False,with_tests=False,run=False)
    args.update(changes);return SimpleNamespace(**args)


def test_full_setup_records_paths_and_builds_without_global_environment_changes(local,monkeypatch):
    monkeypatch.setattr(runner,'require_python',lambda:None)
    monkeypatch.setattr(runner,'setup_python',lambda *a:str(local/'.venv/python'))
    monkeypatch.setattr(runner,'ensure_model',lambda *a:local/'model.gguf')
    monkeypatch.setattr(runner,'ensure_llama',lambda *a:local/'runtime/llama-server.exe')
    monkeypatch.setattr(runner,'ensure_java',lambda *a:local/'jdk')
    monkeypatch.setattr(runner,'ensure_sdk',lambda *a:local/'sdk')
    built=Mock(return_value=local/'app.apk');monkeypatch.setattr(runner,'build_android',built)
    before=os.environ.copy()
    assert runner.setup(setup_args())==0
    state=runner.load_state()
    assert state['api_url']=='http://10.0.2.2:8001/' and state['apk']==str(local/'app.apk')
    assert os.environ==before and not (runner.TOOLS/'setup.lock').exists()
    assert built.call_count==1
    child=runner.child_env(state)
    assert child['JAVA_HOME']==str(local/'jdk') and child['LOCAL_LLM_MODEL_PATH']==str(local/'model.gguf')


def test_failed_install_never_writes_ready_state(local,monkeypatch,capsys):
    monkeypatch.setattr(runner,'require_python',lambda:None)
    monkeypatch.setattr(runner,'setup_python',Mock(side_effect=runner.SetupError('pip failed')))
    assert runner.main(['setup'])==1
    assert not runner.STATE.exists()
    assert '[READY]' not in capsys.readouterr().out
    assert not (runner.TOOLS/'setup.lock').exists()


def test_read_only_check_does_not_download_or_create_environment(local,monkeypatch):
    monkeypatch.setattr(runner,'existing_java',lambda *a:None)
    fetch=Mock();monkeypatch.setattr(runner,'fetch_json',fetch)
    assert runner.main(['check'])==2
    fetch.assert_not_called()
    assert not runner.TOOLS.exists() and not runner.STATE.exists()


def test_android_requires_healthy_backend_before_install_or_build(local,monkeypatch):
    monkeypatch.setattr(runner,'load_state',lambda:{'sdk':str(local/'sdk'),'java_home':str(local/'jdk'),'api_url':'http://10.0.2.2:8001/','port':8001})
    health=Mock(return_value=False);monkeypatch.setattr(runner,'health',health)
    build=Mock();monkeypatch.setattr(runner,'build_android',build)
    assert runner.main(['android'])==1
    health.assert_called_once_with('http://127.0.0.1:8001/')
    build.assert_not_called()


def test_android_configures_only_backend_preference_without_clearing_data(local,monkeypatch):
    state={'sdk':str(local/'sdk'),'java_home':str(local/'jdk'),'api_url':'http://10.0.2.2:8001/','port':8001}
    monkeypatch.setattr(runner,'load_state',lambda:dict(state))
    monkeypatch.setattr(runner,'health',lambda *a:True)
    monkeypatch.setattr(runner,'build_android',lambda *a,**k:local/'app.apk')
    adb=Mock(return_value=SimpleNamespace(stdout='List of devices attached\nemulator-5554\tdevice\n'))
    monkeypatch.setattr(runner,'adb_command',adb)
    assert runner.main(['android','--reverse'])==0
    args=[call.args[1:] for call in adb.call_args_list]
    assert ('reverse','tcp:8001','tcp:8001') in args
    assert not any('clear' in part for call in args for part in call)
    configured=next(call for call in adb.call_args_list if 'run-as' in call.args)
    assert 'http://127.0.0.1:8001' in configured.kwargs['input']
    assert configured.kwargs['serial']=='emulator-5554'


def test_gradle_invokes_java_directly_and_validates_output(local):
    state={'java_home':str(local/'JDK with spaces'),'sdk':str(local/'SDK with spaces'),'api_url':'http://10.0.2.2:8001/'}
    tool=Mock()
    with pytest.raises(runner.SetupError,match='expected debug APK'):runner.build_android(state,tool)
    command=tool.run.call_args.args[0]
    assert command[0].startswith(str(local/'JDK with spaces'))
    assert 'org.gradle.wrapper.GradleWrapperMain' in command and 'cmd.exe' not in command
    apk=write(runner.PROJECT/'apps/mobile-android/app/build/outputs/apk/debug/app-debug.apk',b'APK')
    assert runner.build_android(state,tool)==apk


def test_linked_partial_download_never_overwrites_user_file(local,monkeypatch):
    original=write(local/'important.txt',b'keep')
    partial=local/'model.gguf.part'
    try:partial.symlink_to(original)
    except OSError:pytest.skip('Symlinks unavailable')
    with pytest.raises(runner.SetupError,match='Linked'):
        runner.download('https://downloads.test/a',local/'model.gguf','0'*64)
    assert original.read_bytes()==b'keep'


def test_linked_runner_state_is_not_replaced(local):
    original=write(local/'important.txt',b'keep')
    try:runner.STATE.symlink_to(original)
    except OSError:pytest.skip('Symlinks unavailable')
    with pytest.raises(runner.SetupError,match='Linked'):runner.save_state({'port':8001})
    assert original.read_bytes()==b'keep'


def test_project_venv_is_actually_created_without_using_global_pip(local):
    import shutil
    import subprocess
    import sys
    interpreters=list(dict.fromkeys(filter(None,[sys.executable,shutil.which('python')])))
    python=next((candidate for candidate in interpreters if subprocess.run([candidate,'-c','import ensurepip'],capture_output=True).returncode==0),None)
    if python is None:pytest.skip('No interpreter with bundled ensurepip available')
    source_root=Path(__file__).resolve().parents[2]
    script = """
import sys,subprocess
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,sys.argv[2])
from finalbuild.scripts import local_runner as runner
runner.ROOT=Path(sys.argv[1]);runner.PROJECT=runner.ROOT/'finalbuild';runner.PROJECT.mkdir()
tool=Mock();interpreter=runner.setup_python(tool)
result=subprocess.run([interpreter,'-m','pip','--version'],check=True,capture_output=True,text=True)
assert str(runner.ROOT/'.venv') in result.stdout
assert all(call.args[0][0]==interpreter for call in tool.run.call_args_list)
print(result.stdout)
"""
    result=subprocess.run([python,'-c',script,str(local),str(source_root)],check=True,capture_output=True,text=True)
    assert str(local/'.venv') in result.stdout


def test_incomplete_environment_is_kept_instead_of_overwritten(local):
    marker=write(local/'.venv/personal.txt',b'keep')
    with pytest.raises(runner.SetupError,match='incomplete'):runner.setup_python(Mock())
    assert marker.read_bytes()==b'keep'


def test_interrupted_response_keeps_resumable_bytes(monkeypatch,tmp_path):
    import http.client
    class Broken(Response):
        def __init__(self):super().__init__(b'GGUF')
        def read(self,*args):
            if self.tell()==0:return super().read(*args)
            raise http.client.IncompleteRead(b'',10)
    target=tmp_path/'weights.gguf'
    monkeypatch.setattr(runner.urllib.request,'urlopen',lambda *a,**k:Broken())
    with pytest.raises(runner.SetupError,match='Partial file kept'):
        runner.download('https://downloads.test/a',target,'0'*64,size=14)
    assert not target.exists()
    assert target.with_name('weights.gguf.part').read_bytes()==b'GGUF'


def test_test_enabled_setup_does_not_connect_to_inherited_database(local,monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql://do-not-touch')
    monkeypatch.setattr(runner,'require_python',lambda:None)
    monkeypatch.setattr(runner,'setup_python',lambda *a:str(local/'.venv/python'))
    tool=Mock();monkeypatch.setattr(runner,'Runner',lambda *a:tool)
    assert runner.setup(setup_args(skip_ai=True,skip_android=True,with_tests=True))==0
    assert len(tool.run.call_args_list)==2
    assert all('DATABASE_URL' not in call.kwargs['env'] for call in tool.run.call_args_list)
    assert os.environ['DATABASE_URL']=='postgresql://do-not-touch'
    assert not runner.load_state()['ai_enabled'] and not runner.load_state()['android_enabled']


def test_runner_sets_local_ai_endpoint_in_children_only(monkeypatch):
    monkeypatch.setenv('LOCAL_LLM_SERVER_URL','http://localhost:1234')
    child=runner.child_env({'ai_port':8000,'port':8001})
    assert child['LOCAL_LLM_SERVER_URL']=='http://localhost:1234'
    assert os.environ['LOCAL_LLM_SERVER_URL']=='http://localhost:1234'
    with pytest.raises(SystemExit):runner.main(['setup','--port','8000'])


def test_setup_releases_install_lock_before_opening_desktop(local,monkeypatch):
    def configured(args):
        assert (runner.TOOLS/'setup.lock').is_file()
        return 0
    def launched(args):
        assert not (runner.TOOLS/'setup.lock').exists()
        return 0
    monkeypatch.setattr(runner,'perform_setup',configured)
    monkeypatch.setattr(runner,'desktop',launched)
    assert runner.setup(setup_args(run=True))==0


def test_child_env_uses_global_json_then_process_override(local, monkeypatch):
    config = local / 'environment.json'
    config.write_text('{"version":1,"environment":{"LOCAL_LLM_SERVER_PORT":9222,"LOCAL_LLM_SERVER_THREADS":3}}')
    monkeypatch.setenv('AI_CAR_ENV_CONFIG', str(config))
    for key in ('LOCAL_LLM_SERVER_PORT', 'LOCAL_LLM_SERVER_URL', 'LOCAL_LLM_SERVER_THREADS'):
        monkeypatch.delenv(key, raising=False)
    child = runner.child_env({'ai_port': 8000})
    assert child['LOCAL_LLM_SERVER_PORT'] == '9222'
    assert child['LOCAL_LLM_SERVER_URL'] == 'http://127.0.0.1:9222'
    assert child['LOCAL_LLM_SERVER_THREADS'] == '3'
    monkeypatch.setenv('LOCAL_LLM_SERVER_THREADS', '5')
    assert runner.child_env({})['LOCAL_LLM_SERVER_THREADS'] == '5'
