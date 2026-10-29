from dataclasses import dataclass
import json, sqlite3, time, uuid

@dataclass(frozen=True)
class SyncOperation:
    id: str
    operation: str
    payload: dict
    created_at: float

class SyncQueue:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
    def enqueue(self, operation: str, payload: dict) -> SyncOperation:
        item = SyncOperation(str(uuid.uuid4()), operation, payload, time.time())
        self.db.execute("INSERT INTO sync_queue(id,operation,payload,created_at) VALUES(?,?,?,?)", (item.id,item.operation,json.dumps(item.payload),item.created_at))
        self.db.commit()
        return item
    def pending(self, limit: int = 100):
        rows = self.db.execute("SELECT id,operation,payload,created_at FROM sync_queue ORDER BY created_at LIMIT ?", (limit,)).fetchall()
        return [SyncOperation(r[0],r[1],json.loads(r[2]),r[3]) for r in rows]
    def acknowledge(self, operation_id: str):
        self.db.execute("DELETE FROM sync_queue WHERE id=?", (operation_id,)); self.db.commit()
