from __future__ import annotations

import json

import pytest

from scripts import seed_vehicle_catalog as seed


def test_stable_id_is_deterministic_and_uses_optional_identifiers():
    first = seed.stable_id("Mercedes-Benz", "W211", "W211", 2006, "M272", "ME9.7")
    assert first == seed.stable_id("Mercedes-Benz", "W211", "W211", 2006, "M272", "ME9.7")
    assert len(first) == 32
    assert first != seed.stable_id("Mercedes-Benz", "W211", None, 2006, "M272", None)


def test_expand_years_handles_reversed_and_multiple_ranges():
    assert seed.expand_years([[2003, 2001], [2005, 2005], [2003, 2004]]) == [2001, 2002, 2003, 2004, 2005]
    assert seed.expand_years([]) == []
    with pytest.raises(ValueError, match="Invalid year range"):
        seed.expand_years([[2000], [2001, 2002]])


def test_build_rows_expands_ecus_years_and_filters_blank_values():
    payload = {
        "source": "fixture-source",
        "scope": "fixture-scope",
        "entries": [
            {
                "make": " Mercedes-Benz ",
                "model": " W211 ",
                "chassis": " ",
                "year_ranges": [[2006, 2007]],
                "engines": [
                    {"name": " M272 ", "ecus": [" ME9.7 ", "", "MED17 "], "fuel": [" Petrol ", "", " LPG "]},
                    {"name": "OM642", "ecus": [], "fuel": []},
                ],
            }
        ],
    }

    rows = seed.build_rows(payload)

    assert len(rows) == 6
    assert {row["year"] for row in rows} == {2006, 2007}
    assert {row["ecu"] for row in rows if row["engine"] == "M272"} == {"ME9.7", "MED17"}
    assert all(row["chassis"] is None for row in rows)
    assert all(row["fuel"] == ["petrol", "lpg"] for row in rows if row["engine"] == "M272")
    assert {row["ecu"] for row in rows if row["engine"] == "OM642"} == {None}
    assert all(row["source"] == "fixture-source" and row["scope"] == "fixture-scope" for row in rows)


def test_build_rows_uses_defaults_for_missing_source_scope_ecu_and_fuel():
    rows = seed.build_rows({
        "entries": [{
            "make": "A",
            "model": "B",
            "year_ranges": [[2010, 2010]],
            "engines": [{"name": "E"}],
        }]
    })
    assert rows[0]["year"] == 2010
    assert rows[0]["ecu"] is None
    assert rows[0]["fuel"] == []
    assert rows[0]["source"] == "project-curated-seed"
    assert rows[0]["scope"] == "curated-fitment"


def test_main_rebuilds_catalog_with_seed_rows_and_commits(tmp_path, monkeypatch, capsys):
    payload = {
        "source": "tests",
        "entries": [
            {
                "make": "Mercedes-Benz",
                "model": "W211",
                "year_ranges": [[2006, 2006]],
                "engines": [{"name": "M272", "ecus": ["ME9.7"], "fuel": ["petrol"]}],
            }
        ],
    }
    data_file = tmp_path / "catalog.json"
    data_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(seed, "DATA_FILE", data_file)
    monkeypatch.setattr(seed, "DATABASE_URL", "sqlite:///ignored-by-fake")

    calls = {"created": None, "deleted": None, "rows": [], "committed": False, "engine_args": None}

    class FakeTable:
        @staticmethod
        def create(engine, checkfirst):
            calls["created"] = (engine, checkfirst)

    class FakeRow:
        __table__ = FakeTable()

        def __init__(self, **values):
            self.values = values

    class FakeQuery:
        def delete(self, synchronize_session):
            calls["deleted"] = synchronize_session
            return 1

    class FakeDb:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def query(self, model):
            assert model is FakeRow
            return FakeQuery()

        def add_all(self, rows):
            calls["rows"] = rows

        def commit(self):
            calls["committed"] = True

    engine = object()

    def fake_create_engine(url, **kwargs):
        calls["engine_args"] = (url, kwargs)
        return engine

    monkeypatch.setattr(seed, "create_engine", fake_create_engine)
    monkeypatch.setattr(seed, "Session", lambda _engine: FakeDb())
    monkeypatch.setattr(seed, "VehicleCatalogEntryRow", FakeRow)

    seed.main()

    assert calls["created"] == (engine, True)
    assert calls["deleted"] is False
    assert len(calls["rows"]) == 1
    assert calls["rows"][0].values["make"] == "Mercedes-Benz"
    assert calls["committed"] is True
    assert calls["engine_args"][0] == "sqlite:///ignored-by-fake"
    assert "Seeded 1 vehicle catalog rows" in capsys.readouterr().out
