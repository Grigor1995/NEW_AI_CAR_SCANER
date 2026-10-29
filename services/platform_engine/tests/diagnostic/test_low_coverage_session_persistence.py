from __future__ import annotations

import logging

from diagnostic.models import DiagnosticSession, Vehicle
import diagnostic.session_persistence as persistence_module
from diagnostic.session_persistence import DiagnosticSessionPersistence, DiagnosticSessionStateRow


def _session(model: str = "W211") -> DiagnosticSession:
    return DiagnosticSession(vehicle=Vehicle(make="Mercedes-Benz", model=model, year=2006))


def test_disabled_persistence_is_a_safe_noop(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    store = DiagnosticSessionPersistence()

    assert store.enabled is False
    assert store.load() == {}
    store.save_one("unused", _session())
    store.save_all({"unused": _session()})
    store.close()
    assert store.engine is None


def test_save_one_inserts_then_updates_and_save_all_upserts(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sessions.sqlite'}")
    store = DiagnosticSessionPersistence()
    try:
        first = _session()
        store.save_one("first", first)
        first.vehicle.model = "W211 updated"
        store.save_one("first", first)
        second = _session("W245")
        store.save_all({"first": first, "second": second})

        restored = store.load()
        assert restored["first"].vehicle.model == "W211 updated"
        assert restored["second"].vehicle.model == "W245"
    finally:
        store.close()
    assert store.engine is None


def test_load_skips_invalid_rows_but_keeps_valid_sessions(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'invalid.sqlite'}")
    store = DiagnosticSessionPersistence()
    try:
        valid = _session()
        store.save_one("valid", valid)
        with persistence_module.DbSession(store.engine) as db:
            db.add(DiagnosticSessionStateRow(session_id="invalid", payload={"vehicle": {"make": "missing-model"}}))
            db.commit()

        with caplog.at_level(logging.ERROR, logger=persistence_module.__name__):
            restored = store.load()

        assert list(restored) == ["valid"]
        assert "Skipping invalid persisted session invalid" in caplog.text
    finally:
        store.close()


def test_load_returns_empty_when_database_session_fails(monkeypatch, caplog):
    class BrokenDb:
        def __enter__(self):
            raise RuntimeError("database unavailable")

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.delenv("DATABASE_URL", raising=False)
    store = DiagnosticSessionPersistence()
    store.enabled = True
    store.engine = object()
    monkeypatch.setattr(persistence_module, "DbSession", lambda _engine: BrokenDb())

    with caplog.at_level(logging.ERROR, logger=persistence_module.__name__):
        assert store.load() == {}
    assert "Failed to load persisted diagnostic sessions" in caplog.text


def test_save_all_swallows_database_errors_and_close_disposes(monkeypatch, caplog):
    class BrokenDb:
        def __enter__(self):
            raise RuntimeError("write failed")

        def __exit__(self, exc_type, exc, traceback):
            return False

    class Engine:
        def __init__(self):
            self.disposed = False

        def dispose(self):
            self.disposed = True

    monkeypatch.delenv("DATABASE_URL", raising=False)
    store = DiagnosticSessionPersistence()
    engine = Engine()
    store.enabled = True
    store.engine = engine
    monkeypatch.setattr(persistence_module, "DbSession", lambda _engine: BrokenDb())

    with caplog.at_level(logging.ERROR, logger=persistence_module.__name__):
        store.save_all({"s": _session()})
    assert "Failed to persist diagnostic sessions" in caplog.text

    store.close()
    assert engine.disposed is True
    assert store.engine is None
