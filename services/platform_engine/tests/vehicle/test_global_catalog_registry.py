"""Shared vehicle models and engines come from the BACKEND registry only."""
from vehicle.catalog_registry import makes, models, fitments, registry_stats


def test_global_make_model_catalog_is_broader_than_mobile_seed():
    meta = registry_stats()
    assert meta["make_count"] >= 30
    assert meta["global_model_families"] > 100
    assert meta["curated_chassis_entries"] >= 22
    assert meta["worldwide_exhaustive"] is False
    assert meta["data_authority"] == "backend"


def test_makes_case_insensitive_lookup_is_sorted():
    assert "Mercedes-Benz" in makes("mercedes")
    assert all(x in makes() for x in ("BMW", "Toyota", "Kia"))


def test_models_require_existing_make_and_return_engine_family_scope():
    assert models("not-a-manufacturer") == []
    values = models("Mercedes-Benz", 2006)
    example = next(x for x in values if x["model"] == "E-Class")
    assert example["engine_scope"] == "family-level"
    assert example["engine_families"]
    assert "VIN" in example["disclaimer"]


def test_w211_chassis_engine_fitment_is_curated_not_vin_verified():
    row = fitments("Mercedes-Benz", "E-Class", 2006)
    w211 = next(x for x in row if x["chassis"] == "W211")
    assert "M272 E35 3.5" in [x["name"] for x in w211["engines"]]
    assert w211["scope"] == "selector_hint_not_vin_verified"


def test_fitments_are_filtered_by_year():
    assert not any(x["chassis"] == "W211" for x in fitments("Mercedes-Benz", "E-Class", 2026))


def test_vehicle_profile_resolves_2006_w211_m272_without_inventing_protocol():
    from vehicle.catalog_registry import vehicle_protocol_profile
    result = vehicle_protocol_profile(
        make="Mercedes-Benz", model="E-Class", chassis="W211",
        year=2006, engine="M272 E35 3.5", market="EU", fuel="petrol",
    )
    assert result["status"] == "seeded_not_vin_verified"
    assert result["chassis"] == "W211"
    assert result["engine_found_in_curated_hints"]
    assert result["verified_ecu_protocol"] is False
    ids = {c["id"] for c in result["protocols"]["candidates"]}
    assert {"iso14230_4_fast", "iso15765_4_can11_500"} <= ids
    assert "portrait?" in result["image"]["portrait_api_url"]


def test_vehicle_profile_is_available_for_all_global_seed_model_families():
    from vehicle.catalog_registry import global_catalog, vehicle_protocol_profile
    for brand in global_catalog()["makes"]:
        for family in brand["models"]:
            start, end = family["year_ranges"][0]
            year = (int(start) + int(end)) // 2
            result = vehicle_protocol_profile(
                make=brand["make"], model=family["model"],
                year=year, market="unknown",
            )
            assert result["status"] == "seeded_not_vin_verified"
            assert result["protocols"]["confidence"] == "unverified_hint"
            assert result["verified_ecu_protocol"] is False


def test_unseeded_model_fails_closed():
    from vehicle.catalog_registry import vehicle_protocol_profile
    item = vehicle_protocol_profile(
        make="Nonexistent Make", model="Unknown", year=2020
    )
    assert item["status"] == "not_in_seed_catalog"
    assert item["protocols"] is None
