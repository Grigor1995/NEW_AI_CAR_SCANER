import asyncio
from uuid import uuid4

import pytest

from acquisition.models import AcquisitionStartRequest
from acquisition.service import AcquisitionApiService
from api.telemetry_routes import service as telemetry_service


@pytest.mark.asyncio
async def test_simulator_acquisition_emits_records_updates_status_and_stops(monkeypatch):
    appended = []
    monkeypatch.setattr(telemetry_service, "append", lambda samples: appended.extend(samples) or len(samples))
    service = AcquisitionApiService()
    sid = uuid4()
    status = await service.start_simulator(
        sid, AcquisitionStartRequest(poll_interval_ms=20, pids=[0x0C, 0x99])
    )
    assert status.state == "RUNNING"
    assert status.adapter == "simulator"
    assert status.stats["polls"] == 0

    await asyncio.sleep(0.055)
    mid = service.status(sid)
    assert mid.stats["polls"] >= 1
    assert mid.buffered_records >= 2
    records = service.snapshot(sid, 2)
    assert records[-1].channel == "0x99"
    assert records[-1].numeric_value == 0.0
    assert records[-1].unit is None
    assert appended
    assert all(sample.session_id == sid for sample in appended)

    # Starting an already-running task reuses it and does not reset its counters.
    previous_polls = service.status(sid).stats["polls"]
    repeated = await service.start_simulator(sid, AcquisitionStartRequest(poll_interval_ms=20, pids=[0x0C]))
    assert repeated.stats["polls"] == previous_polls

    stopped = await service.stop(sid)
    assert stopped.state == "STOPPED"
    assert service.status(sid).state == "STOPPED"
    with pytest.raises(KeyError):
        service.status(uuid4())


@pytest.mark.asyncio
async def test_simulator_acquisition_marks_error_when_telemetry_append_fails(monkeypatch):
    service = AcquisitionApiService()
    sid = uuid4()
    def fail(_samples):
        raise RuntimeError("telemetry backend down")
    monkeypatch.setattr(telemetry_service, "append", fail)

    await service.start_simulator(sid, AcquisitionStartRequest(poll_interval_ms=20, pids=[0x0C]))
    for _ in range(30):
        await asyncio.sleep(0.002)
        if service.status(sid).state == "ERROR":
            break
    assert service.status(sid).state == "ERROR"
    assert service.status(sid).stats["errors"] == 1
    stopped = await service.stop(sid)
    assert stopped.state == "STOPPED"
    assert service.snapshot(sid)


@pytest.mark.asyncio
async def test_live_parameter_update_preserves_history_and_rejects_real_adapter(monkeypatch):
    from acquisition.models import SimulatorParameters
    monkeypatch.setattr(telemetry_service, "append", lambda samples: None)
    service = AcquisitionApiService()
    sid = uuid4()
    await service.start_simulator(sid, AcquisitionStartRequest(poll_interval_ms=20))
    try:
        await asyncio.sleep(.025)
        service.set_simulator_parameters(sid, SimulatorParameters(speed_kmh=120, coolant_c=105, rpm=2400))
        await asyncio.sleep(.025)
        rows = service.snapshot(sid, 100)
        speeds = [r.numeric_value for r in rows if r.channel == "0x0D"]
        assert 40 in speeds and speeds[-1] == 120
        service._states[sid].adapter = "usb"
        with pytest.raises(ValueError, match="simulator"):
            service.set_simulator_parameters(sid, SimulatorParameters())
    finally:
        await service.stop(sid)


def test_simulator_parameters_reject_nonfinite_and_out_of_range():
    from acquisition.models import SimulatorParameters
    from pydantic import ValidationError
    for values in ({"speed_kmh": -1}, {"coolant_c": float("nan")}, {"throttle_percent": 101}):
        with pytest.raises(ValidationError):
            SimulatorParameters(**values)
