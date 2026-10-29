from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from diagnostic.models import DiagnosticSession
from multi_ecu.models import EcuNodeRequest, GatewayNodeRequest
from api import multi_bus_routes as routes


class FakeRuntime:
    should_fail = False

    def __init__(self, *, session_id, topology, buses):
        if self.should_fail:
            raise ValueError("invalid test topology")
        self.session_id = session_id
        self.topology = topology
        self.buses = buses
        self.connect = AsyncMock()
        self.topology_view = lambda: {
            "ecus": [x.ecu_id for x in topology.ecus],
            "bus_names": [x.name for x in buses],
        }
        self.identify_all = AsyncMock(return_value={
            "ECU1": SimpleNamespace(to_dict=lambda: {"vin": "VINTEST1234567890"})
        })
        self.read_all_dtcs = AsyncMock(return_value={"ECU1": [SimpleNamespace(to_dict=lambda: {"code": "P0302"})]})


def _request():
    return routes.MultiBusConnectRequest(
        buses=[routes.CanBusRequest(name="CAN0", bitrate=500_000)],
        ecus=[EcuNodeRequest(ecu_id="ECU1", name="Engine", request_id=0x7E0, response_id=0x7E8)],
        gateways=[GatewayNodeRequest(gateway_id="GW1", name="Gateway", bus="CAN0")],
        routes=[routes.GatewayRouteRequest(
            gateway_id="GW1", source_bus="CAN0", target_bus="CAN0",
            target_ecu_id="ECU1", addressing="NORMAL",
        )],
    )


def _setup(monkeypatch):
    session = DiagnosticSession()
    monkeypatch.setattr(routes, "sessions", {"s1": session})
    monkeypatch.setattr(routes, "_runtime", {})
    monkeypatch.setattr(routes, "MultiBusDiagnosticRuntime", FakeRuntime)
    FakeRuntime.should_fail = False
    return session


@pytest.mark.asyncio
async def test_connect_404_success_and_value_error_mapping(monkeypatch):
    session = _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await routes.connect("missing", _request())
    assert exc.value.status_code == 404

    result = await routes.connect("s1", _request())
    assert result == {"ecus": ["ECU1"], "bus_names": ["CAN0"]}
    assert routes._runtime["s1"].session_id == session.session_id
    routes._runtime["s1"].connect.assert_awaited_once()

    FakeRuntime.should_fail = True
    with pytest.raises(HTTPException) as exc:
        await routes.connect("s1", _request())
    assert exc.value.status_code == 400
    assert exc.value.detail == "invalid test topology"


def test_topology_requires_connected_runtime_and_returns_view(monkeypatch):
    _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.topology("s1")
    assert exc.value.status_code == 404
    routes._runtime["s1"] = FakeRuntime(
        session_id=uuid4(), topology=SimpleNamespace(ecus=[]), buses=[routes.CanBusRequest(name="CAN0")]
    )
    assert routes.topology("s1")["bus_names"] == ["CAN0"]


@pytest.mark.asyncio
async def test_identify_all_and_read_dtcs_cover_not_found_success_and_conflict(monkeypatch):
    _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await routes.identify_all("s1")
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        await routes.read_dtcs("s1")
    assert exc.value.status_code == 404

    runtime = FakeRuntime(session_id=uuid4(), topology=SimpleNamespace(ecus=[]), buses=[])
    routes._runtime["s1"] = runtime
    assert await routes.identify_all("s1") == {"ecus": {"ECU1": {"vin": "VINTEST1234567890"}}}
    assert await routes.read_dtcs("s1") == {"dtcs_by_ecu": {"ECU1": [{"code": "P0302"}]}}

    async def fail():
        raise RuntimeError("runtime disconnected")
    runtime.identify_all = fail
    with pytest.raises(HTTPException) as exc:
        await routes.identify_all("s1")
    assert exc.value.status_code == 409
