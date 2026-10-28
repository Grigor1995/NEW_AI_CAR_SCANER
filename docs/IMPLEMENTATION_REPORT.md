# NEW_AI_CAR_SCANER implementation status

Date: 2026-10-28. This is the source-preserving foundation and native TCP
milestone, not completion of the production ecosystem.

## Source and reuse

Imported `Grigor1995/AI-CAR-SCANER` main at
`a71c547b4b58f88f9c09f7f25d86931b79131bd2`, followed by its existing ecosystem
foundation branch at `540e00f07b8f60c2788c8d12dea1200817669afb`. Git history is
preserved. The original source repository is unchanged. The new repository's
origin remains `Grigor1995/NEW_AI_CAR_SCANER`.

Reused PySide6 desktop, Kotlin Android, Swift iOS, original UI/icons/backgrounds,
FastAPI, shared vehicle catalog, DiagnosticSession, protocol parsing, rules,
AI/RAG, simulators, reports and existing test suites. Also reused the source's
opt-in account/ownership/workshop consent foundation, additive Alembic revision,
role contracts, technical documentation and interactive architecture. Historical
source results are retained separately in
[evidence/imported-foundation-implementation-report.md](evidence/imported-foundation-implementation-report.md).
The current execution results below supersede assumptions based on those results.

## New C++ implementation

- Added `native/obd`: C++20/pybind11 TCP connection, nonblocking socket I/O,
  bounded 64 KiB prompt-delimited buffering, partial writes, deadlines, RAII
  socket cleanup and narrow read-only command validation.
- Added async `NativeObdWifiTransport` behind the existing DiagnosticTransport.
  Native calls release the GIL and run off the UI/event-loop thread; cancellation
  drains the bounded worker before closing its socket.
- Acquisition and device connection factories select it only with boolean
  `native_tcp: true`. Existing Python transports remain the default. Missing
  native builds fail explicitly when selected.
- Added loopback integration/negative tests through the real GenericObdClient,
  including initialization, measured response decoding and DTC retrieval.
- Updated architecture data and regenerated Mermaid views. Preserved the existing
  UI files and icon family; no new dashboard template or duplicate engine.

This implementation validates Linux TCP/IPv4 only. POSIX macOS compilation is
untested; Windows/mobile bindings, native BLE/USB, UDS addressing and native
protocol decoding are not implemented by this extension. Existing transports
remain available. No physical-device or acceleration claim is made.

## Current machine validation

| Check | Result |
|---|---|
| Focused imported foundation/OBD/golden/unit regression | 189 passed |
| Shared regression after first native integration | 1,017 passed, 2 skipped; 0 failures/errors |
| Final OBD + acquisition + device integration after last changes | 187 passed, including 19 native loopback cases |
| Desktop logic / diagnostic E2E / negative / UI-POM / widgets | 216 / 6 / 68 / 142 / 25 passed; 1 platform skip |
| Desktop all-source / production-core coverage | 90.43% / 90.84% |
| Local ecosystem HTTP smoke | 10 checks passed: migration, approval, scoped read, legacy bypass denial, revocation and restart persistence |
| Persistent local development server | health, read-only OBD plan and nonempty shared vehicle catalog passed |
| Interactive architecture in Chromium | 10 views / 22 nodes; search, layers, collapse, details, relationships, zoom, pointer pan, wheel and theme passed |
| C++20 Release build | passed with GCC 14.2, pybind11 3.1.0, CMake 4.4.4 |
| Repeated saved setup script | passed |
| Python static checks / Git whitespace | passed for new adapter/tests and changed files |

Selections overlap; do not sum these as unique tests. The final targeted run
includes changes added after the full shared regression. Native C++ and new
adapter coverage are not measured; desktop coverage is not a substitute.
[Machine-readable current results](evidence/new-repository-validation.json).
[Installed Python versions](evidence/cloud-python-dependencies.txt).

The existing deterministic fixture benchmark measured p50 0.50 ms, p95 0.67 ms,
min 0.45 ms, max 1.13 ms. This excludes OBD polling, socket latency and LLM
inference. It does not measure C++ acceleration or establish vehicle latency.
Startup/navigation/memory and physical adapter performance remain unmeasured.

## API and database changes

No additional HTTP API or schema changes were introduced by the C++ milestone.
The reused foundation exposes `/api/v2/ecosystem` and additive revision
`0001_ecosystem`; see API_SPECIFICATION.md and DATABASE_DESIGN.md. Keep its
feature flag off for the current unauthenticated native clients. Legacy local
APIs are not suitable for public multi-tenant exposure.

## Reproducible development

[Native build and activation](../native/obd/README.md).
[Cloud startup and checks](CLOUD_DEVELOPMENT.md).
The tested installation and startup instructions are saved in environment draft
fields `install_script` and `start_skill`. Review/save them in environment
settings, then publish the environment. Draft persistence is not publication or
fresh-task restoration evidence. Dependencies persist; live processes must restart.

## Outstanding product and release work

The full staged roadmap remains in DEVELOPMENT_PLAN.md. Authenticated diagnostic
adapters and native login/workspace/consent screens precede enabling ecosystem
mode. Verified contacts, unattended scheduling, notification providers, licensed
wiring/repair data, work orders, merchant commerce and admin management/analytics
remain later milestones. No production statistics or repair data are fabricated.

Real OBD hardware, live PostgreSQL concurrency/backup, external providers,
Windows packaging, Android build and iOS/Xcode validation were not executed in
this machine. Original source reports of platform runs are historical evidence,
not current certification. Production hardening and complete cross-platform
release acceptance remain outstanding.
