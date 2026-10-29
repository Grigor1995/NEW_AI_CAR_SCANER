"""Offline contract tests — no hardware, cloud APIs, or CI needed."""
import pytest

from vehicle.protocol.registry import (
    PROTOCOLS, all_protocols, read_elm_detected_protocol, assess_protocols
)


def test_transport_catalog_covers_all_elm_obd_choices_without_claiming_hardware():
    entries = all_protocols()
    assert len(entries) >= 20
    assert len({x["id"] for x in entries}) == len(entries)
    assert {p.elm_code for p in PROTOCOLS if p.elm_code} >= set("123456789A")
    assert all(x["support"] != "hardware_verified" for x in entries)
    assert next(x for x in entries if x["id"] == "uds_on_doip")["elm_code"] is None


@pytest.mark.parametrize("raw, expected, auto", [
    ("A6", "iso15765_4_can11_500", True),
    ("6", "iso15765_4_can11_500", False),
    ("A3", "iso9141_2", True),
    ("A5", "iso14230_4_fast", True),
    ("AA", "j1939_250", True),
])
def test_parse_elm_atdpn_readback(raw, expected, auto):
    result = read_elm_detected_protocol(raw)
    assert result["protocol_id"] == expected
    assert result["auto_selected"] is auto
    assert result["confirmed_ecu_communication"] is False


def test_unknown_adapter_readback_never_invents_support():
    result = read_elm_detected_protocol("SEARCHING")
    assert result["protocol_id"] is None
    assert result["evidence"] == "unrecognized"


def test_us_2008_passenger_prioritizes_can_but_does_not_claim_certainty():
    x = assess_protocols(year=2008, market="US", make="Ford")
    assert x["candidates"][0]["id"] == "iso15765_4_can11_500"
    assert x["confidence"] == "unverified_hint"
    assert "confirmed" in x["notice"].lower()


@pytest.mark.parametrize("make,first", [
    ("Ford", "j1850_pwm"), ("Chevrolet", "j1850_vpw")
])
def test_older_us_manufacturer_is_weak_hint_only(make, first):
    x = assess_protocols(year=2000, market="US", make=make)
    assert x["candidates"][0]["id"] == first
    assert x["confidence"] == "unverified_hint"


def test_europe_2005_is_not_assigned_a_single_protocol():
    x = assess_protocols(year=2005, market="EU", make="Mercedes-Benz")
    assert len(x["candidates"]) > 3
    assert x["detection_command"] == "ATSP0"


def test_battery_electric_vehicle_has_no_fake_emissions_pid_claim():
    x = assess_protocols(year=2022, market="EU", fuel="battery-electric")
    assert x["candidates"][0]["id"] == "uds_on_can"
    assert "emissions" in x["warnings"][0]


def test_heavy_duty_and_obdonuds_are_not_generic_elm_supported():
    x = assess_protocols(year=2027, market="US", vehicle_class="heavy")
    ids = [c["id"] for c in x["candidates"]]
    assert {"j1939_250", "wwh_obd", "obdonuds"} <= set(ids)
    assert next(c for c in x["candidates"] if c["id"] == "obdonuds")["support"] == "metadata_only"


def test_hardware_detected_protocol_is_adapter_report_only():
    x = assess_protocols(year=2006, market="EU", detected_elm="A6")
    assert x["confidence"] == "adapter_reported"
    assert x["detected"]["confirmed_ecu_communication"] is False


@pytest.mark.parametrize("year", [1800, 2200])
def test_year_safety(year):
    with pytest.raises(ValueError):
        assess_protocols(year=year)


def test_exhaustive_standard_and_oem_ids_have_disjoint_layer_semantics():
    records = all_protocols()
    assert len(records) >= 35
    assert len({item["id"] for item in records}) == len(records)
    assert next(x for x in records if x["id"] == "vw_tp20")["layer"] == "manufacturer_specific"
    assert next(x for x in records if x["id"] == "j1979_classic")["layer"] == "diagnostic_application"


def test_early_eu_and_us_obd_can_not_asserted_before_adoption():
    x = assess_protocols(year=2000, market="EU", make="Mercedes-Benz")
    ids = {row["id"] for row in x["candidates"]}
    assert "iso9141_2" in ids
    assert "iso15765_4_can11_500" not in ids


def test_2006_european_w211_has_multiple_candidate_transports():
    x = assess_protocols(year=2006, market="EU", make="Mercedes-Benz")
    ids = {row["id"] for row in x["candidates"]}
    assert "iso14230_4_fast" in ids
    assert "iso15765_4_can11_500" in ids
    assert x["verified_obd_support"] is False
    assert any(p["id"] == "mercedes_oem" for p in x["oem_diagnostics"])


def test_obdonuds_not_assigned_to_every_modern_passenger():
    a = assess_protocols(year=2026, market="US", make="Toyota")
    b = assess_protocols(year=2025, market="EU", vehicle_class="heavy")
    assert all(c["id"] != "obdonuds" for c in a["candidates"])
    assert all(c["id"] != "obdonuds" for c in b["candidates"])


def test_pre_1996_vehicle_not_reported_as_generic_obd2():
    hint = assess_protocols(year=1992, market="EU")
    assert hint["candidates"] == []
    assert "Pre-1996" in hint["warnings"][0]


def test_oem_diagnostic_hints_separate_from_emissions_protocols():
    x = assess_protocols(year=2014, market="EU", make="Volkswagen")
    ids = {entry["id"] for entry in x["oem_diagnostics"]}
    assert {"vw_tp20", "kwp1281", "uds_on_can"} <= ids
    assert not any(entry["evidence"] == "hardware_verified" for entry in x["oem_diagnostics"])
