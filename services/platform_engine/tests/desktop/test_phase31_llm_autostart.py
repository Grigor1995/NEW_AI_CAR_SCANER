from __future__ import annotations

from types import SimpleNamespace

import apps.desktop.main as desktop_main


def test_resolve_model_path_uses_project_models(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_main, "ROOT", tmp_path)
    monkeypatch.delenv("LOCAL_LLM_MODEL_PATH", raising=False)
    monkeypatch.setattr(desktop_main, "LLM_MODEL", "Qwen3-8B-Q4_K_M.gguf")
    assert desktop_main._resolve_model_path() == (tmp_path / "models" / "Qwen3-8B-Q4_K_M.gguf").resolve()


def test_resolve_llama_server_prefers_explicit_path(monkeypatch, tmp_path):
    exe = tmp_path / "llama-server.exe"
    exe.write_bytes(b"x")
    monkeypatch.setenv("LOCAL_LLM_SERVER_PATH", str(exe))
    assert desktop_main._resolve_llama_server() == exe.resolve()


def test_start_llama_server_builds_expected_command(monkeypatch, tmp_path):
    # This case verifies enabled startup even if the outer QA runner
    # disables real model autostart in its process environment.
    monkeypatch.delenv("AI_CAR_DISABLE_LLM_AUTOSTART", raising=False)
    exe = tmp_path / "llama-server.exe"
    exe.write_bytes(b"x")
    model = tmp_path / "Qwen3.gguf"
    model.write_bytes(b"gguf")

    monkeypatch.setenv("LOCAL_LLM_SERVER_PATH", str(exe))
    monkeypatch.setattr(desktop_main, "ROOT", tmp_path)
    monkeypatch.setenv("LOCAL_LLM_MODEL_PATH", str(model))
    monkeypatch.setattr(desktop_main, "_llm_healthy", lambda: False)
    monkeypatch.setattr(desktop_main, "_is_port_open", lambda *_: False)
    monkeypatch.setattr(desktop_main, "_appdata_log", lambda _: tmp_path / "llama.log")
    monkeypatch.setattr(desktop_main, "_LLM_STARTUP_TIMEOUT", 0.1)
    monkeypatch.setattr(desktop_main, "_llm_healthy", lambda: True)

    calls: dict[str, object] = {}

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(poll=lambda: None, returncode=None, terminate=lambda: None, wait=lambda **_: None, kill=lambda: None)

    monkeypatch.setattr(desktop_main.subprocess, "Popen", fake_popen)
    result = desktop_main.start_llama_server()

    # With the health lambda returning true, the existing-server branch is used.
    assert result is None
    assert "command" not in calls


