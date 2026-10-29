"""Shared Mode 01 scaling and native byte-transport bridge contract."""
from dataclasses import dataclass

from vehicle.obd.protocols.elm327 import ELM327Protocol, OBDProtocolError
from obd.protocols import initialization, detected_protocol


@dataclass(frozen=True)
class Pid:
    command: str
    key: str
    length: int
    unit: str
    offset: float = 0
    scale: float = 1


PIDS = (
    Pid("010C", "rpm", 2, "rpm", scale=0.25),
    Pid("010D", "speed_kmh", 1, "km/h"),
    Pid("0105", "coolant_c", 1, "°C", offset=-40),
    Pid("0104", "engine_load_percent", 1, "%", scale=100/255),
    Pid("010F", "intake_air_c", 1, "°C", offset=-40),
    Pid("0110", "maf_gps", 2, "g/s", scale=0.01),
    Pid("010B", "map_kpa", 1, "kPa"),
    Pid("0111", "throttle_percent", 1, "%", scale=100/255),
    Pid("0106", "short_fuel_trim_percent", 1, "%", offset=-100, scale=100/128),
    Pid("0107", "long_fuel_trim_percent", 1, "%", offset=-100, scale=100/128),
)


def polling_plan(protocol_id="auto") -> dict:
    return {"schema_version": 1, "protocol_id": protocol_id,
            "initialization": initialization(protocol_id) + ["0100"],
            "initialization_timeout_ms": 35000,
            "discovery": ["0100", "ATDPN"],
            "commands": ["0100", "ATDPN"] + [p.command for p in PIDS],
            "read_only": True, "requires_prompt_terminated_responses": True}


def supported_polling_plan(responses: dict[str, str]) -> dict:
    """Select implemented live PIDs from observed Mode 01 PID 00 bitmaps.

    All current live channels are in the first page (01..20). Combine complete
    responses from multiple ECUs; never infer support from a model or a value.
    """
    frames = {key.upper().replace(" ", ""): value for key, value in responses.items()}
    payloads = ELM327Protocol.payloads("0100", frames.get("0100", "NO DATA"))
    masks = [int.from_bytes(p[2:], "big") for p in payloads if p[:2] == b"\x41\x00" and len(p) == 6]
    if not masks:
        raise OBDProtocolError("A complete Mode 01 PID 00 capability reply is required")
    mask = 0
    for value in masks:
        mask |= value
    supported = [pid for pid in range(1, 33) if mask & (1 << (32-pid))]
    commands = [pid.command for pid in PIDS if int(pid.command[2:], 16) in supported]
    return {"schema_version": 2, "initialization": [], "discovery": [],
            "commands": commands, "supported_pids": supported,
            "unsupported_commands": [pid.command for pid in PIDS if pid.command not in commands],
            "capabilities_observed": True, "read_only": True,
            "requires_prompt_terminated_responses": True}


def decode_snapshot(responses: dict[str, str]) -> dict:
    normalized = {key.upper().replace(" ", ""): value for key, value in responses.items()}
    values, errors = {}, {}
    for pid in PIDS:
        try:
            data = ELM327Protocol.parse_pid(int(pid.command[2:], 16), normalized.get(pid.command, "NO DATA"))
            if len(data) != pid.length:
                raise OBDProtocolError(f"Expected {pid.length} bytes; received {len(data)}")
            values[pid.key] = int.from_bytes(data, "big") * pid.scale + pid.offset
        except (ValueError, OBDProtocolError) as error:
            values[pid.key] = None
            errors[pid.command] = str(error)
    protocol = None
    if "ATDPN" in normalized:
        try:
            protocol = detected_protocol(normalized["ATDPN"])
        except ValueError as error:
            errors["ATDPN"] = str(error)
    return {"protocol": protocol, "values": values, "units": {p.key: p.unit for p in PIDS}, "errors": errors,
            "source": "native_transport_bridge", "hardware_verified": False}
