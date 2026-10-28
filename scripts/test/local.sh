#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ -f /workspace/toolchains/env.sh ]]; then source /workspace/toolchains/env.sh; fi
ctest --preset dev
python3 scripts/test/http_smoke.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ./build/dev/car_diagnostic --self-test
python3 scripts/test/source_contracts.py
