"""Single backend registry for the project global seed and curated engine fitments.

The NHTSA-derived make/model year ranges are broad, engine_families are hints;
the 22 curated chassis entries have engine labels but are NOT VIN-verified
individual vehicles. All clients must use this API as their authoritative
catalogue, preserving only a clearly labelled offline presentation fallback.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_PATH = ROOT / "data" / "vehicle_catalog.json"
FITMENT_PATH = ROOT / "data" / "vehicle_fitments.json"


@lru_cache(maxsize=1)
def global_catalog() -> dict[str, Any]:
    return json.loads(GLOBAL_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def curated_fitments() -> dict[str, Any]:
    return json.loads(FITMENT_PATH.read_text(encoding="utf-8"))


def makes(query: str = "") -> list[str]:
    needle = query.casefold().strip()
    return sorted({
        entry["make"] for entry in global_catalog()["makes"]
        if needle in entry["make"].casefold()
    })


def models(make: str, year: int | None = None, query: str = "", limit: int = 300) -> list[dict[str, Any]]:
    if not make.strip():
        return []
    result: list[dict[str, Any]] = []
    for brand in global_catalog()["makes"]:
        if brand["make"].casefold() != make.casefold():
            continue
        for row in brand["models"]:
            if query and query.casefold().strip() not in row["model"].casefold():
                continue
            ranges = row.get("year_ranges") or []
            if year is not None and not any(low <= year <= high for low, high in ranges):
                continue
            result.append({
                "make": brand["make"],
                "model": row["model"],
                "year_ranges": ranges,
                "vehicle_type": row.get("vehicle_type"),
                "engine_families": row.get("engine_families", []),
                "common_fuels": row.get("common_fuels", []),
                "engine_scope": row.get("engine_data_scope", "family-level"),
                "source": global_catalog().get("source", {}).get("name", "project-seed"),
                "disclaimer": "Model-family hints only; year-specific engine fitment requires VIN/market confirmation.",
            })
    return sorted(result, key=lambda row: row["model"])[:limit]


def fitments(make: str, model: str, year: int | None = None) -> list[dict[str, Any]]:
    answer: list[dict[str, Any]] = []
    for row in curated_fitments()["entries"]:
        if row["make"].casefold() != make.casefold() or row["model"].casefold() != model.casefold():
            continue
        years = row.get("years", [])
        if year is not None and year not in years:
            continue
        answer.append({
            "make": row["make"], "model": row["model"],
            "chassis": row["chassis"], "years": years if year is None else [year],
            "engines": row.get("engines", []),
            "source": "project-curated-fitment",
            "scope": "selector_hint_not_vin_verified",
            "disclaimer": "Chassis, engine and ECU choices vary by model year, VIN, engine market and option code.",
        })
    return answer


def registry_stats() -> dict[str, Any]:
    brands = global_catalog()["makes"]
    curated = curated_fitments()["entries"]
    return {
        "make_count": len(brands),
        "global_model_families": sum(len(make["models"]) for make in brands),
        "curated_chassis_entries": len(curated),
        "global_source": global_catalog().get("source", {}),
        "worldwide_exhaustive": False,
        "data_authority": "backend",
        "engines": "family-level globally; selected curated chassis hints, not VIN-level certainty",
    }


def vehicle_protocol_profile(
    *, make: str, model: str, year: int, market: str = "unknown",
    engine: str = "", chassis: str = "", fuel: str = "",
    vehicle_class: str = "passenger", detected_elm: str | None = None,
) -> dict[str, Any]:
    """One canonical response for ALL seeded make/model/year combinations.

    The year/market regulation hints are the same for any client. An engine
    label does not confirm a real engine, a physical ECU or a transport.
    """
    from urllib.parse import urlencode
    from vehicle.protocol.registry import assess_protocols

    if not make.strip() or not model.strip():
        raise ValueError("make and model are required")
    if not (1886 <= year <= 2100):
        raise ValueError("Year outside supported range")
    matching_models = [
        row for row in models(make, year=year, limit=500)
        if row["model"].casefold() == model.casefold()
    ]
    if not matching_models:
        return {
            "status": "not_in_seed_catalog",
            "make": make, "model": model, "year": year,
            "protocols": None,
            "engines": [],
            "notice": "Not in local seed. Query /vpic/models or VIN/OEM documentation; do not infer a protocol.",
        }

    representative = matching_models[0]
    entries = [
        row for row in fitments(make, model, year=year)
        if not chassis or row["chassis"].casefold() == chassis.casefold()
    ]
    selected_engine = engine.strip()
    listed_engines = [
        {"name": eng.get("name"), "ecus": eng.get("ecus", []),
         "scope": "curated_not_vin_verified"}
        for entry in entries for eng in entry["engines"]
    ]
    exact_engines = [
        e for e in listed_engines if e["name"].casefold() == selected_engine.casefold()
    ] if selected_engine else []
    matched_chassis = next(
        (entry["chassis"] for entry in entries if not chassis or entry["chassis"].casefold() == chassis.casefold()),
        chassis or None,
    )
    compatibility = assess_protocols(
        year=year, market=market, make=representative["make"],
        fuel=fuel, vehicle_class=vehicle_class, detected_elm=detected_elm,
    )
    portrait = (
        "/api/v1/vehicle-registry/portrait?"
        + urlencode({
            "make": representative["make"], "model": representative["model"],
            "chassis": matched_chassis or "",
        })
    )
    return {
        "status": "seeded_not_vin_verified",
        "make": representative["make"],
        "model": representative["model"],
        "year": year,
        "market": market,
        "chassis": matched_chassis,
        "requested_engine": selected_engine or None,
        "engine_found_in_curated_hints": bool(exact_engines),
        "engines": listed_engines,
        "engine_families": representative["engine_families"],
        "common_fuels": representative["common_fuels"],
        "vehicle_type": representative["vehicle_type"],
        "engine_scope": "curated_selector_hints" if entries else representative["engine_scope"],
        "protocols": compatibility,
        "image": {
            "source": "project-generated",
            "portrait_api_url": portrait,
            "real_photo_lookup_api_url": (
                "/api/v1/vehicle-registry/photo?"
                + urlencode({
                    "make": representative["make"], "model": representative["model"],
                    "chassis": matched_chassis or "",
                })
            ),
            "real_photo_match_status": "unverified_until_attributed_commons_response",
        },
        "sources": ["NHTSA-derived local model seed"]
        + (["project curated engine hints"] if entries else []),
        "verified_ecu_protocol": False,
        "notice": (
            "Catalog vehicle/engine/protocol information is advisory only; "
            "VIN/market/engine ECU/adapter handshake required for exact support."
        ),
    }
