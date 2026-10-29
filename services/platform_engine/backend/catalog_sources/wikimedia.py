"""Import licensed Commons page images with source/creator/license metadata."""
from html import unescape
import json
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ALLOWED_LICENSES = {"CC0", "Public domain", "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
                    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def fetch_json(host: str, **params) -> dict:
    url = f"https://{host}/w/api.php?" + urlencode(params | {"format": "json", "formatversion": 2})
    with urlopen(Request(url, headers={"User-Agent": "AI-Car-Scanner/0.6.0 (vehicle reference import)"}), timeout=20) as response:
        return json.loads(response.read(2 * 1024 * 1024))


def clean_text(value: str) -> str:
    return unescape(re.sub(r"<[^>]*>", "", value)).strip()


def image_metadata(title: str, get=fetch_json) -> dict:
    page = get("en.wikipedia.org", action="query", prop="pageimages", piprop="name", titles=title, redirects=1)
    pages = page.get("query", {}).get("pages", [])
    filename = next((p.get("pageimage") for p in pages if p.get("pageimage")), None)
    if not filename:
        raise ValueError("Article has no Commons page image")
    details = get("commons.wikimedia.org", action="query", prop="imageinfo", titles="File:"+filename,
                  iiprop="url|extmetadata", iiurlwidth=960)
    infos = [i for p in details.get("query", {}).get("pages", []) for i in p.get("imageinfo", [])]
    if not infos:
        raise ValueError("Image is not available from Wikimedia Commons")
    info = infos[0]
    ext = info.get("extmetadata", {})
    def text(name):
        return clean_text(ext.get(name, {}).get("value", ""))
    license_name = text("LicenseShortName")
    if license_name not in ALLOWED_LICENSES:
        raise ValueError(f"License is missing or outside the supported reuse list: {license_name}")
    url = info.get("thumburl") or info["url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "upload.wikimedia.org":
        raise ValueError("Unexpected Commons image host")
    return {"download_url": url, "original_url": info["url"], "source_page": info["descriptionurl"],
            "creator": text("Artist"), "credit": text("Credit"), "license": license_name,
            "license_url": text("LicenseUrl"), "file_title": filename,
            "kind": "wikimedia_commons", "article_title": title}


def fetch_image(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "upload.wikimedia.org":
        raise ValueError("Only HTTPS Commons image downloads are supported")
    with urlopen(Request(url, headers={"User-Agent": "AI-Car-Scanner/0.6.0"}), timeout=30) as response:
        if urlparse(response.geturl()).netloc != "upload.wikimedia.org":
            raise ValueError("Unexpected download redirect")
        data = response.read(MAX_IMAGE_BYTES+1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds import size limit")
    return data
