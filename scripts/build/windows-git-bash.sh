#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${QT_ROOT:?Set QT_ROOT to your Qt 6.8+ desktop kit, e.g. C:/Qt/6.8.3/mingw_64}"
cmake --preset dev -DCMAKE_PREFIX_PATH="$QT_ROOT"
cmake --build --preset dev
ctest --preset dev
./build/dev/car_diagnostic.exe
