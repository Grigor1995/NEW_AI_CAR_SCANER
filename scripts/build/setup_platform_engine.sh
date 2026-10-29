#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ "${OS:-}" == "Windows_NT" ]] && command -v py >/dev/null 2>&1; then
  py -3 -m venv .engine-venv
elif [[ "${OS:-}" == "Windows_NT" ]]; then
  echo "Install official Windows Python 3.12+ with the py launcher, then rerun." >&2
  exit 1
else
  python -m venv .engine-venv
fi
if [[ -f .engine-venv/Scripts/python.exe ]]; then
  engine_python=.engine-venv/Scripts/python.exe
else
  engine_python=.engine-venv/bin/python
fi
"$engine_python" -m pip install -r services/platform_engine/backend/requirements.txt httpx pytest pytest-asyncio
