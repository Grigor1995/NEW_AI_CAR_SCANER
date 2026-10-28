# V3 phased development plan

Estimates are engineering effort ranges for an experienced small team, not dates
or completion claims. Every milestone must leave a locally buildable/testable
repository. No CI/CD or payment processing is in scope.

| Phase | Scope / deliverable and source boundary | Dependencies and API/schema work | Acceptance and validation | Status / effort |
|---|---|---|---|---|
| 0 safe reset | Verify NEW_AI_CAR_SCANER, archive original, preserve .git/history, remove legacy source/workflows, new CMake structure | verified archive/bundle and recoverable Git ref | original retrievable; no finalbuild/native/Python application runtime | IMPLEMENTED; hours |
| 1 architecture/UI | C++ contracts, domain/service separation, Qt/QML NEO theme, canonical native icons, 24-view dashboard, docs | Qt6.8/OpenSSL/CMake; no new remote services | actual Linux build, translated UI pages, responsive render, browser interactions, source boundary tests | IMPLEMENTED foundation; full product UI remains phased; 1–2 weeks total |
| 2 identity/storage | Durable local accounts, roles, scoped vehicles/settings; then verified contact, workshop sharing, PostgreSQL/remote sync | schema1 implemented; consent/organization/PostgreSQL migrations and scoped versioned APIs proposed | credentials/expiry/revocation/isolation/restart tests now; grant expiry/races/live PG before completion | PARTIAL; 2–4 weeks |
| 3 diagnostic core | TCP/desktop serial, strict ELM/CAN/ISO-TP read slice, write safety policy; then broader read/UDS and bound executor | actual adapters, verified profiles, bench ECUs, mobile drivers; remote diagnostic APIs not yet exposed | malformed/timeout/bitmap/negative safety tests now; hardware/protocol matrix and one-use audited write executor required | PARTIAL; 3–6 weeks + hardware |
| 4 USER | Current owner profiles/live reads/rules/JSON reports; then schedules, contact alerts, services/repair/history | phases2/3, verified providers; scan-run/outbox/history schema and APIs proposed | no unavailable scan success, consented delivery, DST/quiet-hours/idempotency and owner E2Es | PARTIAL; 2–4 weeks |
| 5 CUSTOMER | Workshop/staff, invitations/vehicle grants, work orders, licensed diagrams, test plans and PDFs | phase2 explicit owner scopes, licensed repair sources; org/consent/work-order migrations proposed | grant approval/revoke/race denial; professional E2Es; licensed applicability | PLANNED; 3–5 weeks |
| 6 MARKET | Merchant approval, listings, inventory, verified fitment, discounts, quotes; no payments | protected provisioning, verified catalogs; merchant/product/fitment/offer APIs/schema proposed | eligibility and stock concurrency, unknown fitment explicit, no paid diagnostic ranking | PLANNED; 2–4 weeks |
| 7 ADMIN | Account/business moderation, controlled configuration, real metrics, audit and release management | granular auth/MFA + real activity; privileged APIs/schema proposed | no self-grant, no implicit private vehicle bypass, real aggregates/audit | PLANNED; 2–4 weeks |
| 8 settings | Current four locales/units/themes/persistence; then all notification/AI/device/privacy/update preferences and sync | native lifecycle + identity/provider domains; conflict/version metadata proposed | current catalog/runtime/round-trip tests; full locale layout, secure sync/conflict E2Es | PARTIAL; 1–3 weeks |
| 9 updates | Version/signature primitives now; pinned signed feeds, package verification/staging, platform delivery/history later | signing authority, stores/installer/SDKs; release manifests and version APIs proposed | corrupted/signature/rollback/incompatible/interrupted-install/storage tests; signed native artifacts | PARTIAL; 2–4 weeks |
| 10 AI | Current deterministic evidence/test-result slice; then structured providers, RAG/ML/reference retrieval | licensed evidence/data + configured models; hypothesis/test-result persistence/API proposed | schema/provenance checks, no invented values, held-out diagnostics and recalculation, offline fallback | PARTIAL; 3–6 weeks |
| 11 native validation | Separate Windows/Android/iOS builds, permissions/lifecycle, offline sync, accessibility and performance | Qt/OpenSSL native kits, Xcode/signing/Android SDK, actual devices | real native packages, hardware evidence, latency/memory/battery and UI parity; Linux alone is insufficient | BLOCKED native SDK/hardware; 2–5 weeks |
| 12 final QA/release | Full workflow/security/load/regression/hardware/restore acceptance, complete current docs | all preceding acceptance and external prerequisites | production security review, verified backups, signed release and rollback, no unknown critical failures | PLANNED; 2–4 weeks |

## Immediate next executable milestones

1. Split remaining owner-profile persistence into a small vehicle repository
   contract; add explicit workshop organization/owner-consent grants and tests
   before exposing any shared data. Introduce reviewed PostgreSQL migrations.
2. Extend the new protocol core with request-bound VIN/readiness/freeze-frame
   APIs and recorded-capability checks; add serialized adapter recovery and
   hardware capture validation. Do not enable write execution on unverified ECUs.
3. Implement a one-use prepare/confirm/execute/verify/audit coordinator using
   trusted operation profiles and authorized bench fixtures, then certify an
   exact adapter/vehicle workflow before actual writes.
4. Implement notification/scheduler and update delivery domains only after their
   external trust/configuration requirements are available. Keep payment code absent.

Current phase evidence and remaining gates are in IMPLEMENTATION_REPORT.md.
