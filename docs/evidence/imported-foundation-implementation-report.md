# Implementation report — first ecosystem foundation milestone

Branch: `feature/ecosystem-foundation-20261028`. Base: `a71c547`.
Date: 2026-10-28. `main` is not modified by this development branch.

## Completed scope

Phase 0 audit/baseline and the first Phase 1 backend slice are implemented.
This is not a claim that the entire ecosystem is production-ready.

- Existing native UI, icons, vehicle catalog, DiagnosticSession, OBD/telemetry,
  deterministic engine, local AI/RAG and test-result recalculation are retained.
- Added durable accounts with validated EN/HY/RU preferences, international phone
  format and IANA timezone. Contacts remain explicitly unverified; no provider
  delivery or ownership verification is fabricated.
- Added bounded-cost scrypt password hashes, random opaque bearer credentials
  stored only as SHA-256 hashes, expiry/logout and current-account checks.
- Defined exactly USER/CUSTOMER/ADMIN primary modes and separate MARKET portal
  role; validated mode selection from current DB assignments. No public ADMIN
  or MARKET self-grant endpoint exists. Self-service workshop registration is
  unverified and grants only CUSTOMER plus that center's owner membership.
- Added owned profiles reusing the existing vehicle_profiles payload and shared
  Vehicle model. Anonymous legacy rows are never assigned to a new account.
- Added current staff/CUSTOMER role checks, addressed invitations, explicit owner
  approval of per-vehicle read scopes/expiry, atomic invitation claiming and
  immediate checks for revoked/expired grants or inactive accounts/staff/centers.
  Owners see the business name and verification state before approval/revocation.
- Added scoped audit events, password-safe EN/HY/RU error envelopes and bounded
  in-process auth attempt throttles. This is not a distributed production limiter.
- Default feature flag is off. Enabled ecosystem mode denies legacy anonymous
  API bypasses and skips anonymous global-session cache load/persistence. Existing
  local clients retain API behavior with the flag off. Runner now binds loopback
  by default; physical-LAN development needs an explicit trusted-network override.
- Added explicit Alembic configuration and additive revision `0001_ecosystem`,
  with legacy-row retention, safe downgrade and namespace-limited autogeneration.
- Added locally bundled interactive architecture, ten selectable flows and
  matching Mermaid sources, typed API contracts and staged documentation.

## Schema and APIs

Nine new ecosystem tables: accounts, account_roles, auth_sessions,
service_centers, staff, vehicle_ownership, invitations, access_consents and
 audit_events. `vehicle_profiles` is referenced/reused and created with its old
schema only if absent. No old account, catalog or session data is rewritten.
Database engines use existing bounded connection behavior and are disposed by
the migration CLI. PostgreSQL offline DDL is review evidence only.

Implemented prefix `/api/v2/ecosystem`, 13 paths / 16 operations: register;
login/logout; get/update current profile; validate workspace; list/create owned
vehicles; list/create staff service centers; create/list/accept invitations;
list/revoke own grants; and consent-authorized shared vehicle read. Response
models exclude secrets; shared vehicle output also removes arbitrary metadata
and the owner's private nickname/contact information. Generated contract:
[ecosystem-openapi.json](architecture/ecosystem-openapi.json).

## Executed verification

| Check | Actual outcome |
|---|---|
| Common Python regression | 1001 passed, 2 skipped, 0 failed / errors; 50.07 s |
| Backend line coverage | 97.10% (5729/5900 statements) |
| Foundation suite | 34 passed, 0 failed; 24.29 s |
| Foundation line / branch / combined coverage | 99.62% / 94.44% / 99.00%; gate >=90% |
| Desktop logic / diagnostic E2E / negative / UI-POM / widgets | 216 / 6 / 68 / 142 / 25 passed; 1 platform skip |
| Desktop aggregate / production core | 90.43% / 90.84% |
| Android baseline | build/JVM/lint successful, 113 JVM cases; cached Gradle work explicitly present |
| SQLite Alembic | fresh + existing-row upgrade, repeat upgrade, downgrade preservation and safe autogeneration PASS |
| Real local HTTP/Uvicorn smoke | 10 checks PASS, including approval/revocation and restart persistence |
| Architecture browser | actual Chromium PASS: 10 views, 22 nodes, search/filter/collapse, component/edge details, zoom, real pointer pan/wheel, theme and narrow layout |
| PostgreSQL offline SQL | generated successfully; no live PostgreSQL migration or race test claimed |
| Static checks | Ruff F401/F811/F821/F841, JS syntax and Git whitespace checks passed |
| Physical OBD / external providers | NOT EXECUTED / NOT CONFIGURED |
| iOS / Windows packaging execution | BLOCKED on this Linux host |
| C++ tests/coverage | NOT APPLICABLE; no C++ implementation |

Do not sum overlapping test selections as unique cases. The full executable
report is [final-qa.json](evidence/final-qa.json); coverage and raw statement/
branch locations are in [foundation-coverage.json](evidence/foundation-coverage.json).
The original audit baseline remains separate in [BASELINE_QA_REPORT.md](BASELINE_QA_REPORT.md).

### Deterministic performance (isolated fixture)

```text
PERF deterministic_analysis_ms p50=0.52 p95=1.11 min=0.44 max=2.72
.....
5 passed in 0.19s
```

This measures local fixture copy + deterministic reasoning, excluding physical
OBD polling, network and LLM inference. UI startup/navigation, memory pressure
and actual protocol latency were not measured. It does not justify a C++ rewrite
or imply a vehicle/hardware SLA.

## Changed files and reusable artifacts

New source: `backend/ecosystem` models/security/schemas/service/API/error/migration
policy modules; Alembic env/revision/config; foundation API/migration tests;
local HTTP/browser QA and OpenAPI/Mermaid exporters. Modified integration points:
`backend/api/main.py`, dependency files, global JSON defaults, runner bind default
and its test/guide. Native UI/icon/transport/diagnostic-engine files are unchanged.

All new/modified paths relative to base are recorded in
[changed-files.json](evidence/changed-files.json). The required 25 root technical
Markdown documents, architecture assets and evidence live under `docs/`.

## Remaining work and release gates

1. Milestone 1B: authenticated scoped adapters to existing diagnostic sessions,
   hardware/devices, telemetry, tests, knowledge and reports; explicit legacy
   ownership import and controlled operator/staff/admin provisioning. Existing
   malformed legacy vehicle-body validation is an audited hardening task.
2. Milestone 1C: current-themed native login/workspace/profile and consent UI,
   secure token storage and full EN/HY/RU client parity. Do not enable ecosystem
   mode for existing unauthenticated native clients before this migration.
3. Phases 2–5: verified contacts, scheduler/availability/deferred scans,
   consented provider delivery, service discovery, licensed repair/wiring,
   work orders, merchant products/fitment/discounts and real admin analytics.
4. Phases 6–7: real PostgreSQL concurrency/backup tests, hardware validation,
   native releases, measured sync/optimization, MFA/recovery, distributed abuse
   controls, retention/export/deletion, operational hardening and security review.

Business verification is not implemented; invitation creation alone grants no
access. Future administrative suspension must deactivate the relevant account,
center/staff membership or grant; CUSTOMER is also a self-service workspace role.
No paid placement influences diagnostic ranking. No SMS/email is sent, ECU
write executed, CI/CD introduced, deployment performed or production readiness
claimed by this milestone.
