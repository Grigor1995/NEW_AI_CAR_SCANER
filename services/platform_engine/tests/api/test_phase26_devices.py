from fastapi.testclient import TestClient
from api.main import app
from api.device_routes import manager


def setup_function():
    manager.devices.clear()
    manager.connections.clear()


def teardown_function():
    manager.devices.clear()
    manager.connections.clear()


def test_simulator_device_full_api_flow():
    client = TestClient(app)
    created = client.post("/api/v1/devices/simulator")
    assert created.status_code == 200, created.text
    device = created.json()
    did = device["device_id"]

    listed = client.get("/api/v1/devices")
    assert listed.status_code == 200
    assert any(x["device_id"] == did for x in listed.json()["devices"])

    connected = client.post(f"/api/v1/devices/{did}/connect", json={"config": {}})
    assert connected.status_code == 200, connected.text
    assert connected.json()["status"] == "connected"

    vin = client.get(f"/api/v1/devices/{did}/obd/vin")
    assert vin.status_code == 200
    assert vin.json()["vin"] == "WDD2110801A123456"

    dtcs = client.get(f"/api/v1/devices/{did}/obd/dtcs")
    assert dtcs.status_code == 200
    assert dtcs.json()["dtcs"] == ["P0102"]

    live = client.get(f"/api/v1/devices/{did}/obd/live-data")
    assert live.status_code == 200
    assert live.json()["values"]["rpm"] == 1696.0

    disconnected = client.post(f"/api/v1/devices/{did}/disconnect")
    assert disconnected.status_code == 200
    assert disconnected.json()["status"] == "disconnected"


def test_reconnect_reuses_connection_configuration():
    client = TestClient(app)
    device = client.post("/api/v1/devices/simulator").json()
    did = device["device_id"]
    assert client.post(f"/api/v1/devices/{did}/connect", json={"config": {}}).status_code == 200
    reconnected = client.post(f"/api/v1/devices/{did}/reconnect")
    assert reconnected.status_code == 200, reconnected.text
    assert reconnected.json()["status"] == "connected"
