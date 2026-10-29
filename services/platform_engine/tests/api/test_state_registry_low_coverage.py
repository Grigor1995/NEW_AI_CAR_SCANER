from diagnostic.models import DiagnosticSession

import api.state as state


class FakePersistence:
    def __init__(self, *, enabled=False, loaded=None):
        self.enabled = enabled
        self.loaded = loaded or {}
        self.saved_one = []
        self.saved_all = []
    def load(self):
        return dict(self.loaded)
    def save_one(self, key, value):
        self.saved_one.append((key, value))
    def save_all(self, sessions):
        self.saved_all.append(dict(sessions))


def test_registry_mapping_operations_without_persistence(monkeypatch):
    monkeypatch.setattr(state, "persistence", FakePersistence(enabled=False))
    registry = state.GlobalSessionRegistry()
    session = DiagnosticSession()

    registry["s1"] = session
    assert registry["s1"] is session
    assert registry.get("missing") is None
    assert list(registry) == ["s1"]
    assert len(registry) == 1
    assert list(registry.values()) == [session]
    assert list(registry.items()) == [("s1", session)]
    del registry["s1"]
    assert len(registry) == 0


def test_registry_refresh_and_lookup_use_persisted_snapshot(monkeypatch):
    persisted_session = DiagnosticSession()
    persistence = FakePersistence(enabled=True, loaded={"session": persisted_session})
    monkeypatch.setattr(state, "persistence", persistence)
    registry = state.GlobalSessionRegistry()

    registry.refresh()
    assert registry["session"] is persisted_session
    assert len(registry) == 1


def test_registry_keeps_cached_value_when_database_snapshot_lacks_key(monkeypatch):
    cached = DiagnosticSession()
    persistence = FakePersistence(enabled=True, loaded={})
    monkeypatch.setattr(state, "persistence", persistence)
    registry = state.GlobalSessionRegistry()
    registry._cache["cached"] = cached

    assert registry["cached"] is cached


def test_registry_writes_single_and_all_sessions_to_persistence(monkeypatch):
    persistence = FakePersistence(enabled=True)
    monkeypatch.setattr(state, "persistence", persistence)
    registry = state.GlobalSessionRegistry()
    session = DiagnosticSession()

    registry["session-1"] = session
    assert persistence.saved_one == [("session-1", session)]

    registry._cache["session-2"] = DiagnosticSession()
    state.sessions._cache.clear()
    state.sessions._cache["persisted"] = session
    try:
        state.persist_sessions()
        assert persistence.saved_all[-1] == {"persisted": session}
    finally:
        state.sessions._cache.clear()


def test_persistence_helpers_do_nothing_when_disabled(monkeypatch):
    persistence = FakePersistence(enabled=False)
    monkeypatch.setattr(state, "persistence", persistence)
    state.load_persisted_sessions()
    state.persist_sessions()
    assert persistence.saved_one == []
    assert persistence.saved_all == []
