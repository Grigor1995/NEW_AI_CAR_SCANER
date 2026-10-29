"""Offline startup diagnostics over real HTTP, without pretending to run GGUF inference."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from apps.desktop import main as launcher
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('offline_ai_doctor', Path(__file__).resolve().parents[2]/'scripts/check_offline_ai.py')
_doctor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_doctor)
inspect = _doctor.inspect


@pytest.mark.parametrize('backend_provider,backend_available,ready',[
    ('LlamaServerLLMProvider',True,True),
    ('HttpOpenAICompatibleProvider',True,False),
    ('LlamaServerLLMProvider',False,False),
])
def test_doctor_checks_actual_backend_provider_not_only_model_file(monkeypatch,tmp_path,backend_provider,backend_available,ready):
    model=tmp_path/'models/installed.gguf'
    model.parent.mkdir();model.write_bytes(b'path fixture only, not model weights')
    runtime=tmp_path/'tools/llama.cpp/llama-server.exe'
    runtime.parent.mkdir(parents=True);runtime.write_bytes(b'path fixture, never executed')
    monkeypatch.setattr(launcher,'ROOT',tmp_path)
    monkeypatch.setattr(launcher,'BUNDLE_ROOT',tmp_path)
    monkeypatch.setattr(launcher,'LLM_MODEL','default.gguf')
    for key in ('LOCAL_LLM_MODEL_PATH','LOCAL_LLM_SERVER_MODEL','LOCAL_LLM_SERVER_PATH'):
        monkeypatch.delenv(key,raising=False)
    paths=[]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            bodies={'/health':{'status':'ok'},'/v1/models':{'data':[{'id':'installed.gguf'}]},
                    '/props':{'default_generation_settings':{'n_ctx':8192}},
                    '/api/v1/ai/provider':{'provider':backend_provider,'available':backend_available}}
            content=json.dumps(bodies[self.path]).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(content)))
            self.end_headers();self.wfile.write(content)
        def log_message(self,*args): pass

    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setattr(launcher,'LLM_BASE_URL',base)
    monkeypatch.setattr(launcher,'BACKEND_URL',base)
    try:
        report=inspect()
        assert report['ready'] is ready
        assert report['model_exists'] and report['model_path'] == str(model)
        assert report['server_binary'] == str(runtime)
        assert '/api/v1/ai/provider' in paths and '/v1/models' in paths
        if not ready:
            assert 'existing backend' in report['next_step']
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
