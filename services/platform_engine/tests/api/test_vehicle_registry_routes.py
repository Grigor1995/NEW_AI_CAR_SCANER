"""Contract tests for FastAPI registry endpoints; no physical vehicle required."""
import pytest
from fastapi import HTTPException

from api import vehicle_registry_routes as routes


def test_global_protocols_are_metadata_not_hardware_verification():
    payload = routes.protocols()
    assert payload["real_vehicle_verification"] == "not_claimed"
    assert len(payload["protocols"]) >= 20


def test_registry_endpoints_read_backend_seed_not_ui_lists():
    assert "Mercedes-Benz" in routes.global_makes("Mercedes")
    rows = routes.global_models(make="Mercedes-Benz", year=2006, q="", limit=100)
    assert any(x["model"] == "E-Class" for x in rows)
    curated = routes.global_fitments(make="Mercedes-Benz", model="E-Class", year=2006)
    assert any(x["chassis"] == "W211" for x in curated)


def test_global_compatibility_result_never_claims_confirmed_ecu():
    response = routes.compatibility(
        year=2006, make="Mercedes-Benz", market="EU",
        fuel="petrol", vehicle_class="passenger",
        detected_elm="A6",
    )
    assert response["detected"]["protocol_id"] == "iso15765_4_can11_500"
    assert response["detected"]["confirmed_ecu_communication"] is False


def test_generated_vehicle_image_is_centralized_on_server():
    image = routes.local_portrait(make="Mercedes-Benz", model="E-Class", chassis="W211")
    assert image.media_type == "image/png"
    assert image.headers["x-image-provenance"] == "project-generated"
    assert str(image.path).endswith("mercedes-benz_e-class_w211.png")


def test_vin_lookup_requires_explicit_post_body(monkeypatch):
    seen = []
    monkeypatch.setattr(routes, "nhtsa_decode_vin", lambda vin, year: seen.append((vin, year)) or {"source":"NHTSA"})
    response = routes.vin_lookup(routes.VinLookupRequest(
        vin="WDBUF56X06B123456", model_year=2006
    ))
    assert response["source"] == "NHTSA"
    assert seen == [("WDBUF56X06B123456", 2006)]


def test_photo_response_discloses_generated_fallback_and_licensing(monkeypatch):
    monkeypatch.setattr(routes, "commons_photo_candidate", lambda *_args: {
        "status": "no_licensed_candidate", "source": "Wikimedia Commons"
    })
    data = routes.photo("Mercedes-Benz", "E-Class", "W211")
    assert data["image_authority"] == "backend"
    assert "portrait?" in data["fallback_generated_portrait"]
    assert data["status"] == "no_licensed_candidate"


def test_remote_upstream_failure_returns_service_unavailable(monkeypatch):
    from vehicle.external_registry import RemoteRegistryUnavailable
    def offline():
        raise RemoteRegistryUnavailable("unavailable")
    monkeypatch.setattr(routes, "nhtsa_available_makes", offline)
    with pytest.raises(HTTPException) as exc:
        routes.vpic_makes()
    assert exc.value.status_code == 503


def test_profile_is_backend_owned_and_not_hardware_verified():
    response = routes.vehicle_profile(
        make="Mercedes-Benz", model="E-Class", year=2006, market="EU",
        engine="M272 E35 3.5", chassis="W211", fuel="petrol",
        vehicle_class="passenger", detected_elm=None,
    )
    assert response["status"] == "seeded_not_vin_verified"
    assert response["engine_found_in_curated_hints"]
    assert response["verified_ecu_protocol"] is False
    assert len(response["protocols"]["candidates"]) > 1


def test_unseeded_profile_returns_404_without_fabricated_engine_fitment():
    with pytest.raises(HTTPException) as exc:
        routes.vehicle_profile(
            make="Unknown", model="Imaginary", year=2021,
            market="unknown", chassis="", engine="", fuel="",
            vehicle_class="passenger", detected_elm=None,
        )
    assert exc.value.status_code == 404
