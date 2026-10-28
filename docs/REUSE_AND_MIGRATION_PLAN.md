# Reuse and migration plan

## Foundation boundary

Add `/api/v2/ecosystem` behind `AI_CAR_ECOSYSTEM_ENABLED`, disabled by default.
Preserve existing APIs and native UI in the default local mode. In ecosystem
mode, deny legacy `/api/*` routes rather than letting anonymous legacy paths
bypass owner/consent enforcement. Native authenticated clients are a subsequent
milestone; enabling the feature before those clients migrate is intentionally
not transparent. Document this opt-in compatibility boundary.

Reuse existing Vehicle JSON/profile storage, the professional Membership/Role
permission helpers, DiagnosticSession and all reasoning/OBD APIs internally.
New accounts, roles, opaque login sessions, workshop staff, invitations and
per-vehicle grants require durable tables. Existing anonymous vehicles remain
unclaimed: no automatic assignment to the first account. MARKET is a merchant
role/portal attached to a primary mode, never a fourth diagnostic mode.

## Safe schema rollout

Introduce Alembic configuration and additive revision(s), with PostgreSQL as the
production target and SQLite integration tests. Add new `ecosystem_*` tables;
reference existing `vehicle_profiles` with a foreign key and retain its payload
contract. Never rewrite current vehicle/session tables or copy production rows
implicitly. Run migrations explicitly; do not silently create ecosystem tables
when the feature is enabled. Test preservation of a pre-existing legacy row,
upgrade idempotence via Alembic version tracking and downgrade dependencies.

Deploy backup -> migrate -> authenticated API smoke tests -> migrate native
clients -> enable feature -> monitor. Rollback the feature flag first. Database
downgrade is an explicit operator action and removes only foundation tables;
keep legacy rows and user reports. Reconcile duplicate legacy users/organization
identities via an approved mapping later; do not equate emails with authorization.

## Technology choices

Keep Python/SQLAlchemy/FastAPI, PySide6, Kotlin and Swift. Current deterministic
processing is well below the requested p95 90 ms budget in the isolated golden
fixture; C++ extraction requires a reproducible hot-path profile first. Keep
transport bridges native where permissions/background restrictions demand it.
All external integrations must expose actual availability and verification
states; no pretend successful email, SMS, unattended scan or vehicle measurement.

## Incremental interfaces

Retain `vehicle/interfaces.py`, `ai/interfaces.py` and provider adapters. Add
identity/session-store and consent repository boundaries without a second
reasoning engine. Phase 2 introduces scheduler/notification interfaces and a
deferred scan state; phase 3 licensed repair-provider/work-order interfaces;
phase 4 compatibility/price eligibility services, isolated from fault ranking.
See DEVELOPMENT_PLAN.md for dependencies and acceptance gates.

## New repository native milestone

The source and its existing foundation history were retained in NEW_AI_CAR_SCANER.
The user explicitly requested C++ for OBD connections; an opt-in TCP transport
now exists behind the shared interface. See native/obd/README.md and the current
implementation report. Diagnostic-core migration still requires profiling.
