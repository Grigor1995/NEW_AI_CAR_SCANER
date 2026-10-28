#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ -f /workspace/toolchains/env.sh ]]; then source /workspace/toolchains/env.sh; fi
cmake --preset dev
cmake --build --preset dev
ctest --preset dev
