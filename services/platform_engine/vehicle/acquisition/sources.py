from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable
from time import time_ns
from uuid import UUID
from vehicle.obd.client import GenericObdClient
from vehicle.can.models import CanFrame
from vehicle.uds.client import UdsClient
from .models import AcquisitionRecord, AcquisitionSourceType

class AcquisitionSource(ABC):
    source_type: AcquisitionSourceType
    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
    @abstractmethod
    async def read_once(self, session_id: UUID, sequence: int) -> list[AcquisitionRecord]: ...

class ObdPollingSource(AcquisitionSource):
    source_type = AcquisitionSourceType.OBD_PID
    def __init__(self, client: GenericObdClient, pids: list[int] | None = None):
        self.client = client
        self._requested_pids = list(pids if pids is not None else [0x0C, 0x05, 0x0D, 0x11])
        self.pids = list(self._requested_pids)
        self._pid_names = {0x0C:'rpm', 0x05:'coolant_c', 0x0D:'speed_kmh', 0x11:'throttle_percent'}
        self._decoders = {
            0x0C: self.client.protocol.rpm,
            0x05: self.client.protocol.coolant_c,
            0x0D: self.client.protocol.speed_kmh,
            0x11: self.client.protocol.throttle_percent,
        }
    async def connect(self) -> None:
        await self.client.connect()
        capability_reader = getattr(self.client, "supported_live_commands", None)
        if capability_reader is not None:
            try:
                commands = await capability_reader()
                supported = {int(command[2:], 16) for command in commands}
                self.pids = [pid for pid in self._requested_pids if pid in supported]
                if not self.pids:
                    raise ValueError("Vehicle reports no supported channels for this live plan")
            except BaseException:
                await self.client.disconnect()
                raise
    async def disconnect(self) -> None:
        await self.client.disconnect()
    async def read_once(self, session_id: UUID, sequence: int) -> list[AcquisitionRecord]:
        out=[]
        for pid in self.pids:
            try:
                raw = await self.client.read_pid(pid)
                decoder = self._decoders.get(pid)
                value = float(decoder(raw)) if decoder else None
                name = self._pid_names.get(pid, f'pid_0x{pid:02X}')
                unit = {'rpm':'rpm','coolant_c':'C','speed_kmh':'km/h','throttle_percent':'%'}.get(name)
                out.append(AcquisitionRecord(session_id=session_id, timestamp_ns=time_ns(), source_type=self.source_type, channel=name, numeric_value=value, unit=unit, raw=raw if isinstance(raw, bytes) else None, sequence=sequence, metadata={'pid': pid}))
            except Exception as exc:
                transport = getattr(self.client, "transport", None)
                if transport is not None and not getattr(transport, "connected", True):
                    # Let AcquisitionManager enter its reconnect path instead of
                    # emitting endless INVALID samples from a closed transport.
                    raise
                out.append(AcquisitionRecord(session_id=session_id, timestamp_ns=time_ns(), source_type=self.source_type, channel=self._pid_names.get(pid, f'pid_0x{pid:02X}'), numeric_value=None, quality='INVALID', sequence=sequence, metadata={'pid': pid, 'error': str(exc)}))
        return out

class CanStreamSource(AcquisitionSource):
    source_type = AcquisitionSourceType.CAN_FRAME
    def __init__(self, bus, *, timeout_ms: int = 100):
        self.bus = bus
        self.timeout_ms = timeout_ms
    async def connect(self) -> None: return None
    async def disconnect(self) -> None: return None
    async def read_once(self, session_id: UUID, sequence: int) -> list[AcquisitionRecord]:
        frame: CanFrame | None = await self.bus.receive(self.timeout_ms)
        if frame is None:
            return []
        return [AcquisitionRecord(session_id=session_id, timestamp_ns=(frame.timestamp_ns or time_ns()), source_type=self.source_type, channel=f'can:0x{frame.arbitration_id:X}', raw=frame.data, sequence=sequence, metadata={'arbitration_id': frame.arbitration_id, 'dlc': frame.dlc, 'is_extended': frame.is_extended, 'is_fd': frame.is_fd})]

class UdsDidPollingSource(AcquisitionSource):
    source_type = AcquisitionSourceType.UDS_DID
    def __init__(self, client: UdsClient, dids: list[int], decoders: dict[int, Callable[[bytes], float]] | None = None):
        self.client = client
        self.dids = dids
        self.decoders = decoders or {}
    async def connect(self) -> None: return None
    async def disconnect(self) -> None: return None
    async def read_once(self, session_id: UUID, sequence: int) -> list[AcquisitionRecord]:
        out=[]
        for did in self.dids:
            try:
                payload = await self.client.read_data_by_identifier(did)
                decoder = self.decoders.get(did)
                value = float(decoder(payload)) if decoder else None
                out.append(AcquisitionRecord(session_id=session_id, timestamp_ns=time_ns(), source_type=self.source_type, channel=f'uds:0x{did:04X}', numeric_value=value, raw=payload, sequence=sequence, metadata={'did': did}))
            except Exception as exc:
                out.append(AcquisitionRecord(session_id=session_id, timestamp_ns=time_ns(), source_type=self.source_type, channel=f'uds:0x{did:04X}', numeric_value=None, raw=None, quality='INVALID', sequence=sequence, metadata={'did': did, 'error': str(exc)}))
        return out
