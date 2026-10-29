from pathlib import Path
import json

from backend.scripts.seed_vehicle_catalog import build_rows


def test_vehicle_fitment_seed_expands_years_and_engines():
    data_path = Path(__file__).parents[1] / "data" / "vehicle_fitment_catalog.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    rows = build_rows(payload)

    assert rows
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert all(row["make"] and row["model"] and row["engine"] for row in rows)

    w211 = [
        row for row in rows
        if row["make"] == "Mercedes-Benz"
        and row["model"] == "E-Class"
        and row["chassis"] == "W211"
        and row["year"] == 2006
    ]
    assert {row["engine"] for row in w211} >= {
        "M112 E32 3.2",
        "M113 E50 5.0",
        "M272 E35 3.5",
        "OM642 3.0 V6",
    }
    assert any(row["engine"] == "M272 E35 3.5" and row["ecu"] == "ME9.7" for row in w211)
