import pytest
from fastapi import HTTPException

import api.vehicle_catalog_routes as routes


@pytest.fixture(autouse=True)
def isolate_reference_catalog(monkeypatch):
    # This module verifies SQL construction. Integration tests cover merged data.
    monkeypatch.setattr(routes, "selector_entries", lambda **filters: [])


def sample_entry(**overrides):
    row = {
        "make": "Mercedes-Benz",
        "model": "E350",
        "chassis": "W211",
        "year": 2006,
        "engine": "M272 3.5",
        "ecu": "ME 9.7",
        "fuel": ["petrol", "LPG"],
        "source": "test",
        "scope": "curated-fitment",
    }
    row.update(overrides)
    return row


def capture_run_all(monkeypatch, result=None):
    calls = []
    def fake_run_all(sql, params):
        calls.append((sql, params))
        return list(result or [])
    monkeypatch.setattr(routes, "_run_all", fake_run_all)
    return calls


def test_list_entries_includes_only_nonblank_filters(monkeypatch):
    calls = capture_run_all(monkeypatch, [sample_entry()])
    entries = routes.list_entries(
        make="Mercedes-Benz", model=" E350 ", chassis=" ", year=2006, engine=None, ecu="ME 9.7"
    )
    sql, params = calls[0]
    assert len(entries) == 1
    assert entries[0]["chassis"] == "W211"
    assert "make = :make" in sql
    assert "model = :model" in sql
    assert "year = :year" in sql
    assert "ecu = :ecu" in sql
    assert "chassis = :chassis" not in sql
    assert params == {
        "make": "Mercedes-Benz",
        "model": " E350 ",
        "year": 2006,
        "ecu": "ME 9.7",
    }


def test_list_entries_without_filters_uses_base_where_clause(monkeypatch):
    calls = capture_run_all(monkeypatch)
    assert routes.list_entries() == []
    sql, params = calls[0]
    assert "WHERE 1=1" in sql
    assert params == {}


def test_list_makes_and_models_extract_values(monkeypatch):
    calls = capture_run_all(monkeypatch, [{"make": "BMW"}, {"make": "Mercedes-Benz"}])
    assert routes.list_makes() == ["BMW", "Mercedes-Benz"]
    assert "SELECT DISTINCT make" in calls[-1][0]

    calls = capture_run_all(monkeypatch, [{"model": "E350"}, {"model": "E500"}])
    assert routes.list_models("Mercedes-Benz") == ["E350", "E500"]
    assert calls[-1][1] == {"make": "Mercedes-Benz"}


@pytest.mark.parametrize(
    ("handler", "args", "result_key", "values"),
    [
        (routes.list_chassis, {"make": "Mercedes-Benz", "model": "E350"}, "chassis", ["W211", "W212"]),
        (routes.list_years, {"make": "Mercedes-Benz", "model": "E350", "chassis": "W211"}, "year", [2006, 2005]),
        (routes.list_engines, {"make": "Mercedes-Benz", "model": "E350", "year": 2006, "chassis": "W211"}, "engine", ["M272 3.5"]),
        (routes.list_ecus, {"make": "Mercedes-Benz", "model": "E350", "engine": "M272 3.5", "year": 2006, "chassis": "W211"}, "ecu", ["ME 9.7"]),
    ],
)
def test_catalog_facets_apply_filters_and_extract_values(monkeypatch, handler, args, result_key, values):
    calls = capture_run_all(monkeypatch, [{result_key: value} for value in values])
    result = handler(**args)
    assert result == values
    sql, params = calls[0]
    assert "WHERE" in sql
    assert params["make"] == "Mercedes-Benz"
    assert params["model"] == "E350"


def test_catalog_facets_reject_blank_make_or_model(monkeypatch):
    calls = capture_run_all(monkeypatch)
    with pytest.raises(HTTPException) as make_error:
        routes.list_chassis("  ", "E350")
    assert make_error.value.status_code == 400
    with pytest.raises(HTTPException) as model_error:
        routes.list_engines("Mercedes-Benz", " ")
    assert model_error.value.status_code == 400
    assert calls == []


def test_engine_route_parameters_preserve_year_and_chassis(monkeypatch):
    calls = capture_run_all(monkeypatch, [{"engine": "M272 3.5"}])
    assert routes.list_engines("Mercedes-Benz", "E350", year=2006, chassis="W211") == ["M272 3.5"]
    sql, params = calls[0]
    assert "WITH exact AS" in sql
    assert "scope = 'curated-fitment'" in sql
    assert params == {"make": "Mercedes-Benz", "model": "E350", "year": 2006, "chassis": "W211"}


def test_resolve_variant_returns_curated_and_broad_rows(monkeypatch):
    expected = [sample_entry(), sample_entry(chassis=None, scope="broad")]
    calls = capture_run_all(monkeypatch, expected)
    result = routes.resolve_variant("Mercedes-Benz", "E350", 2006, "M272 3.5", chassis="W211", ecu="ME 9.7")
    assert result == expected
    sql, params = calls[0]
    assert "CASE WHEN scope = 'curated-fitment' THEN 0 ELSE 1 END" in sql
    assert params == {
        "make": "Mercedes-Benz",
        "model": "E350",
        "year": 2006,
        "engine": "M272 3.5",
        "chassis": "W211",
        "ecu": "ME 9.7",
    }


def test_database_failures_become_service_unavailable(monkeypatch):
    def fail():
        raise RuntimeError("database offline")
    monkeypatch.setattr(routes, "_ensure_catalog_table", fail)
    with pytest.raises(HTTPException) as error:
        routes._run_all("SELECT 1", {})
    assert error.value.status_code == 503
    assert "database offline" in error.value.detail
