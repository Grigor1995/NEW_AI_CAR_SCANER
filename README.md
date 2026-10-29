# CAR DIAGNOSTIC ANALYSIS — V3

New C++20 / Qt 6.8 / QML foundation for a shared automotive diagnostic system.
The native V3 application replaces the old desktop UI. The later functionality
migration restores source-compatible backend services as a separate local
companion; see the migration section below. Git history and
`archive/pre-v3-ac8d946` preserve the previous implementation.

**Current state:** Linux-built development milestone, not a complete production
ecosystem. Real TCP/desktop serial source, protocol decoding, local accounts,
private vehicle profiles, persistent settings, deterministic analysis, write
safety policy and an interactive architecture dashboard are implemented in the
scopes documented below. ECU writes remain locked. Hardware and native
Windows/Android/iOS release validation have not run. Payments are not implemented.

## Source functionality migration

The source diagnostic platform is available through **Application → Diagnostic
platform** and the Guided Tests / Teach AI / ECU Network tiles. It preserves
135 source API operations, reasoning/RAG, telemetry, vehicle catalogs,
JSON/PDF reports and the optional consent foundation. The Qt client and physical
TCP/serial polling remain C++; the companion retains Python business/AI services
and calls compiled C++ telemetry/PID kernels where enabled.

[Full repository analysis, feature mapping, Windows startup and limitations](docs/migration/README.md).
Companion setup: `bash scripts/build/setup_platform_engine.sh`; start it with
`.engine-venv/Scripts/python.exe scripts/run_platform_engine.py` on Windows or
`.engine-venv/bin/python scripts/run_platform_engine.py` on Linux, then launch the
Qt application in another terminal. Companion sessions/accounts are separate
from the V3 native Store; provider-dependent capabilities need configuration.

## Launcher UI correction

The home screen now follows the supplied original background, 3D icons and
12-tile layout. Open **Application → Settings** for preferences. Explicitly themed
controls fix the light-text/white-background problem shown on Windows.
[Current screenshots and validation](docs/testing/UI_REFERENCE_CORRECTION.md).

## Build and run

Requires CMake >=3.24, Ninja, C++20, OpenSSL 3 and Qt 6.8+ modules listed in
[BUILD_AND_RUN](docs/BUILD_AND_RUN.md). The old Python launcher no longer applies.

```bash
cmake --preset dev
cmake --build --preset dev
ctest --preset dev
./build/dev/car_diagnostic
```

Windows Git Bash after installing matching Qt/compiler/OpenSSL tools:

```bash
export QT_ROOT='C:/Qt/6.8.3/mingw_64' # replace with your actual kit
bash scripts/build/windows-git-bash.sh
```

Cloud Linux setup: `python3 scripts/build/cloud_bootstrap.py`, then
`source /workspace/toolchains/env.sh` before building. Native platform build
instructions and limitations are in `apps/windows`, `apps/android`, `apps/ios`.

## Documentation and evidence

- [Implementation report](docs/IMPLEMENTATION_REPORT.md)
- [Product specification V3](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture and domain boundaries](docs/SYSTEM_ARCHITECTURE.md)
- [Interactive architecture dashboard — open locally](docs/architecture/interactive_architecture.html)
- [Phased development plan](docs/DEVELOPMENT_PLAN.md)
- [Local testing](docs/TEST_METHODOLOGY.md)
- [Documentation index](docs/README.md)

The dashboard bundles all scripts locally and distinguishes implemented, partial,
planned, blocked and disabled components. No CI/CD workflows or active payment
code are included.
