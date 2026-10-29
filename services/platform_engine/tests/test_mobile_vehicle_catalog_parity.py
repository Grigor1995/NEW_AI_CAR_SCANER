"""Cross-platform offline vehicle snapshot contract.

Run from finalbuild: python -m pytest tests/test_mobile_vehicle_catalog_parity.py -q
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = (
    ROOT / "shared/vehicle_catalog.json",
    ROOT / "apps/mobile-android/app/src/main/assets/vehicle_catalog.json",
    ROOT / "apps/mobile-ios/AICarScanner/VehicleCatalog/vehicle_catalog.json",
)


def test_mobile_snapshots_are_byte_identical_to_desktop():
    source = SNAPSHOTS[0].read_bytes()
    for path in SNAPSHOTS[1:]:
        assert path.read_bytes() == source, f"{path} differs from Desktop shared snapshot"


def test_snapshot_schema_and_reference_vehicle():
    document = json.loads(SNAPSHOTS[0].read_text(encoding="utf-8"))
    rows = document["vehicles"]
    assert rows and document["schema_version"] == 1
    assert all(set(("make", "model", "chassis", "year", "engine", "ecu", "fuel")) <= row.keys() for row in rows)
    assert any(
        row["make"] == "Mercedes-Benz"
        and row["model"] == "E-Class"
        and row["chassis"] == "W211"
        and row["year"] == 2006
        and row["engine"] == "M272 E35 3.5"
        for row in rows
    )
