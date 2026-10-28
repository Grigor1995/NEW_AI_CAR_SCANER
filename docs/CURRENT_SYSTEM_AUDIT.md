# Current system audit

Date: 2026-10-28 (Asia/Yerevan). Baseline: `a71c547`. Branch:
`feature/ecosystem-foundation-20261028`. Audit completed before foundation code changes.

## Actual repository

Git root is the directory containing `build.py`, `runner.py`, `installer.py` and
`finalbuild/`. There are 975 tracked files: 439 Python, 58 Kotlin, 19 Swift;
151 backend files, 147 common test files, 51 Desktop files, 160 Android files
and 102 iOS files. Counts include assets; they are not test-case counts.
No tracked C++, headers, JNI or CMake implementation was found.
`main` is the integration base; remote neon-UI and desktop-recovery branches
also exist. This task creates a new branch and does not merge/delete them.

## Reuse classification

| Component / actual path | Decision | Evidence / necessary extension |
|---|---|---|
| `apps/desktop/ui.py`, `demo_ui.py` | REUSE | Working PySide6 navigation, themed panels, editable launcher, charts, reports; no replacement UI |
| Android `presentation`, `data/obd` | EXTEND | Native Compose; Classic/BLE/Wi-Fi/USB clients; account/token workspaces absent |
| iOS `AICarScanner` | EXTEND | Native SwiftUI, BLE/Wi-Fi bridges, same assets; account workspace absent; no generic iOS serial guarantee |
| `assets/launcher`, `assets/vehicle_models` | REUSE | Abstract vehicle brand, neon 3D icons, shared generation portraits; keep existing light/dark styles |
| `diagnostic/models.py` | REUSE | One DiagnosticSession, evidence provenance, test history; retain IDs internally, not in report UI |
| `diagnostic/rules.py`, `ai/reasoning/engine.py` | REUSE | Evidence-ranked hypotheses, completed-test replay/recalculation, deterministic fallback; existing golden scenario passes |
| `ai/llm`, `ai/rag`, `ai/ingestion`, `ai/ml` | EXTEND | Existing local/HTTP providers, retrieval, ingest, numeric anomaly logic; no separate diagnostic engine |
| `device`, `vehicle`, `obd`, `acquisition`, `telemetry` | EXTEND | Capability-driven ELM/ISO-TP/UDS/read-only discovery, simulator and reconnect logic; physical coverage unavailable |
| `data`, `shared/vehicle_catalog.json`, catalog APIs | REUSE | Shared catalog and fitment sources; no invented universal model/protocol compatibility |
| `diagnostic/session_persistence.py`, `api/state.py` | EXTEND | SQLAlchemy JSON snapshots; global cache/registry currently not owner-scoped |
| `api/client_features_routes.py` | EXTEND | Shared profile and Unicode PDF contracts; legacy profiles lack ownership |
| `professional_platform` | REFACTOR incrementally | Useful Organization/Membership/Role/RBAC models; in-memory organization/audit data are not a durable tenant boundary |
| `security/auth.py`, `security/rbac.py` | EXTEND alongside legacy | Token/permission helpers have unit tests but no API enforcement; token claims/header validation insufficient for new public accounts |
| `api/platform_routes.py` | REFACTOR boundary | Organization audit endpoint has no authentication; legacy role names are workshop staff roles, not USER/CUSTOMER/ADMIN modes |
| `infrastructure/postgres/schema.sql` | EXTEND | Existing relational bootstrap + pgvector; no checked-in Alembic environment/revision history despite installed dependency |
| New identity/ownership/consent schema | EXTEND | Add versioned tables; never infer ownership of existing anonymous profiles |
| Build/runner/installer/environment JSON | REUSE | Local-only builds; optional GGUF/runtime provisioning and bundled source; no CI/CD introduced |
| Whole-language rewrite | REJECT | No measured local diagnostic bottleneck justifies C++ migration now |

## Security findings

There are 87 decorated synchronous API route functions (async routes not included
in this count). No `Depends`/Bearer/verify_token enforcement was found in the
existing API routers. Anonymous session IDs, vehicle profiles, device control
and workshop audit are not a production multi-tenant security boundary. Existing
role helpers alone do not authorize HTTP requests. Keep legacy operation local;
new ecosystem rollout must fail closed and block legacy API bypasses when enabled.
An admin workshop role must never imply a platform ADMIN account.

## Gaps and inconsistencies

No real USER/CUSTOMER/ADMIN account lifecycle, verified contact delivery, durable
sharing grants, scheduler, notification delivery, merchant catalog or licensed
repair-data integration was found. Existing organization analytics are in-memory,
not registered-user production analytics. The PostgreSQL bootstrap and JSON
snapshot schemas coexist. Native transports remain platform-specific while PID
planning/decoding and diagnostic decisions remain backend-owned. Android defaults
to a historical hosted API URL unless runner/settings overrides it. iOS, Windows
packaging and real hardware cannot be validated from this Linux host.

Prior audits under `finalbuild/docs/maintenance`, `reviews`, `obd`, `testing` are
retained; this report supersedes only assumptions about new ecosystem readiness.

Additional audit finding: the legacy session-creation route manually constructs
Vehicle from an untyped dict; malformed nested input can raise an unhandled
Pydantic error. Its typed v2 profile endpoint rejects malformed inputs with
localized 422 responses. Legacy normalization/hardening remains milestone 1B.

## NEW_AI_CAR_SCANER transfer audit

The source repository was fetched from Grigor1995/AI-CAR-SCANER. Source main
was a71c547b4b58f88f9c09f7f25d86931b79131bd2; its existing foundation branch
was 540e00f07b8f60c2788c8d12dea1200817669afb. Both histories are retained in
the new repository. The earlier empty-target audit was preserved outside the
checkout in `/workspace/setup-evidence/empty-repository-audit`. The source
checkout remains unchanged. Counts and findings above describe the imported
baseline, not newly certified behavior. The new C++ transport is an additive
milestone; desktop/mobile UI, icons and diagnostic decisions are not replaced.
