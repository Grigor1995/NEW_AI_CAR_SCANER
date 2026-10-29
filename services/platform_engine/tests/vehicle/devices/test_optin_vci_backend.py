"""Device backend must not activate physical LAN/USB by default."""

from device.manager import VCIConnectionManager, _build_vci_manager


def test_vci_default_is_simulator(monkeypatch):
    monkeypatch.delenv("AI_CAR_ENABLE_PHYSICAL_VCI", raising=False)
    vci = _build_vci_manager()
    assert type(vci) is VCIConnectionManager


def test_physical_vci_rejected_on_non_loopback_bind(monkeypatch):
    monkeypatch.setenv("AI_CAR_ENABLE_PHYSICAL_VCI", "1")
    monkeypatch.setenv("AI_CAR_BACKEND_HOST", "0.0.0.0")
    assert type(_build_vci_manager()) is VCIConnectionManager


def test_explicit_local_optin_allows_real_adapter_manager(monkeypatch):
    monkeypatch.setenv("AI_CAR_ENABLE_PHYSICAL_VCI", "1")
    monkeypatch.setenv("AI_CAR_BACKEND_HOST", "127.0.0.1")
    vci = _build_vci_manager()
    assert type(vci).__name__ == "LocalVciManager"
    assert hasattr(vci, "connected_obd")
    assert hasattr(vci, "read_dtcs")
