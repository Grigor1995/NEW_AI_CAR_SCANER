"""Build orchestration contracts without invoking external SDKs or installers."""
from __future__ import annotations

from argparse import Namespace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import importlib.util

spec = importlib.util.spec_from_file_location("unified_native_build", Path(__file__).resolve().parents[1] / "scripts/build_all.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def arguments(tmp_path, **overrides):
    values = dict(targets=list(build.TARGETS), output=tmp_path / "artifacts", check=False,
                  skip_unavailable=False, with_tests=False, no_install=True)
    values.update(overrides)
    return Namespace(**values)


def summary(tmp_path):
    return json.loads(next((tmp_path / "artifacts").glob("*/build-summary.json")).read_text())


def fake_package(args, runner, work, output, tools):
    artifact = output / "package.zip"
    artifact.write_bytes(b"valid build output")
    return [artifact]


def test_one_failed_target_does_not_hide_successful_independent_builds(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "REPO", tmp_path)
    monkeypatch.setattr(build, "preflight", lambda target: [])
    def failed(*_args):
        raise build.BuildError("compiler exit 7")
    monkeypatch.setattr(build, "BUILDERS", {"desktop": fake_package, "android": failed, "ios": fake_package})
    assert build.execute(arguments(tmp_path)) == 1
    report = summary(tmp_path)
    assert report["status"] == "FAIL"
    assert report["targets"]["desktop"]["status"] == "PASS"
    assert report["targets"]["ios"]["status"] == "PASS"
    assert report["targets"]["android"]["artifacts"] == []
    assert "compiler exit 7" in report["targets"]["android"]["error"]


@pytest.mark.parametrize("allow_partial,expected_exit", [(False, 2), (True, 0)])
def test_unavailable_ios_is_explicit_and_never_reported_as_full_success(monkeypatch, tmp_path, allow_partial, expected_exit):
    monkeypatch.setattr(build, "REPO", tmp_path)
    monkeypatch.setattr(build, "preflight", lambda target: ["requires macOS/Xcode"] if target == "ios" else [])
    forbidden = Mock(side_effect=AssertionError("unsupported build must not run"))
    monkeypatch.setattr(build, "BUILDERS", {"desktop": fake_package, "android": fake_package, "ios": forbidden})
    assert build.execute(arguments(tmp_path, skip_unavailable=allow_partial)) == expected_exit
    result = summary(tmp_path)
    assert result["status"] == "PARTIAL"
    assert result["targets"]["ios"]["status"] == "UNAVAILABLE"
    forbidden.assert_not_called()


def test_no_available_target_fails_even_when_skip_is_requested(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "preflight", lambda target: ["missing SDK"])
    assert build.execute(arguments(tmp_path, skip_unavailable=True)) == 1
    assert summary(tmp_path)["status"] == "UNAVAILABLE"


def test_check_has_no_build_install_or_output_side_effects(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "preflight", lambda target: [])
    forbidden = Mock(side_effect=AssertionError("check must not execute builds"))
    monkeypatch.setattr(build, "BUILDERS", dict.fromkeys(build.TARGETS, forbidden))
    assert build.execute(arguments(tmp_path, check=True)) == 0
    assert not (tmp_path / "artifacts").exists()


def test_artifact_missing_after_successful_command_is_a_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "REPO", tmp_path)
    monkeypatch.setattr(build, "preflight", lambda target: [])
    monkeypatch.setattr(build, "BUILDERS", {"android": lambda *args: [tmp_path / "missing.apk"]})
    assert build.execute(arguments(tmp_path, targets=["android"])) == 1
    assert summary(tmp_path)["targets"]["android"]["status"] == "FAIL"


