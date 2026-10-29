"""Backend-only vehicle registry endpoints shared by Desktop/Android/iOS."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from urllib.parse import urlencode
import re

from vehicle.catalog_registry import makes, models, fitments, registry_stats, vehicle_protocol_profile
from vehicle.protocol.registry import all_protocols, assess_protocols, read_elm_detected_protocol
from vehicle.external_registry import (
    RemoteRegistryUnavailable, commons_photo_candidate, nhtsa_decode_vin,
    nhtsa_available_makes, nhtsa_models_for_make,
)

router = APIRouter(prefix="/api/v1/vehicle-registry", tags=["vehicle-registry"])
_ASSETS = Path(__file__).resolve().parents[2] / "assets"


class VinLookupRequest(BaseModel):
    # POST body avoids raw VINs in routine HTTP GET access-log query strings.
    vin: str = Field(..., min_length=17, max_length=17)
    model_year: int | None = Field(None, ge=1980, le=2100)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


@router.get("/stats")
def stats():
    return registry_stats()


@router.get("/makes", response_model=list[str])
def global_makes(q: str = Query("", max_length=80)):
    return makes(q)


@router.get("/models")
def global_models(
    make: str = Query(..., min_length=1, max_length=80),
    year: int | None = Query(None, ge=1886, le=2100),
    q: str = Query("", max_length=80),
    limit: int = Query(200, ge=1, le=500),
):
    return models(make, year=year, query=q, limit=limit)


@router.get("/fitments")
def global_fitments(
    make: str = Query(..., min_length=1, max_length=80),
    model: str = Query(..., min_length=1, max_length=80),
    year: int | None = Query(None, ge=1886, le=2100),
):
    return fitments(make, model, year)


@router.get("/profile")
def vehicle_profile(
    make: str = Query(..., min_length=1, max_length=80),
    model: str = Query(..., min_length=1, max_length=80),
    year: int = Query(..., ge=1886, le=2100),
    market: str = Query("unknown", max_length=24),
    chassis: str = Query("", max_length=40),
    engine: str = Query("", max_length=100),
    fuel: str = Query("", max_length=64),
    vehicle_class: str = Query("passenger", max_length=40),
    detected_elm: str | None = Query(None, max_length=32),
):
    """Backend source of truth for selected vehicle/engine and protocol hints."""
    profile = vehicle_protocol_profile(
        make=make, model=model, year=year, market=market,
        engine=engine, chassis=chassis, fuel=fuel,
        vehicle_class=vehicle_class, detected_elm=detected_elm,
    )
    if profile["status"] == "not_in_seed_catalog":
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Vehicle not in local seed, use vPIC online lookup or VIN data",
                "vpic_models": "/api/v1/vehicle-registry/vpic/models",
                "support": "not_known",
            },
        )
    return profile


@router.get("/vpic/makes")
def vpic_makes():
    try:
        return nhtsa_available_makes()
    except RemoteRegistryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/vpic/models")
def vpic_models(
    make: str = Query(..., min_length=1, max_length=80),
    year: int | None = Query(None, ge=1996, le=2100),
):
    try:
        return nhtsa_models_for_make(make, year)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RemoteRegistryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/protocols")
def protocols():
    return {"protocols": all_protocols(), "real_vehicle_verification": "not_claimed"}


@router.get("/compatibility")
def compatibility(
    year: int = Query(..., ge=1886, le=2100),
    market: str = Query("unknown", max_length=24),
    make: str = Query("", max_length=80),
    fuel: str = Query("", max_length=64),
    vehicle_class: str = Query("passenger", max_length=40),
    detected_elm: str | None = Query(None, max_length=32),
):
    return assess_protocols(
        year=year, market=market, make=make,
        fuel=fuel, vehicle_class=vehicle_class,
        detected_elm=detected_elm,
    )


@router.get("/detected-elm")
def detected_elm(raw: str = Query(..., min_length=1, max_length=32)):
    return read_elm_detected_protocol(raw)


@router.post("/vin")
def vin_lookup(request: VinLookupRequest):
    # vPIC receives the VIN over HTTPS; disclose this before enabling lookup.
    try:
        return nhtsa_decode_vin(request.vin, request.model_year)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RemoteRegistryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/portrait")
def local_portrait(
    make: str = Query(..., min_length=1, max_length=80),
    model: str = Query(..., min_length=1, max_length=80),
    chassis: str = Query("", max_length=40),
):
    # No arbitrary paths can be supplied; generated assets are served read-only
    # from backend assets, rather than 3 different client bundles.
    name = "_".join((_slug(make), _slug(model), _slug(chassis))) + ".png"
    path = _ASSETS / "vehicle_models" / name
    if not path.is_file():
        path = _ASSETS / "AI-Car-Scanner-mobile.png"
    if not path.is_file():
        raise HTTPException(404, "Portrait asset unavailable")
    return FileResponse(
        path, media_type="image/png",
        headers={"X-Image-Provenance": "project-generated", "Cache-Control": "public, max-age=86400"},
    )


@router.get("/photo")
def photo(
    make: str = Query(..., min_length=1, max_length=80),
    model: str = Query(..., min_length=1, max_length=80),
    chassis: str = Query("", max_length=40),
):
    try:
        candidate = commons_photo_candidate(make, model, chassis)
        candidate["fallback_generated_portrait"] = (
            "/api/v1/vehicle-registry/portrait?"
            + urlencode({"make": make, "model": model, "chassis": chassis})
        )
        candidate["image_authority"] = "backend"
        return candidate
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RemoteRegistryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
