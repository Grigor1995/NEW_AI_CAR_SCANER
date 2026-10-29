"""Refresh the native offline selection snapshot from backend generation references."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from obd.catalog import selector_entries


def build_snapshot(payload):
    result = dict(payload)
    rows = [r for r in payload["vehicles"] if r.get("scope") != "generation-reference-not-vin-fitment"]
    def key(row):
        return tuple(str(row.get(k, "")).casefold() for k in ("make", "model", "chassis", "year", "engine"))
    keys = {key(row) for row in rows}
    for row in selector_entries():
        if key(row) not in keys:
            rows.append({k: row.get(k) for k in ("make", "model", "chassis", "year", "engine", "ecu", "source", "scope")} | {"fuel": row["fuel"][0].title()})
            keys.add(key(row))
    result["vehicles"] = rows
    result["description"] = "Backend-generated selection snapshot shared by native clients. Online backend entries take precedence. Generation/engine ranges are guidance, not verified VIN fitment."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "shared/vehicle_catalog.json"
    current = path.read_text(encoding="utf-8")
    expected = json.dumps(build_snapshot(json.loads(current)), ensure_ascii=False, indent=2) + "\n"
    paths = [path, ROOT / "apps/mobile-android/app/src/main/assets/vehicle_catalog.json", ROOT / "apps/mobile-ios/AICarScanner/VehicleCatalog/vehicle_catalog.json"]
    if args.check:
        return 0 if all(p.is_file() and p.read_text(encoding="utf-8") == expected for p in paths) else 1
    for target in paths:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
