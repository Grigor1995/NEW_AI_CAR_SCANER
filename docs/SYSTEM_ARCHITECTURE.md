# System architecture

## Existing runtime and first extension

Keep PySide6 Desktop, Kotlin Compose Android, SwiftUI iOS and the shared FastAPI
backend. Native transport bridges carry Bluetooth/BLE/Wi-Fi/serial bytes;
`device`, `obd`, `telemetry`, `diagnostic` and `ai` own shared decoding,
DiagnosticSession, evidence, recommendations and recalculation. Local backend
plus optional GGUF remains the offline diagnostic topology. PostgreSQL is the
shared-service target; Desktop SQLite remains supported.

First foundation milestone: versioned account/ownership/consent APIs, durable
sessions, three primary modes USER/CUSTOMER/ADMIN, and a MARKET merchant role.
`/api/v2/ecosystem` is feature-gated. The old API is preserved in local mode;
when ecosystem mode is enabled its anonymous paths are denied rather than
allowing a parallel unprotected data path. This does not yet retrofit native
login screens or authenticate the full legacy diagnostic workflow.

## Boundaries

1. UI selection cannot grant a role. Server-side account roles control modes.
2. CUSTOMER requires staff membership in the requested center; roles reuse the
   existing workshop owner/admin/technician/viewer enum and permission helpers.
3. A workshop invitation alone grants no vehicle access. The authenticated
   owner accepts for one owned profile, selected read scopes and expiry.
4. Every read rechecks account status, staff activity and current consent.
5. ADMIN is a primary platform mode, not a universal vehicle-data override.
6. MARKET is attached to an account's permitted primary workspace; it cannot
   select a fourth diagnostic mode or influence diagnostic fault ranking.

## Planned services, explicitly not active

Scheduler/outbox delivery, verified email/mobile, service recommendations,
licensed repair diagrams, work orders, merchant products/offers, role-management
UI, multi-device sync and platform-wide analytics are later milestones. C++
diagnostic-core extraction remains proposed pending profiling. The optional
C++20 TCP transport is implemented separately; see `native/obd/README.md`. Do not use the architecture's proposed nodes as deployment claims.

The interactive visualization is [local HTML](architecture/interactive_architecture.html).
Its data and assets are local; Mermaid source is maintained alongside it.
