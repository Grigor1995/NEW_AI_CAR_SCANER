#!/usr/bin/env bash
set -eu
cd /workspace/NEW_AI_CAR_SCANER
python3 -m venv .venv
.venv/bin/python -m pip install -r finalbuild/backend/requirements-dev.txt -r finalbuild/apps/desktop/requirements.txt -r native/obd/requirements-build.txt
.venv/bin/cmake -S native/obd -B .build-tools/obd -Dpybind11_DIR="$(.venv/bin/python -m pybind11 --cmakedir)" -DPython_EXECUTABLE="$PWD/.venv/bin/python" -DCMAKE_BUILD_TYPE=Release
.venv/bin/cmake --build .build-tools/obd -j 2
PYTHONPATH="$PWD/.build-tools/obd" .venv/bin/python -m pytest finalbuild/tests/obd/test_native_tcp.py -q
