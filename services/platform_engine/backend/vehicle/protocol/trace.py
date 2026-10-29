from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class ProtocolTraceRecorder:
    session_id: object
    events: list = field(default_factory=list)
    def record(self,event,**data): self.events.append({"timestamp":datetime.now(timezone.utc).isoformat(),"event":event,**data})
class TracedCanBus:
    def __init__(self,bus,trace): self.bus=bus; self.trace=trace
    async def send(self,frame):
        self.trace.record("CAN_TX",arbitration_id=frame.arbitration_id,data=frame.data.hex())
        return await self.bus.send(frame)
    async def receive(self,timeout_ms=1000):
        frame=await self.bus.receive(timeout_ms)
        if frame: self.trace.record("CAN_RX",arbitration_id=frame.arbitration_id,data=frame.data.hex())
        return frame
