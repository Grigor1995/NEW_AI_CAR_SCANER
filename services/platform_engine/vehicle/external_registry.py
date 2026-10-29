"""Optional NHTSA VIN and Wikimedia Commons image lookups.

Public remote data is advisory and must never override a measured ECU/VIN
identification. Return provenance and attribution; never scrape Wikipedia
HTML or silently import unlicensed photographs into application bundles.
"""
from __future__ import annotations

from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
import json
import re
from typing import Any
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


class RemoteRegistryUnavailable(RuntimeError):
    pass


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain(html: str) -> str:
    parser = _PlainText()
    parser.feed(html)
    return unescape("".join(parser.parts)).strip()[:300]


def _get_json(url: str) -> dict[str, Any]:
    # URL is built ONLY by the functions below with fixed HTTPS domains.
    request = Request(url, headers={"User-Agent": "AI-Car-Scanner/0.6 (+vehicle metadata lookup)"})
    try:
        with urlopen(request, timeout=6.0) as result:
            payload = json.loads(result.read(1_000_000).decode("utf-8"))
    except (OSError, ValueError, TimeoutError) as exc:
        raise RemoteRegistryUnavailable("Remote vehicle metadata source unavailable") from exc
    if not isinstance(payload, dict):
        raise RemoteRegistryUnavailable("Unexpected remote vehicle metadata format")
    return payload


@lru_cache(maxsize=1)
def nhtsa_available_makes() -> dict[str, Any]:
    """NHTSA GetAllMakes: live optional supplemental list, US-oriented."""
    payload = _get_json(
        "https://vpic.nhtsa.dot.gov/api/vehicles/GetAllMakes?format=json"
    )
    values = payload.get("Results") or []
    if not isinstance(values, list):
        raise RemoteRegistryUnavailable("NHTSA makes response format changed")
    return {
        "source": "NHTSA vPIC / GetAllMakes",
        "market_scope": "US intended-sale/import market; not all world brands",
        "makes": sorted(set(
            str(row["Make_Name"]).strip()
            for row in values if isinstance(row, dict) and row.get("Make_Name")
        )),
        "requires_live_network": True,
    }


@lru_cache(maxsize=128)
def nhtsa_models_for_make(make: str, year: int | None = None) -> dict[str, Any]:
    """Optional live make/model discovery; NEVER assume engine/ECU specifics."""
    name = make.strip()
    if not (1 <= len(name) <= 80) or any(c in name for c in "<>\\\\\r\n"):
        raise ValueError("Invalid make")
    if year is not None and not (1996 <= year <= 2100):
        raise ValueError("vPIC model-year filtering requires >=1996")
    prefix = "https://vpic.nhtsa.dot.gov/api/vehicles/"
    if year is not None:
        url = (
            prefix + "GetModelsForMakeYear/make/" + quote(name, safe="")
            + "/modelyear/" + str(year) + "?format=json"
        )
    else:
        url = prefix + "GetModelsForMake/" + quote(name, safe="") + "?format=json"
    values = _get_json(url).get("Results") or []
    if not isinstance(values, list):
        raise RemoteRegistryUnavailable("NHTSA models response format changed")
    return {
        "source": "NHTSA vPIC / " + ("GetModelsForMakeYear" if year is not None else "GetModelsForMake"),
        "make": name,
        "year": year,
        "market_scope": "US intended-sale/import; exact engine and ECU require VIN/OEM identification",
        "model_names": sorted(set(
            str(row["Model_Name"]).strip() for row in values
            if isinstance(row, dict) and row.get("Model_Name")
        )),
        "engine_details": "not_provided",
        "requires_live_network": True,
    }


