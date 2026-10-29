from __future__ import annotations
import asyncio
from collections import deque
from typing import Awaitable, Callable
from uuid import UUID
from .models import AcquisitionRecord, AcquisitionState, ReconnectPolicy
from .offline_queue import OfflineQueue
from .sources import AcquisitionSource

RecordSink = Callable[[list[AcquisitionRecord]], Awaitable[None] | None]

class AcquisitionManager:
    """Lifecycle, buffering and reconnect manager shared by desktop/mobile/device clients."""
    def __init__(self, source: AcquisitionSource, *, session_id: UUID, poll_interval_s: float = 0.1, buffer_size: int = 10_000, reconnect_policy: ReconnectPolicy | None = None, offline_queue: OfflineQueue | None = None, sink: RecordSink | None = None):
        if poll_interval_s <= 0: raise ValueError('poll_interval_s must be > 0')
        self.source=source; self.session_id=session_id; self.poll_interval_s=poll_interval_s; self.buffer_size=buffer_size
        self.reconnect_policy = reconnect_policy or ReconnectPolicy()
        self.offline_queue = offline_queue
        self.sink = sink
        self.state=AcquisitionState.STOPPED
        self._buffer: deque[AcquisitionRecord]=deque(maxlen=buffer_size)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._sequence = 0
        self.stats={'polls':0,'records':0,'errors':0,'reconnects':0,'queued_offline':0}

    async def start(self) -> None:
        if self._task and not self._task.done(): return
        self._stop.clear(); self.state=AcquisitionState.STARTING
        await self._connect_with_retry()
        self.state=AcquisitionState.RUNNING
        self._task=asyncio.create_task(self._run(), name=f'acquisition-{self.session_id}')

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
            self._task=None
        try: await self.source.disconnect()
        finally: self.state=AcquisitionState.STOPPED

    def snapshot(self, limit: int = 100) -> list[AcquisitionRecord]:
        if limit < 0: raise ValueError('limit must be >= 0')
        return list(self._buffer)[-limit:] if limit else []

    async def _connect_with_retry(self) -> None:
        last_exc=None
        for attempt in range(1, self.reconnect_policy.max_attempts + 1):
            if self._stop.is_set(): return
            try:
                await self.source.connect(); return
            except Exception as exc:
                last_exc=exc; self.stats['errors'] += 1; self.state=AcquisitionState.RECONNECTING
                if attempt >= self.reconnect_policy.max_attempts: break
                await asyncio.sleep(self.reconnect_policy.delay(attempt))
        self.state=AcquisitionState.ERROR
        raise ConnectionError(f'acquisition connect failed: {last_exc}')

    async def _run(self) -> None:
        while not self._stop.is_set():
            started = asyncio.get_running_loop().time()
            try:
                poll_sequence = self._sequence
                self._sequence += 1
                records = await self.source.read_once(self.session_id, poll_sequence)
                self.stats['polls'] += 1
                if records:
                    self._buffer.extend(records); self.stats['records'] += len(records)
                    delivered = await self._deliver(records)
                    if not delivered:
                        self._queue(records)
            except Exception:
                self.stats['errors'] += 1
                self.state=AcquisitionState.RECONNECTING
                self.stats['reconnects'] += 1
                try:
                    await self.source.disconnect()
                except Exception:
                    pass
                try:
                    await self._connect_with_retry()
                    self.state=AcquisitionState.RUNNING
                except Exception:
                    self.state=AcquisitionState.DEGRADED
                    await asyncio.sleep(self.reconnect_policy.max_backoff_s)
            elapsed = asyncio.get_running_loop().time() - started
            await asyncio.sleep(max(0.0, self.poll_interval_s - elapsed))

    async def _deliver(self, records: list[AcquisitionRecord]) -> bool:
        if self.sink is None: return True
        try:
            result = self.sink(records)
            if asyncio.iscoroutine(result): await result
            return True
        except Exception:
            return False

    def _queue(self, records: list[AcquisitionRecord]) -> None:
        if self.offline_queue is None: return
        for record in records:
            self.offline_queue.append(_record_to_dict(record)); self.stats['queued_offline'] += 1

def _record_to_dict(record: AcquisitionRecord) -> dict:
    return {
        'id': str(record.id), 'session_id': str(record.session_id), 'timestamp_ns': record.timestamp_ns,
        'source_type': record.source_type.value, 'channel': record.channel, 'numeric_value': record.numeric_value,
        'unit': record.unit, 'raw_hex': record.raw.hex() if record.raw else None, 'sequence': record.sequence,
        'quality': record.quality, 'metadata': record.metadata,
    }
