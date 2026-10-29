"""Enrich backend vehicle references with attributed Commons images.

Run from finalbuild: python scripts/import_wikimedia_vehicles.py --limit 50
Requires network access to Wikipedia/Commons and Pillow. API startup is offline.
"""
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from catalog_sources.wikimedia import image_metadata, fetch_image  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--make")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 500:
        parser.error("limit must be between 1 and 500")
    from PIL import Image
    cars = json.loads((ROOT / "data/vehicle_reference.json").read_text(encoding="utf-8"))["vehicles"]
    directory = ROOT / "data/vehicle_images"
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    failures = []
    selected = [c for c in cars if not args.make or c["make"].casefold() == args.make.casefold()][:args.limit]
    for car in selected:
        if car["id"] in manifest and not args.force:
            continue
        try:
            metadata = image_metadata(car["wikipedia_title"])
            data = fetch_image(metadata["download_url"])
            with Image.open(BytesIO(data)) as photo:
                if photo.format not in {"JPEG", "PNG", "WEBP"} or photo.width * photo.height > 40_000_000:
                    raise ValueError("Unsupported or oversized raster photo")
                photo.thumbnail((960, 640))
                converted = BytesIO()
                photo.convert("RGB").save(converted, format="WEBP", quality=86)
            content = converted.getvalue()
            image_path = directory / (car["id"]+".webp")
            image_temp = image_path.with_suffix(".webp.tmp")
            image_temp.write_bytes(content)
            os.replace(image_temp, image_path)
            metadata.update(path=str(image_path.relative_to(ROOT)), sha256=sha256(content).hexdigest(),
                            retrieved_at=datetime.now(timezone.utc).isoformat())
            manifest[car["id"]] = metadata
            temporary = manifest_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
            os.replace(temporary, manifest_path)
            print(f"IMPORTED {car['id']} — {metadata['license']}", flush=True)
        except Exception as error:
            failures.append({"id": car["id"], "error": str(error)})
            print(f"FAILED {car['id']}: {error}", file=sys.stderr, flush=True)
    print(json.dumps({"selected": len(selected), "available_images": len(manifest), "failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
