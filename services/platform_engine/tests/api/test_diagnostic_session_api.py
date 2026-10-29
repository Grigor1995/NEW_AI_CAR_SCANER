from fastapi.testclient import TestClient

from api.main import app


def test_create_add_symptom_dtc_and_analyze():
    client = TestClient(app)

    vehicle = {
        "make": "Mercedes-Benz",
        "model": "W211 E350",
        "year": 2006,
        "engine": "M272 3.5",
        "fuel": ["petrol", "LPG"],
        "ecu": "ME 9.7",
    }
    response = client.post("/api/v1/sessions", json=vehicle)
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]

    symptom = (
        "Engine runs smoothly on petrol, but shakes and hesitates on LPG "
        "when accelerating below 2000 RPM. The problem is more noticeable "
        "when accelerating from low RPM under load. At idle, the engine is "
        "mostly smooth. Switching back to petrol significantly reduces the symptom."
    )
    response = client.post(
        f"/api/v1/sessions/{session_id}/symptoms",
        json={"raw_text": symptom, "symptom": symptom},
    )
    assert response.status_code == 200, response.text
    assert response.json()["symptoms"][0]["raw_text"] == symptom
    symptom_id = response.json()["symptoms"][0]["id"]

    updated = "Engine shakes on LPG below 2000 RPM under load."
    response = client.put(
        f"/api/v1/sessions/{session_id}/symptoms/{symptom_id}",
        json={"raw_text": updated, "symptom": updated},
    )
    assert response.status_code == 200, response.text
    assert response.json()["symptoms"][0]["id"] == symptom_id
    assert response.json()["symptoms"][0]["raw_text"] == updated

    response = client.delete(
        f"/api/v1/sessions/{session_id}/symptoms/{symptom_id}"
    )
    assert response.status_code == 200, response.text
    assert response.json()["symptoms"] == []

    response = client.post(
        f"/api/v1/sessions/{session_id}/dtcs",
        json={"code": "P0302"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["dtcs"][0]["code"] == "P0302"

    edited_vehicle = {
        "make": "Mercedes-Benz",
        "model": "W211 E350",
        "year": 2006,
        "engine": "M272 3.5",
        "fuel": ["petrol", "LPG"],
        "ecu": "ME 9.7",
    }
    response = client.put(
        f"/api/v1/sessions/{session_id}/vehicle",
        json=edited_vehicle,
    )
    assert response.status_code == 200, response.text
    assert response.json()["vehicle"]["engine"] == "M272 3.5"

    response = client.post(f"/api/v1/analysis/{session_id}")
    assert response.status_code == 200, response.text

    body = response.json()
    categories = {item["category"] for item in body["hypotheses"]}
    assert "ignition / combustion" in categories
    assert "LPG fuel delivery / mixture" in categories
    assert "air-fuel / intake" in categories
    assert "mechanical cylinder condition" in categories
    assert all("confirmed coil failure" not in item["statement"].lower() for item in body["hypotheses"])
    assert body["recommendations"]
    assert all(item["priority_score"] > 0 for item in body["recommendations"])
    assert all(item["expected_information_gain"] > 0 for item in body["recommendations"])
    assert all(item["estimated_cost"] > 0 for item in body["recommendations"])
    assert all(
        item["expected_information_gain"] <= 0.95 and item["estimated_cost"] > 0
        for item in body["recommendations"]
    )


def test_legacy_symptom_payload_is_accepted():
    client = TestClient(app)
    response = client.post("/api/v1/sessions", json={})
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/symptoms",
        json={"symptom": "Engine shakes on LPG"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["symptoms"][0]["raw_text"] == "Engine shakes on LPG"


def test_analysis_localizes_to_requested_language_and_links_evidence():
    client = TestClient(app)
    response = client.post(
        "/api/v1/sessions",
        json={
            "make": "Mercedes-Benz",
            "model": "W211 E350",
            "year": 2006,
            "engine": "M272 3.5",
            "fuel": ["petrol", "LPG"],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    symptom = "Engine shakes on LPG below 2000 RPM under load; petrol is normal."
    response = client.post(
        f"/api/v1/sessions/{session_id}/symptoms",
        json={"raw_text": symptom},
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/v1/sessions/{session_id}/dtcs",
        json={"code": "P0302"},
    )
    assert response.status_code == 200

    response = client.post(f"/api/v1/analysis/{session_id}?language=hy")
    assert response.status_code == 200, response.text
    body = response.json()

    assert any(item["category"] == "Բոցավառում / այրում" for item in body["hypotheses"])
    assert any(item["supporting_evidence_ids"] for item in body["hypotheses"])
    assert body["recommendations"]
    assert body["recommendations"][0]["name"] != "Compare fuel-trim and misfire behavior by fuel mode"

    english = client.post(f"/api/v1/analysis/{session_id}?language=en")
    assert english.status_code == 200
    english_body = english.json()
    assert any(item["category"] == "ignition / combustion" for item in english_body["hypotheses"])


def test_recommendations_and_test_result_follow_requested_language():
    client = TestClient(app)
    response = client.post(
        "/api/v1/sessions",
        json={
            "make": "Mercedes-Benz",
            "model": "W211 E350",
            "year": 2006,
            "engine": "M272 3.5",
            "fuel": ["petrol", "LPG"],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    symptom = "Engine shakes on LPG below 2000 RPM under load; petrol is normal."
    assert client.post(
        f"/api/v1/sessions/{session_id}/symptoms",
        json={"raw_text": symptom},
    ).status_code == 200
    assert client.post(
        f"/api/v1/sessions/{session_id}/dtcs",
        json={"code": "P0302"},
    ).status_code == 200

    response = client.post(f"/api/v1/analysis/{session_id}?language=hy")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]

    english_names = {
        "Measure LPG pressure at idle and under load",
        "Compare STFT/LTFT on petrol versus LPG",
        "Compare LPG injector contribution / balance",
        "Compare cylinder misfire counters under the same load",
        "Check ignition performance under controlled load",
        "Validate MAF signal against RPM/load plausibility",
        "Inspect intake and MAF wiring/connectors",
        "Compare fuel-trim and misfire behavior by fuel mode",
        "Inspect LPG pressure and injector behavior under load",
        "Check ignition performance under LPG load",
        "Inspect intake system for an air leak",
        "Compare cylinder-specific misfire counters and compression evidence",
        "Check for unmetered-air leak",
    }
    assert all(item["name"] not in english_names for item in body["recommendations"])
    assert all(
        not item["purpose"].startswith((
            "Separate ", "Check ", "Determine ", "Verify ", "Validate ",
            "Look ", "Establish ", "Obtain "
        ))
        for item in body["recommendations"]
    )

    before_statuses = {item["category"]: item["status"] for item in body["hypotheses"]}

    test_id = body["recommendations"][0]["id"]
    result = client.post(
        f"/api/v1/intelligence/sessions/{session_id}/test-results?language=hy",
        json={
            "test_id": test_id,
            "result": "FAIL",
            "notes": "Գազի ճնշումը նվազում է բեռնվածության ժամանակ։",
        },
    )
    assert result.status_code == 200, result.text
    localized = result.json()
    assert localized["recommendations"]
    assert all(item["name"] not in english_names for item in localized["recommendations"])
    assert all(item["expected_information_gain"] > 0 for item in localized["recommendations"])
    assert all(item["estimated_cost"] > 0 for item in localized["recommendations"])
    assert all(item["id"] != test_id for item in localized["recommendations"])
    assert any("Թեստի արդյունք" in item["fact"] for item in localized["evidence"])
    assert any(item.get("test_name") for item in localized["test_results"])
    assert any(item["result_label"] in {"ԱՆՑԱՎ", "ՉԱՆՑԱՎ", "ԱՆԱՎԱՐՏ"} for item in localized["test_results"])

    after_statuses = {item["category"]: item["status"] for item in localized["hypotheses"]}
    assert any(
        after_statuses.get(category) != before_statuses.get(category)
        for category in after_statuses.keys() & before_statuses.keys()
    )


def test_non_lpg_analysis_keeps_rule_recommendations():
    client = TestClient(app)
    response = client.post(
        "/api/v1/sessions",
        json={
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "engine": "2.5",
            "fuel": ["petrol"],
        },
    )
    session_id = response.json()["session_id"]
    response = client.post(
        f"/api/v1/sessions/{session_id}/symptoms",
        json={"raw_text": "Engine idles rough and RPM fluctuates."},
    )
    assert response.status_code == 200
    response = client.post(
        f"/api/v1/sessions/{session_id}/dtcs",
        json={"code": "P0171"},
    )
    assert response.status_code == 200

    response = client.post(f"/api/v1/analysis/{session_id}?language=hy")
    assert response.status_code == 200, response.text
    hy_names = {item["name"] for item in response.json()["recommendations"]}
    assert "Ստուգել չչափված օդի արտահոսքը" in hy_names

    response = client.post(f"/api/v1/analysis/{session_id}?language=ru")
    assert response.status_code == 200, response.text
    ru_names = {item["name"] for item in response.json()["recommendations"]}
    assert "Проверить подсос неучтённого воздуха" in ru_names

def test_test_result_status_contract_normalizes_legacy_unknown_and_rejects_other_values():
    client = TestClient(app)
    created = client.post("/api/v1/sessions", json={})
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]
    test_id = "00000000-0000-0000-0000-000000000001"

    legacy = client.post(
        f"/api/v1/intelligence/sessions/{session_id}/test-results",
        json={"test_id": test_id, "result": "UNKNOWN"},
    )
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["test_results"][-1]["result"] == "INCOMPLETE"

    invalid = client.post(
        f"/api/v1/intelligence/sessions/{session_id}/test-results",
        json={"test_id": test_id, "result": "SKIPPED"},
    )
    assert invalid.status_code == 422, invalid.text
