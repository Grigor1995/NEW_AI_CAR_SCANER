from vehicle.can.models import CanFrame
from vehicle.network.discovery import VehicleNetworkDiscoveryEngine, CanIdObservation


def frame(fid: int, ts: int, data: bytes = b"\x10\x03"):
    return CanFrame(arbitration_id=fid, data=data, timestamp_ns=ts)


def test_profiles_and_periodicity():
    result = VehicleNetworkDiscoveryEngine().analyze(
        [frame(0x100, 0), frame(0x100, 100_000_000), frame(0x100, 200_000_000)], bus="CAN0"
    )
    p = result.profiles[0]
    assert p.arbitration_id == 0x100
    assert p.frame_count == 3
    assert p.periodicity_ms == 100.0


def test_infers_uds_request_response_pair_without_confirming_ecu():
    obs = [
        CanIdObservation("CAN0", 0x7E0, 0, 2, "1003"),
        CanIdObservation("CAN0", 0x7E8, 2_000_000, 2, "5003"),
        CanIdObservation("CAN0", 0x7E0, 100_000_000, 2, "1003"),
        CanIdObservation("CAN0", 0x7E8, 102_000_000, 2, "5003"),
    ]
    result = VehicleNetworkDiscoveryEngine().analyze_observations(obs)
    assert [(p.request_id, p.response_id) for p in result.uds_pairs] == [(0x7E0, 0x7E8)]
    assert result.ecu_candidates[0].classification == "UDS_REQUEST_RESPONSE_INFERRED"
    assert result.ecu_candidates[0].confidence < 1.0


def test_unpaired_active_ids_are_observed_nodes():
    result = VehicleNetworkDiscoveryEngine().analyze(
        [frame(0x120, 0), frame(0x120, 10_000_000)], bus="CAN1"
    )
    assert len(result.ecu_candidates) == 1
    candidate = result.ecu_candidates[0]
    assert candidate.classification == "OBSERVED_CAN_NODE"
    assert candidate.request_id is None
    assert candidate.response_id is None


def test_multi_bus_analysis():
    engine = VehicleNetworkDiscoveryEngine()
    obs = [
        CanIdObservation("CAN0", 0x700, 0, 1, "01"),
        CanIdObservation("CAN0", 0x700, 100_000_000, 1, "01"),
        CanIdObservation("CAN1", 0x7E0, 0, 2, "1003"),
        CanIdObservation("CAN1", 0x7E8, 1_000_000, 2, "5003"),
        CanIdObservation("CAN1", 0x7E0, 100_000_000, 2, "1003"),
        CanIdObservation("CAN1", 0x7E8, 101_000_000, 2, "5003"),
    ]
    result = engine.analyze_observations(obs)
    assert {p.bus for p in result.profiles} == {"CAN0", "CAN1"}
    assert any(p.bus == "CAN1" for p in result.uds_pairs)
