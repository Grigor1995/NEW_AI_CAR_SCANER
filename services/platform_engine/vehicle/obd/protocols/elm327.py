from __future__ import annotations
import re
from dataclasses import dataclass

class OBDProtocolError(ValueError):
    pass

@dataclass(frozen=True)
class OBDResponse:
    command: str
    raw: str
    payload: bytes

class ELM327Protocol:
    """Transport-agnostic ELM327 command builder/parser for generic OBD-II."""

    @staticmethod
    def normalize(raw: str | bytes) -> str:
        if isinstance(raw, bytes):
            raw = raw.decode("ascii", errors="ignore")
        return raw.replace("\r", " ").replace("\n", " ").replace(">", " ").strip()

    @classmethod
    def parse_hex_payload(cls, command: str, raw: str | bytes) -> OBDResponse:
        text = cls.normalize(raw).upper()
        payloads = cls.payloads(command, raw)
        return OBDResponse(command=command.upper().replace(" ", ""), raw=text, payload=payloads[0])

    @classmethod
    def payloads(cls, command: str, raw: str | bytes) -> list[bytes]:
        """Parse header-off ELM replies and CAN single/segmented frames per ECU.

        No search through unrelated bytes or fallback to the last two bytes:
        malformed/wrong-service responses must not become plausible measurements.
        """
        if isinstance(raw, bytes):
            raw = raw.decode("ascii", errors="strict")
        text = raw.upper().replace(">", "")
        if any(error in text for error in ("NO DATA", "UNABLE TO CONNECT", "ERROR", "STOPPED", "BUS ERROR", "CAN ERROR", "BUFFER FULL", "?")):
            raise OBDProtocolError(cls.normalize(text))
        text = re.sub(r"SEARCHING\.*|BUS INIT[:. ]*(?:OK)?", "", text)
        command = command.upper().replace(" ", "")
        completed, segmented = [], {}
        formatted = bytearray()
        for line in re.split(r"[\r\n]+", text):
            line = line.strip()
            if not line or line.replace(" ", "") in (command, "OK"):
                continue
            # Adapter's numbered, already reassembled ISO-TP display.
            if re.match(r"^[0-9A-F]+:", line):
                value = line.partition(":")[2].replace(" ", "")
                if not re.fullmatch(r"(?:[0-9A-F]{2})+", value):
                    raise OBDProtocolError("Malformed numbered ELM payload")
                formatted.extend(bytes.fromhex(value))
                continue
            tokens = line.split()
            ecu = None
            if len(tokens) > 1 and len(tokens[0]) in (3, 8):
                ecu, tokens = tokens[0], tokens[1:]
            compact = "".join(tokens)
            if ecu is None and len(tokens) == 1:
                if len(compact) >= 5 and len(compact) % 2:
                    ecu, compact = compact[:3], compact[3:]
                elif len(compact) > 10 and compact.startswith(("18DA", "18DB")):
                    ecu, compact = compact[:8], compact[8:]
            if not re.fullmatch(r"(?:[0-9A-F]{2})+", compact):
                # ELM's displayed total-length line for formatted VIN responses.
                if re.fullmatch(r"[0-9A-F]{3}", compact):
                    continue
                raise OBDProtocolError(f"Malformed hexadecimal reply: {line}")
            data = bytes.fromhex(compact)
            if ecu is None:
                if data.hex().upper().startswith(command):
                    data = data[len(command)//2:]
                if data:
                    completed.append(data)
                continue
            frame = data[0] >> 4
            if frame == 0:
                size = data[0] & 15
                if not size or size > len(data)-1:
                    raise OBDProtocolError("Truncated CAN single frame")
                completed.append(data[1:1+size])
            elif frame == 1 and len(data) >= 2:
                size = ((data[0] & 15) << 8) | data[1]
                segmented[ecu] = [size, bytearray(data[2:]), 1]
            elif frame == 2 and ecu in segmented:
                state = segmented[ecu]
                if data[0] & 15 != state[2]:
                    raise OBDProtocolError("ISO-TP sequence mismatch")
                state[1].extend(data[1:])
                state[2] = (state[2]+1) & 15
            else:
                raise OBDProtocolError("Unsupported or out-of-order CAN framing")
        for size, data, _sequence in segmented.values():
            if len(data) < size:
                raise OBDProtocolError("Incomplete ISO-TP response")
            completed.append(bytes(data[:size]))
        if formatted:
            completed.append(bytes(formatted))
        if not completed:
            raise OBDProtocolError("No hexadecimal payload")
        return completed

    @classmethod
    def parse_pid(cls, pid: int, raw: str | bytes) -> bytes:
        expected = bytes((0x41, pid))
        for payload in cls.payloads(f"01{pid:02X}", raw):
            if payload.startswith(expected):
                return payload[2:]
        raise OBDProtocolError(f"PID 01{pid:02X} not present")

    @staticmethod
    def rpm(data: bytes) -> float:
        if len(data) < 2: raise OBDProtocolError("RPM requires 2 data bytes")
        return ((data[0] << 8) | data[1]) / 4.0

    @staticmethod
    def coolant_c(data: bytes) -> float:
        if not data: raise OBDProtocolError("Coolant requires 1 data byte")
        return data[0] - 40.0

    @staticmethod
    def speed_kmh(data: bytes) -> float:
        if not data: raise OBDProtocolError("Speed requires 1 data byte")
        return float(data[0])

    @staticmethod
    def throttle_percent(data: bytes) -> float:
        if not data: raise OBDProtocolError("Throttle requires 1 data byte")
        return data[0] * 100.0 / 255.0

    @staticmethod
    def dtc_codes(payload: bytes) -> list[str]:
        # Mode 03 payload is pairs of bytes; first service/header bytes are skipped if present.
        if len(payload) >= 2 and payload[0] in (0x43, 0x47, 0x4A):
            payload = payload[1:]
        result=[]
        for i in range(0, len(payload)-1, 2):
            a,b=payload[i],payload[i+1]
            if a == 0 and b == 0: continue
            chars="PCBU"
            code=chars[(a >> 6) & 0x03] + f"{a & 0x3F:02X}{b:02X}"
            result.append(code)
        return result
