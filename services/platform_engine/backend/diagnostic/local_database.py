"""Initialize the Desktop-owned SQLite catalog without replacing user records."""
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from diagnostic.database import database_engine
from diagnostic.db_models import VehicleCatalogEntryRow
from backend.scripts.seed_vehicle_catalog import build_rows


def prepare_local_database(url: str, root: Path) -> int:
    if make_url(url).get_backend_name() != "sqlite":
        raise ValueError("Desktop local database initialization requires SQLite")
    rows = build_rows(json.loads((root / "data/vehicle_fitment_catalog.json").read_text(encoding="utf-8")))
    engine = database_engine(url)
    try:
        VehicleCatalogEntryRow.__table__.create(engine, checkfirst=True)
        with Session(engine) as db:
            existing = set(db.scalars(select(VehicleCatalogEntryRow.id)))
            missing = [VehicleCatalogEntryRow(**row) for row in rows if row["id"] not in existing]
            db.add_all(missing)
            db.commit()
        return len(missing)
    finally:
        engine.dispose()
