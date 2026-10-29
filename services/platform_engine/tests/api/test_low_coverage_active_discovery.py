from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from diagnostic.models import DiagnosticSession
from vehicle.network.discovery import DiscoveredEcuCandidate, VehicleNetworkDiscoveryResult
from vehicle.network.active_discovery import ActiveProbeResult
from vehicle.network.models import EcuNode, GatewayRoute, VehicleNetworkTopology
from network_discovery import active_service as active_service_module
from api import active_discovery_routes as routes


def _candidate(candidate_id, bus="CAN1", request_id=0x7E0, response_id=0x7E8):
    return DiscoveredEcuCandidate(
        candidate_id=candidate_id, bus=bus, request_id=request_id,
        response_id=response_id, confidence=0.7, classification="UDS_REQUEST_RESPONSE_INFERRED",
        evidence=("ids observed",), observed_ids=(request_id, response_id),
    )


@pytest.mark.asyncio
async def test_active_service_filters_targets_routes_via_gateway_and_correlates(monkeypatch):
    captured = {}

    class FakeEngine:
        def __init__(self, policy=None):
            self.policy = policy

        async def probe_many(self, targets, buses):
            captured["targets"] = targets
            captured["buses"] = buses
            return [
                ActiveProbeResult(
                    candidate_id=targets[0].candidate_id, bus=targets[0].bus,
                    request_id=targets[0].request_id, response_id=targets[0].response_id,
                    classification="CONFIRMED_UDS_ECU", confidence=0.99, responded=True,
                    identity={"vin": "VINTEST1234567890"}, gateway_id=targets[0].gateway_id,
                )
            ] if targets else []

    monkeypatch.setattr(active_service_module, "ActiveEcuDiscoveryEngine", FakeEngine)
    service = active_service_module.ActiveNetworkDiscoveryService()
    sid = uuid4()
    passive = VehicleNetworkDiscoveryResult(ecu_candidates=[
        _candidate("routed"),
        _candidate("missing-id", request_id=None, response_id=0x7E8),
        _candidate("unselected", bus="CAN0"),
        _candidate("no-bus", bus="CAN9"),
    ])
    topology = VehicleNetworkTopology(
        ecus=(EcuNode("ECU1", "Engine", 0x7E0, 0x7E8, bus="CAN1"),),
        routes=(GatewayRoute("GW1", "CAN0", "CAN1", "ECU1"),),
    )
    results = await service.probe_candidates(
        sid, passive, {"CAN0": object(), "CAN1": object()}, topology,
        candidate_ids=["routed", "missing-id", "unselected", "no-bus"],
    )

    assert len(results) == 1
    target = captured["targets"][0]
    assert target.candidate_id == "routed"
    assert target.bus == "CAN0"
    assert target.gateway_id == "GW1"
    assert service.results(sid) == results
    assert service.results(uuid4()) == []

    correlated = service.correlate(sid, passive, topology)
    assert correlated["active_probe_count"] == 1
    assert correlated["confirmed_count"] == 1
    assert correlated["gateway_correlations"] == 1
    assert next(x for x in correlated["candidates"] if x["candidate_id"] == "missing-id")["status"] == "PASSIVE_ONLY"
    assert correlated["unmatched_active"] == []


class FakePassiveService:
    def __init__(self, result):
        self.result = result
    def analyze(self, session_id):
        return self.result


class FakeActiveService:
    def __init__(self):
        self.probe_candidates = AsyncMock(return_value=[])
        self.correlate = lambda *args: {"active_probe_count": 0, "candidates": []}


def _route_setup(monkeypatch):
    session = DiagnosticSession()
    candidate = _candidate("ecu-1")
    passive = VehicleNetworkDiscoveryResult(ecu_candidates=[candidate])
    active = FakeActiveService()
    runtime = SimpleNamespace(raw_buses={"CAN0": object()}, topology=VehicleNetworkTopology())
    monkeypatch.setattr(routes, "sessions", {"s1": session})
    monkeypatch.setattr(routes, "multi_bus_runtime", {"s1": runtime})
    monkeypatch.setattr(routes, "passive_service", FakePassiveService(passive))
    monkeypatch.setattr(routes, "active_service", active)
    return session, passive, active, runtime


