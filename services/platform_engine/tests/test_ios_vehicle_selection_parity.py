"""Regression guards for iOS dependent vehicle filters and catalog refresh."""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] /
          "apps/mobile-ios/AICarScanner/DiagnosticScreen.swift")


def test_vehicle_picker_cascades_from_make_to_ecu():
    source = SOURCE.read_text(encoding="utf-8")
    for selection in ["make", "model", "chassis", "year", "engine"]:
        assert f".onChange(of: {selection})" in source
    assert "ecu = ecus.first ?? \"\"" in source


def test_offline_status_depends_on_backend_connectivity():
    source = SOURCE.read_text(encoding="utf-8")
    assert "if !viewModel.catalogOnline {" in source


def test_api_url_settings_offer_explicit_catalog_refresh():
    source = SOURCE.read_text(encoding="utf-8")
    assert "await viewModel.loadCatalog()" in source
    assert "Refresh catalog" in source


def test_new_session_reset_has_no_hardcoded_vehicle_fitment():
    source = SOURCE.read_text(encoding="utf-8")
    reset = source.split("private func reset(){", 1)[1].split("}", 1)[0]
    assert 'make=makes.first ?? ""' in reset
    assert "M272 E35 3.5" not in reset
