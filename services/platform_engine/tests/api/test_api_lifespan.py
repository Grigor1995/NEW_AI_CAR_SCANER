from __future__ import annotations

import api.main as main
from fastapi.testclient import TestClient


def test_lifespan_loads_persisted_sessions_before_serving_requests(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(main, "load_persisted_sessions", lambda: calls.append("loaded"))

    with TestClient(main.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    assert calls == ["loaded"]
