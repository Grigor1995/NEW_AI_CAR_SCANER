from __future__ import annotations
from dataclasses import dataclass
from vehicle.isotp.stack import IsoTpStack

class UdsError(Exception):
    def __init__(self, message: str, *, service_id: int | None = None, nrc: int | None = None):
        super().__init__(message); self.service_id = service_id; self.nrc = nrc

@dataclass(frozen=True)
class UdsResponse:
    service_id: int
    payload: bytes

class UdsClient:
    """Read/diagnostic UDS client. Write/programming services are intentionally absent in Phase 3."""
    def __init__(self, isotp: IsoTpStack): self.isotp = isotp

    async def request(self, service_id: int, payload: bytes = b"") -> UdsResponse:
        await self.isotp.send(bytes([service_id]) + payload)
        response = await self.isotp.receive()
        if not response: raise UdsError("empty UDS response", service_id=service_id)
        if response[0] == 0x7F:
            if len(response) < 3: raise UdsError("malformed negative response", service_id=service_id)
            raise UdsError(f"UDS negative response NRC=0x{response[2]:02X}", service_id=response[1], nrc=response[2])
        if response[0] != ((service_id + 0x40) & 0xFF):
            raise UdsError("unexpected positive response", service_id=service_id)
        return UdsResponse(response[0], response[1:])

    async def diagnostic_session_control(self, session_type: int) -> bytes:
        return (await self.request(0x10, bytes([session_type]))).payload


    async def read_data_by_identifier(self, did: int) -> bytes:
        if not 0 <= did <= 0xFFFF: raise ValueError("DID must fit uint16")
        return (await self.request(0x22, did.to_bytes(2, "big"))).payload

    async def read_dtc_information(self, subfunction: int = 0x02) -> bytes:
        return (await self.request(0x19, bytes([subfunction]))).payload