def test_artifact_hashes_match_downloadable_output_and_runs_are_isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "REPO", tmp_path)
    monkeypatch.setattr(build, "preflight", lambda target: [])
    monkeypatch.setattr(build, "BUILDERS", {"android": fake_package})
    for _ in range(2):
        assert build.execute(arguments(tmp_path, targets=["android"])) == 0
    reports = list((tmp_path / "artifacts").glob("*/build-summary.json"))
    assert len(reports) == 2
    for file in reports:
        report = json.loads(file.read_text())
        entry = report["targets"]["android"]["artifacts"][0]
        data = (file.parent / entry["path"]).read_bytes()
        assert entry["size_bytes"] == len(data)
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()


def test_runner_preserves_nonzero_exit_and_captures_diagnostics(tmp_path):
    runner = build.Runner(tmp_path / "logs/command.log")
    import sys
    with pytest.raises(build.BuildError, match="exit 7"):
        runner.run([sys.executable, "-c", "print('compiler diagnostic'); raise SystemExit(7)"], cwd=tmp_path)
    assert "compiler diagnostic" in runner.log.read_text()


def test_ios_preflight_is_actionable_on_windows(monkeypatch):
    monkeypatch.setattr(build.platform, "system", lambda: "Windows")
    reasons = build.preflight("ios")
    assert "macOS" in reasons[0]
    assert "run this builder on a Mac" in reasons[0]


def test_android_sdk_reads_local_properties_without_changing_shell_home(monkeypatch, tmp_path):
    project = tmp_path / "project"
    (project / "apps/mobile-android").mkdir(parents=True)
    sdk = tmp_path / "sdk with spaces"
    sdk.mkdir()
    (project / "apps/mobile-android/local.properties").write_text(f"sdk.dir={sdk.as_posix()}\n")
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    monkeypatch.setattr(build, "PROJECT", project)
    assert build.android_sdk() == sdk


def test_ios_test_destination_uses_available_iphone_not_hardcoded_model(monkeypatch):
    data = {"devices": {"com.apple.CoreSimulator.SimRuntime.iOS-18-2": [
        {"name": "iPhone 16", "udid": "available-iphone", "isAvailable": True},
        {"name": "iPhone 15", "udid": "unavailable", "isAvailable": False},
        {"name": "iPad Pro", "udid": "ipad", "isAvailable": True}]}}
    monkeypatch.setattr(build.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(data)))
    assert build.simulator_destination() == "platform=iOS Simulator,id=available-iphone"


def test_removed_ci_flag_never_dispatches_remote_builds(monkeypatch):
    command = Mock()
    monkeypatch.setattr(build.subprocess, "run", command)
    with pytest.raises(SystemExit) as error:
        build.main(["--ci", "--with-tests"])
    assert error.value.code == 2
    command.assert_not_called()


def test_ios_package_is_a_simulator_app_not_a_signed_ipa(monkeypatch, tmp_path):
    work = tmp_path / "work"
    output = tmp_path / "output"
    output.mkdir()
    app = work / "DerivedData/Build/Products/Debug-iphonesimulator/AICarScanner.app"
    app.mkdir(parents=True)
    (app / "Info.plist").write_text("simulator application metadata")
    runner = Mock()
    paths = build.build_ios(arguments(tmp_path), runner, work, output, tmp_path / "tools")
    import zipfile
    with zipfile.ZipFile(paths[0]) as archive:
        assert "AICarScanner.app/Info.plist" in archive.namelist()
    assert paths[0].name.endswith("iOS-Simulator.zip")
    commands = [call.args[0] for call in runner.run.call_args_list]
    assert any("CODE_SIGNING_ALLOWED=NO" in command and "iphonesimulator" in command for command in commands)
    assert not any("archive" in command or "-exportArchive" in command for command in commands)


