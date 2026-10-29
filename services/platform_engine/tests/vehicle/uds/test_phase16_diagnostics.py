import pytest
from uuid import uuid4
from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.adapters.uds_simulator import UdsEcuSimulator
from vehicle.isotp.stack import IsoTpStack
from vehicle.protocol.trace import ProtocolTraceRecorder, TracedCanBus
from vehicle.uds.client import UdsClient
from vehicle.uds.decoder import format_uds_dtc, parse_dtc_information
from vehicle.uds.diagnostics import UdsDiagnosticSession


def test_format_and_parse_dtc():
    raw = 0x030200
    assert format_uds_dtc(raw) == 'P030200'
    payload = bytes([0x02, 0xFF]) + raw.to_bytes(3, 'big') + b'\x28'
    records = parse_dtc_information(payload)
    assert len(records) == 1
    assert records[0].code == 'P030200'
    assert records[0].status_byte == 0x28


@pytest.mark.asyncio
async def test_read_only_uds_identity_and_dtcs_multiframe():
    bus = SimulatedCanBus(); UdsEcuSimulator(bus, vin='VINTEST1234567890')
    recorder = ProtocolTraceRecorder(session_id=uuid4()); traced = TracedCanBus(bus, recorder)
    client = UdsClient(IsoTpStack(traced, 0x7E0, 0x7E8))
    diag = UdsDiagnosticSession(client)
    identity = await diag.identify_ecu()
    assert identity.vin == 'VINTEST1234567890'
    records = await diag.read_dtcs()
    assert records and records[0].status_byte == 0x28
    assert len(recorder.snapshot()) >= 8
    assert diag.supports_clear_dtc is False
