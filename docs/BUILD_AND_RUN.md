# Build and run V3

The previous Python/venv launcher commands no longer apply to this rewrite. Install CMake >=3.24, Ninja, a matching C++20 compiler, OpenSSL 3 and Qt 6.8+ with Quick/QuickControls2, Core, Network, Sql/SQLite, SerialPort(desktop), Concurrent, Test, Svg+image plugin, HttpServer/WebSockets and LinguistTools.

## Linux cloud

```bash
python3 scripts/build/cloud_bootstrap.py
source /workspace/toolchains/env.sh
cmake --preset dev
cmake --build --preset dev
ctest --preset dev
./build/dev/car_diagnostic
```

Headless check: QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ./build/dev/car_diagnostic --self-test. Shared pure core without Qt: cmake --preset core; cmake --build --preset core; ctest --preset core. Sanitizers and coverage have their own presets. Run python3 scripts/test/http_smoke.py for actual HTTP checks. No user-facing localhost preview is required.

## Windows Git Bash

Install the desktop Qt/OpenSSL/compiler/CMake/Ninja toolchains first and put matching tools on PATH. Set QT_ROOT to your actual Qt kit directory, then:

```bash
git switch main
git pull --ff-only
export QT_ROOT='C:/Qt/6.8.3/mingw_64'  # replace with your installed kit
bash scripts/build/windows-git-bash.sh
```

The path is an example, not an installed SDK. Windows build/package execution is NOT RUN here. MSVC kits require an initialized MSVC build environment; do not mix MinGW/MSVC OpenSSL or Qt libraries. Android/iOS need their native SDKs and matching Qt/OpenSSL kits; read apps/android/README.md and apps/ios/README.md. No ready Windows EXE/APK/IPA is provided by the Linux build.