def nhtsa_decode_vin(vin: str, model_year: int | None = None) -> dict[str, Any]:
    """NHTSA vPIC VIN decoder; US-oriented coverage; not an ECU protocol oracle.

    Caller must supply a valid 17-character VIN; no VIN is logged.
    """
    vin = vin.strip().upper()
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        raise ValueError("VIN must contain exactly 17 valid VIN characters")
    params = {"format": "json"}
    if model_year is not None:
        if not 1980 <= model_year <= 2100:
            raise ValueError("Invalid VIN model year")
        params["modelyear"] = str(model_year)
    url = (
        "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/"
        + quote(vin, safe="") + "?" + urlencode(params)
    )
    payload = _get_json(url)
    rows = payload.get("Results") or []
    if not isinstance(rows, list) or not rows:
        raise RemoteRegistryUnavailable("NHTSA VIN decoder returned no records")
    row = rows[0]
    def field(key: str) -> str | None:
        value = row.get(key) if isinstance(row, dict) else None
        result = str(value).strip() if value is not None else ""
        return result or None
    return {
        "source": "NHTSA vPIC DecodeVinValuesExtended",
        "scope": "US intended-sale/import market; global VIN coverage incomplete",
        "vin_last4": vin[-4:],
        "make": field("Make"),
        "model": field("Model"),
        "model_year": field("ModelYear"),
        "engine_model": field("EngineModel"),
        "engine_cylinders": field("EngineCylinders"),
        "engine_displacement_l": field("DisplacementL"),
        "fuel_type": field("FuelTypePrimary"),
        "vehicle_type": field("VehicleType"),
        "error_code": field("ErrorCode"),
        "error_text": field("ErrorText"),
        "protocol_detected": None,
        "notice": "VIN decoding does not identify live CAN/UDS/OBD transport or validate installed engine.",
    }


def _permissive_license(name: str) -> bool:
    normalized = re.sub(r"[-_\s]+", " ", name.casefold()).strip()
    # Never accept NonCommercial / NoDerivatives licences.
    if re.search(r"\b(nc|nd|noncommercial|no derivatives)\b", normalized):
        return False
    return (
        normalized.startswith(("cc0", "public domain", "pd "))
        or bool(re.fullmatch(r"cc by(?: sa)?(?: [0-9.]+)?", normalized))
    )


@lru_cache(maxsize=160)
def commons_photo_candidate(make: str, model: str, chassis: str = "") -> dict[str, Any]:
    """Return one clearly UNVERIFIED real Wikimedia Commons photo candidate.

    Model/chassis labels and licensing are recorded; Commons search by filename
    is not a VIN/chassis proof. UI must show candidate status/attribution.
    """
    for piece in (make, model, chassis):
        if len(piece) > 80 or any(c in piece for c in "<>\\\r\n"):
            raise ValueError("Invalid vehicle name for image search")
    if not make.strip() or not model.strip():
        raise ValueError("make and model are required")
    needle = f"{make} {model} {chassis}".strip()
    params = {
        "action": "query", "generator": "search", "gsrsearch": needle,
        "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 900,
        "format": "json", "formatversion": 2,
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    payload = _get_json(url)
    pages = ((payload.get("query") or {}).get("pages") or [])
    if not isinstance(pages, list):
        return {"status": "no_licensed_candidate", "source": "Wikimedia Commons"}
    make_aliases = {make.casefold()}
    if make.casefold() == "volkswagen":
        make_aliases.add("vw")
    elif make.casefold() == "mercedes-benz":
        make_aliases.add("mercedes")
    elif make.casefold() == "chevrolet":
        make_aliases.add("chevy")
    for page in pages:
        title = str(page.get("title", ""))
        lower_title = title.casefold()
        # Preserve only actual image files; don't use SVG or remote HTML.
        if not lower_title.endswith((".jpg", ".jpeg", ".png")):
            continue
        if not any(alias in lower_title for alias in make_aliases):
            continue
        if chassis:
            if chassis.casefold() not in lower_title:
                continue
            basis = "make_and_chassis_filename"
        elif model.casefold() in lower_title:
            basis = "make_and_model_filename"
        else:
            continue
        info = (page.get("imageinfo") or [{}])[0]
        extra = info.get("extmetadata") or {}
        label = _plain(str((extra.get("LicenseShortName") or {}).get("value", "")))
        license_lc = label.casefold()
        if not _permissive_license(license_lc):
            continue
        thumb = info.get("thumburl") or info.get("url")
        description_page = info.get("descriptionurl")
        if (
            not isinstance(thumb, str) or not isinstance(description_page, str)
            or urlsplit(thumb).hostname != "upload.wikimedia.org"
            or urlsplit(description_page).hostname != "commons.wikimedia.org"
        ):
            continue
        author = _plain(str((extra.get("Artist") or {}).get("value", "")))
        return {
            "status": "candidate_unverified",
            "filename_match_basis": basis,
            "image_url": thumb,
            "file_page": description_page,
            "title": title,
            "author": author or "See file page",
            "license": label,
            "license_url": _plain(str((extra.get("LicenseUrl") or {}).get("value", ""))) or None,
            "source": "Wikimedia Commons",
            "notice": "Real photo, but exact chassis/trim/year has NOT been independently verified; attribution and license apply.",
        }
    return {"status": "no_licensed_candidate", "source": "Wikimedia Commons",
            "notice": "No adequately labelled, permissively licensed photograph was found."}
