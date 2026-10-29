from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from obd.catalog import reference_vehicles, compatibility, project_root

router = APIRouter(prefix="/api/v1/vehicle-reference", tags=["vehicle-reference"])


@router.get("")
def list_reference(make: str | None = None, model: str | None = None):
    cars = [c for c in reference_vehicles() if (not make or c["make"].casefold() == make.casefold())
            and (not model or c["model"].casefold() == model.casefold())]
    return {"vehicles": cars, "scope": "generation-reference-not-vin-fitment",
            "notice": "Engine availability varies by year and market. Verify VIN/ECU; protocol is detected on the adapter."}


@router.get("/compatibility")
def profile(make: str, model: str, year: int = Query(ge=1886, le=2100), engine: str | None = None, market: str | None = None):
    return compatibility(make, model, year, engine, market.upper() if market else None)


@router.get("/{reference_id}/image")
def image(reference_id: str):
    car = next((c for c in reference_vehicles() if c["id"] == reference_id), None)
    if not car or not car["image"].get("path"):
        raise HTTPException(404, "Vehicle image has not been imported")
    root = project_root().resolve()
    path = (root / car["image"]["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() not in {".png", ".webp", ".jpg", ".jpeg"}:
        raise HTTPException(404, "Vehicle image is unavailable")
    credit = car["image"]
    headers = {}
    if credit.get("kind") == "wikimedia_commons":
        headers = {"X-Image-Credit": quote(credit.get("creator", "")),
                   "X-Image-License": credit.get("license", ""),
                   "X-Image-Source": quote(credit.get("source_page", ""), safe=":/?=&%")}
    return FileResponse(path, headers=headers)


@router.get("/image")
def selected_image(make: str, model: str, chassis: str):
    car = next((c for c in reference_vehicles() if c["make"].casefold() == make.casefold()
                and c["model"].casefold() == model.casefold() and c["chassis"].casefold() == chassis.casefold()), None)
    if car is None:
        raise HTTPException(404, "No matching vehicle reference")
    return image(car["id"])
