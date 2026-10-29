# Source-compatible diagnostic companion

This directory preserves backend, shared data and vehicle/device modules from
`Grigor1995/AI-CAR-SCANER` main at `a71c547b4b58f88f9c09f7f25d86931b79131bd2`,
plus the additive ownership/consent foundation at
`540e00f07b8f60c2788c8d12dea1200817669afb`.
The original desktop/mobile presentation and installers are not imported.
The current C++/QML client remains the application UI.

`app.py` installs the optional C++ kernels before importing source routes.
`native_acceleration.py` supplies the typed C ABI binding. Failure to load the
library is observable at `/api/v1/migration/runtime`; Python fallback retains the
source service. The desktop's physical TCP/serial path is C++ independently.

Start from the repository root with `scripts/run_platform_engine.py`, not a
working-directory-dependent direct uvicorn invocation. It binds loopback only
and chooses an explicit local SQLite file unless DATABASE_URL is already set.
Accounts, session IDs and permissions are separate from the V3 local Store.
Do not expose the source-compatible v1 APIs as an authenticated remote service.
The optional ecosystem mode uses a separate default DB and blocks the unowned
legacy routes according to its original consent boundary.

See [migration analysis](../../docs/migration/README.md) for setup, tested scopes,
source provenance, retained Python components and platform limitations.
