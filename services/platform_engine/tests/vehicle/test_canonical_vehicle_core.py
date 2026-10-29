"""Canonical vehicle-core import regardless of PYTHONPATH ordering.

No physical adapters or cloud network are accessed.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _probe(paths, cwd):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(map(str, paths))
    check = (
        "import vehicle.obd.client as c; "
        "import vehicle.protocol.registry as r; "
        "assert callable(c.GenericObdClient.connect); "
        "assert len(r.PROTOCOLS) >= 20; "
        "print(c.__file__)"
    )
    return subprocess.run(
        [sys.executable, "-c", check], cwd=cwd, env=env,
        capture_output=True, text=True, timeout=20,
    )


def test_root_first_import_resolves_real_obd_client(tmp_path):
    result = _probe([ROOT, BACKEND], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "backend" + os.sep + "vehicle" not in result.stdout
    assert "vehicle" + os.sep + "obd" + os.sep + "client.py" in result.stdout


def test_backend_first_import_resolves_same_shared_core(tmp_path):
    result = _probe([BACKEND, ROOT], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "backend" + os.sep + "vehicle" not in result.stdout
    assert "vehicle" + os.sep + "obd" + os.sep + "client.py" in result.stdout


def test_backend_only_pythonpath_uses_compatibility_import_shim(tmp_path):
    result = _probe([BACKEND], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "vehicle" + os.sep + "obd" + os.sep + "client.py" in result.stdout


def test_explicit_backend_namespace_keeps_legacy_simulator_service():
    from backend.vehicle.obd.service import ObdDiagnosticService
    from backend.vehicle.obd.client import GenericObdClient as LegacyClient
    from vehicle.obd.client import GenericObdClient as SharedClient
    assert ObdDiagnosticService is not None
    assert LegacyClient is not SharedClient
