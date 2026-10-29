"""One OBD contract for local adapters and native transport-only bridges."""
from time import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from obd.protocols import protocol_catalog, detected_protocol
from obd.decoding import polling_plan, supported_polling_plan, decode_snapshot

router = APIRouter(prefix="/api/v1/obd", tags=["OBD"])


class RawSnapshot(BaseModel):
    responses: dict[str, str] = Field(max_length=32)
    session_id: str | None = Field(default=None, max_length=64)

    @field_validator("responses")
    @classmethod
    def bounded_frames(cls, value):
        if any(len(k) > 16 or len(v) > 8192 for k, v in value.items()):
            raise ValueError("Response keys/frames exceed bridge limits")
        return value


@router.get("/protocols")
def protocols():
    return protocol_catalog()


@router.get("/plan")
def plan(protocol_id: str = "auto"):
    try:
        return polling_plan(protocol_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post("/plan")
def observed_plan(request: RawSnapshot):
    try:
        return supported_polling_plan(request.responses)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post("/decode")
def decode(request: RawSnapshot):
    result = decode_snapshot(request.responses)
    if request.session_id is not None:
        from api.state import sessions
        from api.telemetry_routes import service
        from telemetry.models import TelemetrySample
        if request.session_id not in sessions:
            raise HTTPException(404, "Session not found")
        sid = sessions[request.session_id].session_id
        if any(s.source in {"SIMULATOR", "OBD_ACQUISITION"} for s in service.samples(sid)):
            raise HTTPException(409, "Create a new session before adding real measurements to simulator data")
        names = {"coolant_c": "coolant_temp", "speed_kmh": "vehicle_speed", "maf_gps": "maf", "map_kpa": "map",
                 "throttle_percent": "throttle", "short_fuel_trim_percent": "stft", "long_fuel_trim_percent": "ltft"}
        samples = [TelemetrySample(session_id=sid, timestamp_ms=int(time()*1000), pid=names.get(key, key),
                   value=value, unit=result["units"][key], source="NATIVE_OBD_BRIDGE",
                   metadata={"hardware_verified": False, "protocol": result["protocol"]})
                   for key, value in result["values"].items() if value is not None]
        from api.acquisition_routes import service as acquisition
        try:
            acquisition.append_bridge(sid, result)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        result["accepted_samples"] = service.append(samples)
    return result


@router.get("/detected-protocol")
def detected(raw: str):
    try:
        return detected_protocol(raw)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/discovery/plan")
def discovery_plan():
    from vehicle.diagnostic_discovery import PLAN
    return PLAN


@router.post("/discovery/decode")
async def discovery_decode(request: RawSnapshot):
    from vehicle.diagnostic_discovery import identify
    return await identify(request.responses)
