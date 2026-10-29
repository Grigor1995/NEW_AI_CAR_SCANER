"""VIN-first, read-only discovery shared by local adapters and native bridges."""
from __future__ import annotations
import asyncio
import re
from vehicle.obd.protocols.elm327 import ELM327Protocol
from vehicle.external_registry import nhtsa_decode_vin

PLAN = {"commands": ["0902", "ATH1", "0100", "ATDPN"], "restore": ["ATH0"]}


def vin_from_response(raw: str) -> str | None:
    try:
        for payload in ELM327Protocol.payloads("0902", raw):
            if not payload.startswith(b"\x49\x02"):
                continue
            match = re.search(r"[A-HJ-NPR-Z0-9]{17}", payload[3:].decode("ascii", errors="ignore"))
            if match:
                return match.group()
    except ValueError:
        pass
    return None


def responding_modules(raw: str) -> list[dict]:
    modules = {}
    for line in re.split(r"[\r\n>]+", raw.upper()):
        match = re.match(r"^\s*([0-9A-F]{3}|[0-9A-F]{8})\s+", line)
        compact = "".join(line.split())
        address = match[1] if match else None
        if address is None and re.fullmatch(r"[0-9A-F]+", compact):
            if len(compact) > 10 and compact.startswith(("18DA", "18DB")):
                address = compact[:8]
            elif len(compact) >= 5 and len(compact) % 2:
                address = compact[:3]
        if address is None:
            continue
        try:
            payloads = ELM327Protocol.payloads("0100", line)
        except ValueError:
            continue
        if any(p.startswith(b"\x41\x00") and len(p) >= 6 for p in payloads):
            modules[address] = {"address": address, "name": "OBD ECU", "services": ["01-00"], "observed": True}
    if not modules:
        try:
            payloads = ELM327Protocol.payloads("0100", raw)
            if any(p.startswith(b"\x41\x00") and len(p) >= 6 for p in payloads):
                modules[None] = {"address": None, "name": "OBD ECU", "services": ["01-00"], "observed": True}
        except ValueError:
            pass
    return list(modules.values())


async def identify(responses: dict[str, str], *, simulated: bool = False) -> dict:
    vin = vin_from_response(responses.get("0902", ""))
    vehicle, lookup_status = None, "vin_unavailable"
    if vin and not simulated:
        try:
            vehicle = await asyncio.to_thread(nhtsa_decode_vin, vin)
            lookup_status = "identified" if vehicle.get("make") and vehicle.get("model") and vehicle.get("error_code") == "0" else "incomplete"
        except Exception:
            lookup_status = "lookup_unavailable"
    elif simulated:
        lookup_status = "simulated"
    modules = responding_modules(responses.get("0100", ""))
    protocol = None
    if modules and not simulated:
        from obd.protocols import detected_protocol
        try:
            protocol = detected_protocol(responses.get("ATDPN", ""))
        except ValueError:
            pass  # An adapter label alone is not proof of a negotiated ECU link.
    return {"vin": vin, "vehicle": vehicle, "identification_status": lookup_status,
            "modules": modules, "protocol": protocol, "simulated": simulated,
            "scope": "generic_obd_responders_only"}


async def collect(command) -> dict[str, str]:
    responses = {}
    try:
        for step in PLAN["commands"]:
            responses[step] = await command(step)
    finally:
        # Restore even when a bridge request times out or fails midway.
        for step in PLAN["restore"]:
            await command(step)
    return responses
