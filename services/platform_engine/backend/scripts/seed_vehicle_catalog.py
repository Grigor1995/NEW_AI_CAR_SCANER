from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from diagnostic.db_models import VehicleCatalogEntryRow


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "vehicle_fitment_catalog.json"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://diagnostic:diagnostic@localhost:5432/diagnostic",
)


def stable_id(make: str, model: str, chassis: str | None, year: int, engine: str, ecu: str | None) -> str:
    raw = "|".join((make, model, chassis or "", str(year), engine, ecu or ""))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def expand_years(ranges: list[list[int]]) -> list[int]:
    years: set[int] = set()
    for item in ranges:
        if len(item) != 2:
            raise ValueError(f"Invalid year range: {item!r}")
        start, end = item
        if start > end:
            start, end = end, start
        years.update(range(int(start), int(end) + 1))
    return sorted(years)


def build_rows(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for entry in payload.get("entries", []):
        make = str(entry["make"]).strip()
        model = str(entry["model"]).strip()
        chassis = str(entry.get("chassis", "")).strip() or None
        years = expand_years(entry.get("year_ranges", []))
        for engine in entry.get("engines", []):
            engine_name = str(engine["name"]).strip()
            ecus = [str(x).strip() for x in engine.get("ecus", []) if str(x).strip()]
            fuels = [str(x).strip().lower() for x in engine.get("fuel", []) if str(x).strip()]
            for year in years:
                for ecu in (ecus or [None]):
                    rows.append(
                        {
                            "id": stable_id(make, model, chassis, year, engine_name, ecu),
                            "make": make,
                            "model": model,
                            "chassis": chassis,
                            "year": year,
                            "engine": engine_name,
                            "ecu": ecu,
                            "fuel": fuels,
                            "source": payload.get("source", "project-curated-seed"),
                            "scope": payload.get("scope", "curated-fitment"),
                        }
                    )
    return rows


def main() -> None:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    rows = build_rows(payload)

    engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
    VehicleCatalogEntryRow.__table__.create(engine, checkfirst=True)

    with Session(engine) as db:
        # The JSON seed is authoritative. Rebuild this catalog atomically so
        # removed/changed fitment records cannot remain as stale rows.
        db.query(VehicleCatalogEntryRow).delete(synchronize_session=False)
        db.add_all([VehicleCatalogEntryRow(**row) for row in rows])
        db.commit()

    print(f"Seeded {len(rows)} vehicle catalog rows from {DATA_FILE}")


if __name__ == "__main__":
    main()
