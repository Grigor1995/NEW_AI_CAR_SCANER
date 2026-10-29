from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from diagnostic.database import database_engine
from diagnostic.db_models import VehicleCatalogEntryRow
from diagnostic.local_database import prepare_local_database
import api.vehicle_catalog_routes as catalog


ROOT = Path(__file__).resolve().parents[2]


def test_local_seed_is_repeatable_and_keeps_user_edits(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'local.sqlite'}"
    count = prepare_local_database(url, ROOT)
    assert count > 0
    engine = database_engine(url)
    try:
        with Session(engine) as db:
            row = db.scalars(select(VehicleCatalogEntryRow)).first()
            row.source = "user-edited"
            key = row.id
            db.commit()
        assert prepare_local_database(url, ROOT) == 0
        with Session(engine) as db:
            assert db.get(VehicleCatalogEntryRow, key).source == "user-edited"
        monkeypatch.setattr(catalog, "_engine", engine)
        entries = catalog.list_entries()
        stored = [entry for entry in entries if entry["scope"] != "generation-reference-not-vin-fitment"]
        assert len(stored) == count
        assert any(entry["scope"] == "generation-reference-not-vin-fitment" for entry in entries)
        assert all(isinstance(row["fuel"], list) for row in entries)
        assert any(row["chassis"] == "W211" for row in entries)
    finally:
        engine.dispose()


def test_local_initializer_refuses_external_database():
    import pytest
    with pytest.raises(ValueError, match="requires SQLite"):
        prepare_local_database("postgresql+psycopg://localhost/unused", ROOT)


def test_postgres_driver_gets_a_bounded_timeout(monkeypatch):
    import diagnostic.database as database
    calls = {}
    monkeypatch.setenv("AI_CAR_DB_CONNECT_TIMEOUT_S", "3")
    monkeypatch.setattr(database, "create_engine", lambda url, **kwargs: calls.update(kwargs))
    database.database_engine("postgresql+psycopg://localhost/unused?connect_timeout=600")
    assert calls["connect_args"]["connect_timeout"] == 3
