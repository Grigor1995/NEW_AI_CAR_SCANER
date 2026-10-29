from fastapi.testclient import TestClient

from api.main import app
from global_data import global_data


def test_global_data_is_client_independent():
    snapshot = global_data.snapshot().as_dict()
    assert snapshot["version"]
    assert snapshot["vehicles"]
    assert any(x["case_id"] == "LPG_MISFIRE_001" for x in snapshot["diagnostic_cases"])


def test_global_data_api_contract():
    client = TestClient(app)
    response = client.get("/api/v1/global-data")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == global_data.snapshot().version
    assert body["vehicles"]
    assert body["diagnostic_cases"]


def test_global_case_contract():
    client = TestClient(app)
    response = client.get("/api/v1/global-data/cases/LPG_MISFIRE_001")
    assert response.status_code == 200
    case = response.json()
    assert case["case_id"] == "LPG_MISFIRE_001"
    assert "P0302" in case["dtcs"]


def test_global_data_returns_none_for_unknown_case():
    assert global_data.case("DOES_NOT_EXIST") is None


def test_global_data_snapshot_is_deep_copied():
    snapshot = global_data.snapshot()
    exported = snapshot.as_dict()
    exported["vehicles"][0]["make"] = "MUTATED"
    assert global_data.snapshot().vehicles[0]["make"] != "MUTATED"


def test_global_data_api_returns_404_for_unknown_case():
    client = TestClient(app)
    response = client.get("/api/v1/global-data/cases/DOES_NOT_EXIST")
    assert response.status_code == 404
