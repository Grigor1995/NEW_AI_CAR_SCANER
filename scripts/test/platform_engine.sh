#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ -f .engine-venv/Scripts/python.exe ]]; then
  engine_python="$PWD/.engine-venv/Scripts/python.exe"
else
  engine_python="$PWD/.engine-venv/bin/python"
fi
"$engine_python" -m pytest tests/integration/test_native_engine.py tests/integration/test_platform_launcher.py -q -o asyncio_default_fixture_loop_scope=function -o asyncio_default_test_loop_scope=function
cd services/platform_engine
"$engine_python" -m pytest -p native_acceleration \
  tests/ai tests/telemetry tests/vehicle_network tests/obd tests/unit tests/integration tests/security tests/ecosystem -q
