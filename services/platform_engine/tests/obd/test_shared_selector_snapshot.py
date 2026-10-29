import json
from pathlib import Path

from obd.catalog import selector_entries
import runpy

ROOT = Path(__file__).resolve().parents[2]
build_snapshot = runpy.run_path(str(ROOT / "scripts/sync_offline_selector.py"))["build_snapshot"]


def test_native_snapshot_covers_every_backend_generation_and_engine_year():
    snapshot = json.loads((ROOT / 'shared/vehicle_catalog.json').read_text())
    fields = ('make', 'model', 'chassis', 'year', 'engine')
    keys = {tuple(row.get(k) for k in fields) for row in snapshot['vehicles']}
    assert all(tuple(row.get(k) for k in fields) in keys for row in selector_entries())
    assert len(keys) == len(snapshot['vehicles'])
    assert build_snapshot(snapshot) == snapshot


def test_generated_snapshot_preserves_curated_ecu_and_marks_reference_scope():
    curated = {'make':'Mercedes-Benz','model':'E-Class','chassis':'W211','year':2006,
               'engine':'M272 E35 3.5','ecu':'ME9.7','fuel':'Petrol'}
    output = build_snapshot({'vehicles':[curated]})
    assert output['vehicles'][0] == curated
    references = [r for r in output['vehicles'] if r.get('scope') == 'generation-reference-not-vin-fitment']
    assert references
    assert all(row['ecu'] is None and row['source'].startswith('https://') for row in references)
