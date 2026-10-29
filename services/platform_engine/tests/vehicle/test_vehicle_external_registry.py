"""External data adapters tested with fixtures: no real HTTP request."""
import pytest

from vehicle import external_registry as ext


def test_vin_validation_before_remote_request(monkeypatch):
    monkeypatch.setattr(ext, "_get_json", lambda url: pytest.fail("unexpected network"))
    with pytest.raises(ValueError):
        ext.nhtsa_decode_vin("NOT A VALID VIN")


def test_nhtsa_engine_details_do_not_claim_obd_protocol(monkeypatch):
    def fake_api(url):
        assert "DecodeVinValuesExtended" in url
        return {"Results": [{
            "Make": "Mercedes-Benz", "Model": "E-Class",
            "ModelYear": "2006", "EngineModel": "M272",
            "FuelTypePrimary": "Gasoline", "DisplacementL": "3.5",
        }]}
    monkeypatch.setattr(ext, "_get_json", fake_api)
    record = ext.nhtsa_decode_vin("WDBUF56X06B123456")
    assert record["engine_model"] == "M272"
    assert record["vin_last4"] == "3456"
    assert record["protocol_detected"] is None
    assert "global" in record["scope"].lower()


@pytest.mark.parametrize("label,expected", [
    ("CC BY-SA 4.0", True),
    ("CC BY 3.0", True),
    ("CC0 1.0", True),
    ("Public Domain", True),
    ("CC BY-NC-SA 4.0", False),
    ("CC BY-ND 4.0", False),
    ("All Rights Reserved", False),
])
def test_commons_licensing_filter(label, expected):
    assert ext._permissive_license(label) is expected


def test_licensed_commons_photo_carries_attribution_and_is_unverified(monkeypatch):
    monkeypatch.setattr(ext, "_get_json", lambda url: {"query": {"pages": [{
        "title": "File:Mercedes-Benz E-Class W211 2006.jpg",
        "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/a/b/car.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Mercedes-Benz_E-Class_W211_2006.jpg",
            "extmetadata": {
                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                "Artist": {"value": "<b>Sample Author</b>"},
            },
        }],
    }]}})
    ext.commons_photo_candidate.cache_clear()
    photo = ext.commons_photo_candidate("Mercedes-Benz", "E-Class", "W211")
    assert photo["status"] == "candidate_unverified"
    assert photo["author"] == "Sample Author"
    assert photo["license"] == "CC BY-SA 4.0"
    assert photo["source"] == "Wikimedia Commons"


def test_bad_or_nonfree_credential_never_returns_photo(monkeypatch):
    monkeypatch.setattr(ext, "_get_json", lambda url: {"query": {"pages": [{
        "title": "File:Mercedes-Benz E-Class W211.jpg",
        "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/a/b/car.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:test.jpg",
            "extmetadata": {"LicenseShortName": {"value": "CC BY-NC 4.0"}},
        }],
    }]}})
    ext.commons_photo_candidate.cache_clear()
    assert ext.commons_photo_candidate("Mercedes-Benz", "E-Class", "W211")["status"] == "no_licensed_candidate"
