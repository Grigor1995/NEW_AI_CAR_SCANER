#!/usr/bin/env bash
set -euo pipefail
cd /workspace/NEW_AI_CAR_SCANER
python3 scripts/build/cloud_bootstrap.py
source /workspace/toolchains/env.sh
cmake --preset dev
cmake --build --preset dev
ctest --preset dev
python3 scripts/test/http_smoke.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software XDG_CONFIG_HOME=/workspace/.cache/cda-qa-config XDG_DATA_HOME=/workspace/.cache/cda-qa-data ./build/dev/car_diagnostic --self-test