def test_desktop_archive_keeps_gui_and_backend_together(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "REPO", tmp_path)
    monkeypatch.setattr(build, "desktop_python", lambda *args: Path("python.exe"))
    work = tmp_path / "work"
    dist = work / "dist"
    dist.mkdir(parents=True)
    for name in ("AICarScanner.exe", "backend_service.exe"):
        (dist / name).write_bytes(b"packaged executable fixture")
    output = tmp_path / "output"
    output.mkdir()
    paths = build.build_desktop(arguments(tmp_path), Mock(), work, output, tmp_path / "tools")
    import zipfile
    with zipfile.ZipFile(paths[0]) as archive:
        assert {"AICarScanner.exe", "backend_service.exe", "README.txt"}.issubset(archive.namelist())


def test_android_java_version_outside_gradle_support_is_rejected(monkeypatch, tmp_path):
    sdk = tmp_path / "sdk"
    (sdk / "platforms/android-36").mkdir(parents=True)
    (sdk / "platforms/android-36/android.jar").write_bytes(b"sdk")
    (sdk / "build-tools/35.0.0").mkdir(parents=True)
    monkeypatch.setattr(build, "android_sdk", lambda: sdk)
    monkeypatch.setattr(build, "java_executable", lambda: "java")
    monkeypatch.setattr(build.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='', stderr='openjdk version "26.0.0"'))
    assert any("JDK 17" in reason for reason in build.preflight("android"))


def test_cancelled_build_records_pending_targets_and_returns_130(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "REPO", tmp_path)
    monkeypatch.setattr(build, "preflight", lambda target: [])
    def interrupted(*args):
        raise KeyboardInterrupt
    monkeypatch.setattr(build, "BUILDERS", {"desktop": interrupted, "android": fake_package})
    assert build.execute(arguments(tmp_path, targets=["desktop", "android"])) == 130
    report = summary(tmp_path)
    assert report["status"] == "CANCELLED"
    assert report["targets"]["desktop"]["status"] == "CANCELLED"
    assert report["targets"]["android"]["status"] == "NOT_RUN"


def test_runner_timeout_stops_command_and_keeps_output(tmp_path, capsys):
    import sys
    runner = build.Runner(tmp_path / "build.log")
    with pytest.raises(build.BuildError, match="timed out"):
        runner.run([sys.executable, "-u", "-c", "import time; print('working'); time.sleep(30)"], cwd=tmp_path, timeout=0.3)
    assert "working" in runner.log.read_text()
    assert "working" in capsys.readouterr().out


def test_android_builder_passes_selected_backend_url(monkeypatch, tmp_path):
    project = tmp_path / 'apps/mobile-android'
    apk = project / 'app/build/outputs/apk/debug/app-debug.apk'
    apk.parent.mkdir(parents=True); apk.write_bytes(b'apk')
    output = tmp_path/'output'; output.mkdir()
    monkeypatch.setattr(build,'PROJECT',tmp_path)
    monkeypatch.setattr(build,'android_sdk',lambda:None)
    runner = Mock()
    args = arguments(tmp_path,android_api_url='http://10.0.2.2:8001/')
    build.build_android(args,runner,tmp_path,output,tmp_path)
    assert '-PapiBaseUrl=http://10.0.2.2:8001/' in runner.run.call_args.args[0]


def test_android_backend_url_rejects_credentials():
    with pytest.raises(SystemExit) as error:
        build.main(['--targets','android','--android-api-url','http://user:password@host/'])
    assert error.value.code == 2


@pytest.mark.parametrize('url',['http://[','http://host:invalid/'])
def test_android_backend_url_rejects_invalid_host_or_port(url):
    with pytest.raises(SystemExit) as error:
        build.main(['--targets','android','--android-api-url',url])
    assert error.value.code == 2


def test_runner_can_supply_license_stdin_with_live_logging(tmp_path):
    import sys
    command = [sys.executable, '-c', 'import sys; print("ACCEPTED=" + sys.stdin.read().strip())']
    process = build.Runner(tmp_path / 'stdin.log')
    process.run(command, cwd=tmp_path, input_text='yes\n')
    assert 'ACCEPTED=yes' in process.log.read_text()
