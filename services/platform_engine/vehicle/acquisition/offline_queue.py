from __future__ import annotations
import json
from pathlib import Path
from threading import Lock
from typing import Any

class OfflineQueue:
    """Durable FIFO queue using JSON Lines. Safe for single-process acquisition workers."""
    def __init__(self, path: str | Path, *, max_items: int = 100_000):
        self.path = Path(path)
        self.max_items = max_items
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, item: dict[str, Any]) -> None:
        with self._lock:
            lines = self._read_lines()
            if len(lines) >= self.max_items:
                lines = lines[-(self.max_items - 1):]
            lines.append(item)
            self._write_lines(lines)

    def peek(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return self._read_lines()[:max(0, limit)]

    def ack(self, count: int) -> int:
        with self._lock:
            lines = self._read_lines()
            removed = min(max(0, count), len(lines))
            self._write_lines(lines[removed:])
            return removed

    def size(self) -> int:
        with self._lock:
            return len(self._read_lines())

    def clear(self) -> None:
        with self._lock:
            self._write_lines([])

    def _read_lines(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        result = []
        for line in self.path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                result.append(json.loads(line))
        return result

    def _write_lines(self, lines: list[dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + '.tmp')
        body = ''.join(json.dumps(x, separators=(',', ':'), sort_keys=True) + '\n' for x in lines)
        tmp.write_text(body, encoding='utf-8')
        tmp.replace(self.path)
