from fastapi.testclient import TestClient

from api.main import app


def test_full_diagnostic_lifecycle_create_edit_analyze_record_and_reload():
    client = TestClient(app)
    created = client.post(
        "/api/v1/sessions",
        json={
            "make": "Mercedes-Benz",
            "model": "W211 E350",
            "year": 2006,
            "engine": "M272 3.5",
            "fuel": ["petrol", "LPG"],
        },
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]

    symptom = client.post(
        f"/api/v1/sessions/{session_id}/symptoms",
        json={"raw_text": "Runs smoothly on petrol; shakes on LPG under load."},
    )
    assert symptom.status_code == 200, symptom.text
    symptom_id = symptom.json()["symptoms"][0]["id"]

    changed_symptom = client.put(
        f"/api/v1/sessions/{session_id}/symptoms/{symptom_id}",
        json={"raw_text": "Shakes on LPG below 2000 RPM.", "symptom": "Shakes on LPG below 2000 RPM."},
    )
    assert changed_symptom.status_code == 200, changed_symptom.text
    assert changed_symptom.json()["symptoms"][0]["raw_text"] == "Shakes on LPG below 2000 RPM."

    dtc = client.post(f"/api/v1/sessions/{session_id}/dtcs", json={"code": "P0302"})
    assert dtc.status_code == 200, dtc.text
    dtc_id = dtc.json()["dtcs"][0]["id"]
    updated_dtc = client.put(
        f"/api/v1/sessions/{session_id}/dtcs/{dtc_id}",
        json={"code": "P0302", "description": "Cylinder 2 misfire"},
    )
    assert updated_dtc.status_code == 200, updated_dtc.text
    assert updated_dtc.json()["dtcs"][0]["code"] == "P0302"

    analyzed = client.post(f"/api/v1/analysis/{session_id}?language=en")
    assert analyzed.status_code == 200, analyzed.text
    analysis = analyzed.json()
    assert analysis["hypotheses"]
    assert analysis["recommendations"]
    assert all(item["status"] != "confirmed" for item in analysis["hypotheses"])
    test_id = analysis["recommendations"][0]["id"]

    recorded = client.post(
        f"/api/v1/intelligence/sessions/{session_id}/test-results?language=en",
        json={
            "test_id": test_id,
            "result": "PASS",
            "measurements": {"pressure_bar": 1.2},
            "notes": "Measurement remained stable during the test.",
        },
    )
    assert recorded.status_code == 200, recorded.text
    assert any(item["test_id"] == test_id for item in recorded.json()["test_results"])

    reloaded = client.get(f"/api/v1/sessions/{session_id}")
    assert reloaded.status_code == 200, reloaded.text
    body = reloaded.json()
    assert body["session_id"] == session_id
    assert body["symptoms"][0]["raw_text"] == "Shakes on LPG below 2000 RPM."
    assert body["dtcs"][0]["code"] == "P0302"
    assert any(item["test_id"] == test_id for item in body["test_results"])


def test_diagnostic_api_rejects_unknown_session_for_session_read():
    client = TestClient(app)
    response = client.get("/api/v1/sessions/session-that-does-not-exist")
    assert response.status_code == 404
