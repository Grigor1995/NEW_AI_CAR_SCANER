"""Generation/engine references shared by every native client.

A reference is not VIN fitment, engine-year availability or observed protocol.
"""
import json
from pathlib import Path
import sys


def project_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def reference_vehicles() -> list[dict]:
    root = project_root()
    data = json.loads((root / "data/vehicle_reference.json").read_text(encoding="utf-8"))
    manifest = root / "data/vehicle_images/manifest.json"
    images = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
    result = []
    for row in data["vehicles"]:
        row = dict(row)
        image = dict(images.get(row["id"], row["image"]))
        image["url"] = f"/api/v1/vehicle-reference/{row['id']}/image" if image.get("path") else None
        row["image"] = image
        result.append(row)
    return result


def selector_entries(**filters) -> list[dict]:
    rows = []
    for car in reference_vehicles():
        for engine in car["engines"]:
            for year in range(car["year_start"], car["year_end"]+1):
                row = {key: car[key] for key in ("make", "model", "chassis")}
                row.update(year=year, engine=engine["name"], engine_type=engine["type"], ecu=None,
                           fuel=[engine["type"]], source=car["source_url"], scope="generation-reference-not-vin-fitment",
                           image_url=car["image"]["url"], vehicle_reference_id=car["id"],
                           image_attribution={k: car["image"][k] for k in ("creator", "license", "license_url", "source_page") if car["image"].get(k)} or None,
                           fitment_verified=False, protocol_policy="auto_detect_on_vehicle")
                if all(value is None or row.get(key) == value for key, value in filters.items()):
                    rows.append(row)
    return rows


def compatibility(make: str, model: str, year: int, engine: str | None, market: str | None) -> dict:
    matches = [c for c in reference_vehicles() if c["make"].casefold() == make.casefold()
               and c["model"].casefold() == model.casefold() and c["year_start"] <= year <= c["year_end"]
               and (not engine or any(e["name"].casefold() == engine.casefold() for e in c["engines"]))]
    # Regulation provides candidates, never a verified ECU-specific mapping.
    can_required = market == "US" and year >= 2008
    candidates = ["can-11-500", "can-29-500", "can-11-250", "can-29-250"]
    if not can_required:
        candidates += ["iso9141-2", "kwp-5baud", "kwp-fast", "j1850-pwm", "j1850-vpw"]
    return {"references": matches, "protocol_id": "auto", "candidates": candidates,
            "observed_protocol": None, "status": "requires_adapter_detection", "market": market,
            "basis": "US model-year 2008+ OBD CAN requirement" if can_required else "generic OBD-II adapter candidates; market applicability unverified",
            "confirmed_fitment": False, "all_vehicles_supported": False,
            "next_steps": ["Initialize adapter", "Read 0100 supported PID mask", "Read ATDPN", "Read VIN and ECU identification"]}
