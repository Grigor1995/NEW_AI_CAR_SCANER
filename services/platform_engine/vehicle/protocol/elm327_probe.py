"""Read-only ELM327 protocol identification — adapter transport injected by client.

The host that owns USB/Bluetooth/Wi-Fi establishes the physical link. The
backend owns the shared protocol classification and ECU response validation.
Never issue Mode 04, UDS 2E/31/34/36, security access or actuations.
"""
from __future__ import annotations

import re
from typing import Awaitable, Callable, Any

from vehicle.protocol.registry import read_elm_detected_protocol

AsyncCommand = Callable[[str], Awaitable[str]]


def is_obd_mode_01_supported_pids_reply(raw: str) -> bool:
    """A Mode 01 PID 00 reply starts with 41 00 after optional headers.

    Adapter echoes and SEARCHING are ignored. This is stronger than ATDPN,
    but not proof that every other service/ECU is compatible.
    """
    lines = re.split(r"[\r\n>]+", raw.upper())
    for line in lines:
        compact = re.sub(r"[^0-9A-F]", "", line)
        # Full ELM CAN headers like 7E8 06 41 00 xx... can precede 4100.
        # Four bytes form the PID-00 supported-PIDs bitmask. A partial
        # "41 00" header alone is not ECU communication evidence.
        if re.search(r"4100[0-9A-F]{8}", compact):
            return True
    return False


async def discover_elm_obd_protocol(command: AsyncCommand) -> dict[str, Any]:
    """Read-only *vehicle request* detection using an existing adapter link.

    ATSP0 selects adapter automatic protocol; it does not reprogram a vehicle.
    Mode 0100 queries supported standard OBD PIDs. ATDPN reads adapter mode.
    """
    commands: list[str] = []
    try:
        for message in ("ATSP0", "0100", "ATDPN"):
            result = await command(message)
            commands.append(message)
            if not isinstance(result, str):
                raise ValueError(f"Adapter reply for {message} was not text")
            if message == "0100":
                mode_reply = result
            if message == "ATDPN":
                dpn_reply = result
        observed = read_elm_detected_protocol(dpn_reply)
        ecu_replied = is_obd_mode_01_supported_pids_reply(mode_reply)
        return {
            **observed,
            "confirmed_ecu_communication": ecu_replied,
            "status": (
                "ecu_observed" if ecu_replied and observed["protocol_id"]
                else "adapter_only" if observed["protocol_id"]
                else "unrecognized"
            ),
            "commands": commands,
            "scope": "generic emissions Mode 01 PID 00 only",
            "supported_ecu_services": ["01-00"] if ecu_replied else [],
            "note": "No DTC clearing, actuator tests or manufacturer UDS requests performed.",
        }
    except Exception as exc:
        return {
            "status": "error", "protocol_id": None,
            "confirmed_ecu_communication": False,
            "commands": commands, "error_type": type(exc).__name__,
            "note": "Communication failed; protocol unknown. Do not assume compatibility.",
        }
