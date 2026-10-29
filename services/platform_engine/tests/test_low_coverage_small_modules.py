from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from diagnostic.models import DTC, EvidenceSource, EvidenceStatus, Symptom
from ai.reasoning.evidence_extractor import StructuredEvidenceExtractor
from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.can.models import CanFrame
from vehicle.uds.decoder import format_uds_dtc, parse_dtc_information


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_evidence_extractor_empty_patterns_normalized_symptom_and_dtc_statuses():
    extractor = StructuredEvidenceExtractor()
    assert extractor.extract("  \n  ") == []

    extracted = extractor.extract(
        "Engine shakes on LPG under load below 2000 RPM; petrol is normal",
        EvidenceSource.TECHNICIAN_OBSERVED,
    )
    facts = [item.fact for item in extracted]
    assert facts[0] == "Engine shakes on LPG under load below 2000 RPM; petrol is normal"
    assert {"fuel_mode_lpg", "fuel_mode_petrol", "misfire", "acceleration", "below_2000_rpm", "petrol_normal"} <= set(facts)
    assert all(item.source is EvidenceSource.TECHNICIAN_OBSERVED for item in extracted)

    symptom = Symptom(raw_text="rough idle", normalized={"rpm": 650, "fuel": "LPG"})
    symptom_evidence = extractor.from_symptom(symptom)
    assert any(item.fact == "rpm=650" and item.confidence == 0.9 for item in symptom_evidence)
    measured = extractor.from_dtc(DTC(code="p0302", source=EvidenceSource.ECU_REPORTED))
    reported = extractor.from_dtc(DTC(code="p0171", source=EvidenceSource.USER_REPORTED))
    assert measured.fact == "P0302" and measured.status is EvidenceStatus.MEASURED and measured.confidence == 0.95
    assert reported.status is EvidenceStatus.REPORTED and reported.confidence == 0.8


def test_uds_dtc_decoder_all_prefixes_boundaries_and_payload_shapes():
    assert format_uds_dtc(0x030200) == "P030200"
    assert format_uds_dtc(0x430102).startswith("C")
    assert format_uds_dtc(0x830102).startswith("B")
    assert format_uds_dtc(0xC30102).startswith("U")
    with pytest.raises(ValueError, match="uint24"):
        format_uds_dtc(-1)
    with pytest.raises(ValueError, match="uint24"):
        format_uds_dtc(0x1000000)

    assert parse_dtc_information(b"") == []
    assert parse_dtc_information(b"\x02") == []
    with pytest.raises(ValueError, match="malformed"):
        parse_dtc_information(b"\x00\xff")

    records = parse_dtc_information(bytes([0x02, 0xFF, 0x03, 0x02, 0x00, 0x28, 0xC1, 0x23, 0x45, 0x01, 0xAA]))
    assert [(r.raw_dtc, r.status_byte) for r in records] == [(0x030200, 0x28), (0xC12345, 0x01)]
    assert records[1].confirmed is False  # testFailed alone is not confirmedDTC.
    assert records[0].confirmed is True   # confirmedDTC is status bit 3.


def test_device_health_monitor_ok_warning_and_critical_levels():
    module = _load_module(
        "device_health_monitor_test",
        "device/android-diagnostic-device/health/monitor.py",
    )
    monitor = module.HealthMonitor()
    healthy = monitor.evaluate(80, 40, 4000, "online")
    assert healthy.level is module.HealthLevel.OK
    warning = monitor.evaluate(25, 66, 1500, "wifi")
    assert warning.level is module.HealthLevel.WARNING
    assert warning.connectivity == "wifi"
    assert monitor.evaluate(10, 50, 5000, "offline").level is module.HealthLevel.CRITICAL
    assert monitor.evaluate(90, 75, 5000, "online").level is module.HealthLevel.CRITICAL
    assert monitor.evaluate(90, 40, 499, "online").level is module.HealthLevel.CRITICAL


def test_ota_manifest_accepts_secure_urls_and_rejects_bad_values():
    module = _load_module(
        "device_ota_manifest_test",
        "device/android-diagnostic-device/ota/manifest.py",
    )
    digest = "a" * 64
    module.OtaPolicy.validate(module.OtaManifest("1.2.3", "https://example.test/update.bin", digest, "1.0.0"))
    module.OtaPolicy.validate(module.OtaManifest("1.2.3", "file:///tmp/update.bin", digest, "1.0.0", True))
    for manifest in (
        module.OtaManifest("", "https://example.test/a", digest, "1.0"),
        module.OtaManifest("1.0", "https://example.test/a", "short", "1.0"),
    ):
        with pytest.raises(ValueError, match="Invalid OTA manifest"):
            module.OtaPolicy.validate(manifest)
    with pytest.raises(ValueError, match="approved transport"):
        module.OtaPolicy.validate(module.OtaManifest("1.0", "http://example.test/a", digest, "1.0"))


@pytest.mark.asyncio
async def test_simulated_can_bus_tx_rx_hooks_timeouts_and_empty_tx_queue():
    bus = SimulatedCanBus()
    assert bus.pop_tx() is None
    assert await bus.receive(timeout_ms=1) is None

    seen_tx = []
    seen_rx = []
    async def async_tx(frame):
        await asyncio.sleep(0)
        seen_tx.append(frame.arbitration_id)
    def sync_rx(frame):
        seen_rx.append(frame.arbitration_id)

    bus.add_tx_hook(async_tx)
    bus.add_rx_hook(sync_rx)
    tx = CanFrame(0x7E0, b"\x01\x03")
    await bus.send(tx)
    assert bus.pop_tx() == tx
    assert seen_tx == [0x7E0]

    rx = CanFrame(0x7E8, b"\x02\x41\x0C")
    bus.inject(rx)
    assert seen_rx == [0x7E8]
    assert await bus.receive(timeout_ms=10) == rx

    async_rx = []
    async def async_rx_hook(frame):
        await asyncio.sleep(0)
        async_rx.append(frame.arbitration_id)
    bus.add_rx_hook(async_rx_hook)
    bus.inject(CanFrame(0x7E9, b"\\x01"))
    await asyncio.sleep(0.001)
    assert async_rx == [0x7E9]

def test_simulated_can_bus_closes_async_hook_when_injected_without_event_loop():
    bus = SimulatedCanBus()
    calls = []

    async def async_hook(frame):
        calls.append(frame.arbitration_id)

    bus.add_rx_hook(async_hook)
    # A synchronous caller cannot schedule an async hook; the implementation
    # must close the unused coroutine and avoid a RuntimeWarning.
    bus.inject(CanFrame(0x7E8, b"\\x01"))
    assert calls == []
