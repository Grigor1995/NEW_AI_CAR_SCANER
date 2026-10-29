from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from vehicle.can.models import CanFrame
from vehicle.network.discovery import CanIdObservation, VehicleNetworkDiscoveryEngine


class VehicleNetworkDiscoveryService:
    """Session-scoped passive network discovery with replayable observations."""

    def __init__(self) -> None:
        self._observations: dict[str, list[CanIdObservation]] = defaultdict(list)
        self._engine = VehicleNetworkDiscoveryEngine()

    def ingest_frame(self, session_id: UUID, *, bus: str, frame: CanFrame) -> None:
        self._observations[str(session_id)].append(
            CanIdObservation(
                bus=bus,
                arbitration_id=frame.arbitration_id,
                timestamp_ns=frame.timestamp_ns or 0,
                dlc=frame.dlc,
                data_hex=frame.data.hex().upper(),
                extended=frame.is_extended,
                fd=frame.is_fd,
            )
        )

    def ingest_frames(self, session_id: UUID, *, bus: str, frames: list[CanFrame]) -> int:
        for frame in frames:
            self.ingest_frame(session_id, bus=bus, frame=frame)
        return len(frames)

    def analyze(self, session_id: UUID):
        return self._engine.analyze_observations(self._observations.get(str(session_id), []))

    def reset(self, session_id: UUID) -> None:
        self._observations.pop(str(session_id), None)

    def observation_count(self, session_id: UUID) -> int:
        return len(self._observations.get(str(session_id), []))