@pytest.mark.asyncio
async def test_active_probe_validates_session_runtime_and_returns_correlation(monkeypatch):
    session, passive, active, runtime = _route_setup(monkeypatch)
    req = routes.ActiveProbeRequest(candidate_ids=["ecu-1"], timeout_ms=500, max_targets=2, inter_probe_ms=0)

    with pytest.raises(HTTPException) as exc:
        await routes.active_probe("missing", req)
    assert exc.value.status_code == 404

    monkeypatch.setattr(routes, "multi_bus_runtime", {})
    with pytest.raises(HTTPException) as exc:
        await routes.active_probe("s1", req)
    assert exc.value.status_code == 409
    monkeypatch.setattr(routes, "multi_bus_runtime", {"s1": runtime})

    response = await routes.active_probe("s1", req)
    assert response == {"session_id": "s1", "results": [], "correlation": {"active_probe_count": 0, "candidates": []}}
    active.probe_candidates.assert_awaited_once()
    args = active.probe_candidates.await_args.args
    assert args[0] == session.session_id


def test_active_map_validates_runtime_and_returns_correlation(monkeypatch):
    session, passive, active, runtime = _route_setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.active_map("missing")
    assert exc.value.status_code == 404

    monkeypatch.setattr(routes, "multi_bus_runtime", {})
    with pytest.raises(HTTPException) as exc:
        routes.active_map("s1")
    assert exc.value.status_code == 409
    monkeypatch.setattr(routes, "multi_bus_runtime", {"s1": runtime})
    assert routes.active_map("s1") == {"active_probe_count": 0, "candidates": []}

def test_active_service_correlates_responder_no_response_and_unmatched_probe_results():
    service = active_service_module.ActiveNetworkDiscoveryService()
    sid = uuid4()
    passive = VehicleNetworkDiscoveryResult(ecu_candidates=[
        _candidate("responder"), _candidate("silent"), _candidate("passive-only"),
    ])
    service._results[str(sid)] = [
        ActiveProbeResult(
            candidate_id="responder", bus="CAN0", request_id=0x7E0, response_id=0x7E8,
            classification="ACTIVE_UDS_RESPONDER", confidence=0.78, responded=True,
            negative_responses=("0xF190:NRC=0x31",),
        ),
        ActiveProbeResult(
            candidate_id="silent", bus="CAN1", request_id=0x7E1, response_id=0x7E9,
            classification="NO_RESPONSE", confidence=0.05, responded=False, error="timeout",
        ),
        ActiveProbeResult(
            candidate_id="extra-active", bus="CAN2", request_id=0x7E2, response_id=0x7EA,
            classification="ACTIVE_UDS_RESPONDER", confidence=0.78, responded=True,
        ),
    ]

    result = service.correlate(sid, passive)
    statuses = {item["candidate_id"]: item["status"] for item in result["candidates"]}
    assert statuses == {
        "responder": "ACTIVE_RESPONDER",
        "silent": "NO_RESPONSE",
        "passive-only": "PASSIVE_ONLY",
    }
    assert result["active_probe_count"] == 3
    assert [item["candidate_id"] for item in result["unmatched_active"]] == ["extra-active"]


@pytest.mark.asyncio
async def test_active_probe_maps_policy_validation_error_to_400(monkeypatch):
    _session, _passive, active, _runtime = _route_setup(monkeypatch)
    request = routes.ActiveProbeRequest(allowed_dids=[], timeout_ms=500, max_targets=1, inter_probe_ms=0)
    with pytest.raises(HTTPException) as exc:
        await routes.active_probe("s1", request)
    assert exc.value.status_code == 400
    assert "read-only DID" in exc.value.detail
    active.probe_candidates.assert_not_awaited()

@pytest.mark.asyncio
async def test_active_service_handles_missing_topology_route_candidate_filter_and_empty_filter(monkeypatch):
    seen = []

    class FakeEngine:
        def __init__(self, policy=None):
            self.policy = policy

        async def probe_many(self, targets, buses):
            seen.extend(targets)
            return []

    monkeypatch.setattr(active_service_module, "ActiveEcuDiscoveryEngine", FakeEngine)
    service = active_service_module.ActiveNetworkDiscoveryService()
    sid = uuid4()
    passive = VehicleNetworkDiscoveryResult(ecu_candidates=[
        _candidate("one", bus="CAN0"),
        _candidate("two", bus="CAN0", request_id=0x7E1, response_id=0x7E9),
    ])
    # The route refers to a missing target ECU. The service must skip it and
    # still keep probing candidates directly available on the bus.
    bad_topology = VehicleNetworkTopology(
        routes=(GatewayRoute("GW-MISSING", "CAN0", "CAN1", "not-present"),)
    )
    targets = await service.probe_candidates(
        sid, passive, {"CAN0": object()}, bad_topology, candidate_ids=["one"],
    )
    assert targets == []
    assert len(seen) == 1
    assert seen[0].candidate_id == "one"
    assert seen[0].gateway_id is None

    seen.clear()
    # An empty candidate filter intentionally behaves like no filter in this API.
    await service.probe_candidates(sid, passive, {"CAN0": object()}, topology=None, candidate_ids=[])
    assert [item.candidate_id for item in seen] == ["one", "two"]
