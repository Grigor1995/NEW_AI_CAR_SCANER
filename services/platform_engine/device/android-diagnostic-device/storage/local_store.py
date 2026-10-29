import json
import sqlite3
from pathlib import Path
from typing import Any

class LocalDiagnosticStore:
    """Small offline-first SQLite store. Production Android uses the same logical schema via Drift/SQLite."""
    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, updated_at REAL NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS sync_queue (id TEXT PRIMARY KEY, operation TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL)")
        self.db.commit()
    def upsert(self, record_id: str, kind: str, payload: dict[str, Any], updated_at: float) -> None:
        self.db.execute("INSERT INTO records(id,kind,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,payload=excluded.payload,updated_at=excluded.updated_at", (record_id, kind, json.dumps(payload), updated_at))
        self.db.commit()
    def get(self, record_id: str):
        row = self.db.execute("SELECT id,kind,payload,updated_at FROM records WHERE id=?", (record_id,)).fetchone()
        if not row: return None
        return {"id": row[0], "kind": row[1], "payload": json.loads(row[2]), "updated_at": row[3]}

    def close(self) -> None:
        """Release the underlying SQLite connection."""
        self.db.close()

    def __enter__(self) -> "LocalDiagnosticStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
