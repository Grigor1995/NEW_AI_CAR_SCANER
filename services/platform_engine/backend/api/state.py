from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from diagnostic.models import DiagnosticSession
from diagnostic.session_persistence import persistence
from device.manager import vci_manager as vci_manager


class GlobalSessionRegistry(MutableMapping[str, DiagnosticSession]):
    """Process cache backed by shared persistence.

    Desktop/mobile never own session state. With DATABASE_URL configured,
    PostgreSQL is the shared source of truth and this mapping is only a cache.
    """

    def __init__(self):
        self._cache: dict[str, DiagnosticSession] = {}

    def refresh(self) -> None:
        if persistence.enabled:
            self._cache = persistence.load()

    def __getitem__(self, key: str) -> DiagnosticSession:
        if persistence.enabled:
            loaded = persistence.load()
            if key in loaded:
                self._cache[key] = loaded[key]
        return self._cache[key]

    def __setitem__(self, key: str, value: DiagnosticSession) -> None:
        self._cache[key] = value
        if persistence.enabled:
            persistence.save_one(key, value)

    def __delitem__(self, key: str) -> None:
        del self._cache[key]

    def __iter__(self) -> Iterator[str]:
        self.refresh()
        return iter(self._cache)

    def __len__(self) -> int:
        self.refresh()
        return len(self._cache)

    def values(self):
        self.refresh()
        return self._cache.values()

    def items(self):
        self.refresh()
        return self._cache.items()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


sessions = GlobalSessionRegistry()


def load_persisted_sessions() -> None:
    sessions.refresh()


def persist_sessions() -> None:
    if persistence.enabled:
        persistence.save_all(dict(sessions._cache))
