from dataclasses import dataclass
import struct

MAGIC = b"AAV1"

@dataclass(frozen=True)
class VciPacket:
    channel: int
    payload: bytes

class CustomVciCodec:
    """Reference framing for the future custom Android VCI. This is not a vehicle protocol."""
    @staticmethod
    def encode(packet: VciPacket) -> bytes:
        if not 0 <= packet.channel <= 255: raise ValueError("channel out of range")
        if len(packet.payload) > 65535: raise ValueError("payload too large")
        return MAGIC + bytes([packet.channel]) + struct.pack(">H", len(packet.payload)) + packet.payload
    @staticmethod
    def decode(frame: bytes) -> VciPacket:
        if len(frame) < 7 or frame[:4] != MAGIC: raise ValueError("invalid VCI frame")
        channel = frame[4]; length = struct.unpack(">H", frame[5:7])[0]
        if len(frame) != 7 + length: raise ValueError("invalid VCI length")
        return VciPacket(channel, frame[7:])