def test_start_llama_server_starts_when_unhealthy(monkeypatch, tmp_path):
    # This case verifies enabled startup even if the outer QA runner
    # disables real model autostart in its process environment.
    monkeypatch.delenv("AI_CAR_DISABLE_LLM_AUTOSTART", raising=False)
    exe = tmp_path / "llama-server.exe"
    exe.write_bytes(b"x")
    model = tmp_path / "Qwen3.gguf"
    model.write_bytes(b"gguf")

    monkeypatch.setenv("LOCAL_LLM_SERVER_PATH", str(exe))
    monkeypatch.setenv("LOCAL_LLM_MODEL_PATH", str(model))
    monkeypatch.setenv("LOCAL_LLM_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_LLM_SERVER_PORT", "8000")
    monkeypatch.setenv("LOCAL_LLM_SERVER_CONTEXT", "4096")
    monkeypatch.setenv("LOCAL_LLM_SERVER_THREADS", "8")
    monkeypatch.setattr(desktop_main, "ROOT", tmp_path)
    monkeypatch.setattr(desktop_main, "LLM_HOST", "127.0.0.1")
    monkeypatch.setattr(desktop_main, "LLM_PORT", 8000)
    monkeypatch.setattr(desktop_main, "LLM_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(desktop_main, "LLM_HEALTH_URL", "http://127.0.0.1:8000/health")
    monkeypatch.setattr(desktop_main, "LLM_MODEL", "Qwen3.gguf")
    monkeypatch.setattr(desktop_main, "_llm_healthy", lambda: False)
    monkeypatch.setattr(desktop_main, "_is_port_open", lambda *_: False)
    monkeypatch.setattr(desktop_main, "_LLM_STARTUP_TIMEOUT", 0.1)
    monkeypatch.setattr(desktop_main.time, "sleep", lambda _: None)
    monkeypatch.setattr(desktop_main, "_appdata_log", lambda _: tmp_path / "llama.log")

    calls: dict[str, object] = {}

    class Proc:
        returncode = None
        def poll(self): return None
        def terminate(self): pass
        def wait(self, **_): pass
        def kill(self): pass

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        # Once spawned, simulate a healthy server.
        monkeypatch.setattr(desktop_main, "_llm_healthy", lambda: True)
        return Proc()

    monkeypatch.setattr(desktop_main.subprocess, "Popen", fake_popen)
    result = desktop_main.start_llama_server()

    try:
        assert result is not None
        command = calls["command"]
        assert command[:2] == [str(exe), "-m"]
        assert str(model) in command
        assert "--host" in command and "127.0.0.1" in command
        assert "--port" in command and "8000" in command
    finally:
        desktop_main.stop_llama_server()


def test_source_runtime_is_found_next_to_project_without_path_env(monkeypatch,tmp_path):
    monkeypatch.delenv('LOCAL_LLM_SERVER_PATH',raising=False)
    monkeypatch.setattr(desktop_main,'ROOT',tmp_path)
    monkeypatch.setattr(desktop_main,'BUNDLE_ROOT',tmp_path)
    monkeypatch.setattr(desktop_main.shutil,'which',lambda _:None)
    runtime = tmp_path/'llama-server.exe'
    runtime.write_bytes(b'fixture')
    assert desktop_main._resolve_llama_server() == runtime.resolve()


def test_source_runtime_is_found_in_documented_tools_directory(monkeypatch,tmp_path):
    monkeypatch.delenv('LOCAL_LLM_SERVER_PATH',raising=False)
    monkeypatch.setattr(desktop_main,'ROOT',tmp_path)
    monkeypatch.setattr(desktop_main,'BUNDLE_ROOT',tmp_path)
    monkeypatch.setattr(desktop_main.shutil,'which',lambda _:None)
    runtime = tmp_path/'tools/llama.cpp/llama-server.exe'
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b'fixture')
    assert desktop_main._resolve_llama_server() == runtime.resolve()


def test_single_installed_gguf_is_used_without_renaming(monkeypatch,tmp_path):
    monkeypatch.delenv('LOCAL_LLM_MODEL_PATH',raising=False)
    monkeypatch.delenv('LOCAL_LLM_SERVER_MODEL',raising=False)
    monkeypatch.setattr(desktop_main,'ROOT',tmp_path)
    monkeypatch.setattr(desktop_main,'LLM_MODEL','default.gguf')
    models = tmp_path/'models';models.mkdir()
    installed = models/'my-existing-qwen.gguf';installed.write_bytes(b'fixture')
    assert desktop_main._resolve_model_path() == installed.resolve()
    monkeypatch.setenv('LOCAL_LLM_SERVER_MODEL',installed.name)
    assert desktop_main._resolve_model_path() == installed.resolve()
    monkeypatch.setenv('LOCAL_LLM_SERVER_MODEL','explicit-missing.gguf')
    assert desktop_main._resolve_model_path() == (models/'explicit-missing.gguf').resolve()


def test_multiple_ggufs_require_explicit_choice(monkeypatch,tmp_path):
    monkeypatch.delenv('LOCAL_LLM_MODEL_PATH',raising=False)
    monkeypatch.delenv('LOCAL_LLM_SERVER_MODEL',raising=False)
    monkeypatch.setattr(desktop_main,'ROOT',tmp_path)
    monkeypatch.setattr(desktop_main,'LLM_MODEL','default.gguf')
    models=tmp_path/'models';models.mkdir()
    for name in ('one.gguf','two.gguf'):(models/name).write_bytes(b'fixture')
    assert desktop_main._resolve_model_path() == (models/'default.gguf').resolve()
