# V3 implementation report — new C++/Qt foundation

Date: 2026-10-28. Repository: Grigor1995/NEW_AI_CAR_SCANER.
This is a tested development milestone, not completion of the production product.

## Safe reset and preservation

V3 explicitly replaces the preceding reuse requirement. Confirmed the Git root
and origin, verified a clean starting tree at ac8d9469279a52bdb53b7cf7405bda67f7e6fdc6,
created archive/pre-v3-ac8d946, verified a complete Git bundle, made a source tar
archive and retained the entire previous working tree under /workspace/backups.
.git and history remain intact. Old application code, assets, dependencies and
workflows were removed from the active tree. New C++/QML source and artwork were
written independently; previous application modules were not reused.

Verified local recovery files:

- /workspace/backups/NEW_AI_CAR_SCANER-pre-v3.bundle (git bundle verify passed)
- /workspace/backups/NEW_AI_CAR_SCANER-pre-v3.tar
- /workspace/backups/pre-v3-checkout (all previous checkout files, including local tools)

Bundle SHA-256: 08050cdce85cb83b59ee14b6ea8d1e800bda11d8ebd4fa9c68ff52d279827d3f.
Source-tar SHA-256: 469a7f98d95d7766c5e9d30b4b81385a1c29d2d6aaea8488dda129f32b8e68bc.
Archives are outside the active checkout; the Git archive branch is the portable
history recovery point. Old binaries are not presented as V3 builds.

The complete changed/created/removed path inventory is
[testing/changed-files.json](testing/changed-files.json); the new runtime source
is in apps/shared, core, services, backend and ui.

## Implemented source and behavior

- New CMake/C++20 structure; separate cda_core, cda_services, car_diagnostic and
  cda_backend targets. Domain algorithms have no Qt UI/database dependencies.
- Original NEO AUTOMOTIVE Qt/QML foundation with top navigation, responsive cards,
  account dialogs, private vehicle entry, actual adapter reads, metric cards,
  bounded measured-sample traces, conservative rule guidance, JSON export and
  persistent settings. Unimplemented sections explicitly say so.
- One canonical car/circuit/waveform SVG; Qt-rendered PNG previews, Windows ICO,
  Android adaptive/legacy icons and iOS icon assets derived from that artwork.
- Local SQLite accounts with salted OpenSSL scrypt, secure random one-hour
  bearer credentials stored as hashes, active-account/expiry/logout checks,
  private vehicle scope, whitelisted preferences and initial audit records.
- Exactly USER/CUSTOMER/ADMIN primary role values, MARKET separately assigned;
  USER-only public registration and explicit local-operator role provisioning.
  CUSTOMER/ADMIN/MARKET business workflows remain unimplemented.
- Real asynchronous C++ Qt TCP and desktop serial source; initialization,
  supported-PID bitmap, only eligible RPM/speed/coolant polling and stored DTCs.
  Strict ELM/header/CAN/ISO-TP parsing, invalid/unavailable/unsupported/stale states,
  native units, UTC timestamps and provenance. No generated live sensor data.
- Transport read allowlist, independent central write-policy validation with
  negative checks for every prerequisite. No ECU write executor is exposed.
- Deterministic P0302 evidence and test-result recalculation slice, including a
  synthetic W211 E350 M272 petrol-normal/LPG-misfire regression fixture.
- Pure unit conversions and real Ed25519 signature/version primitives.
  These are not a complete online updater or provider-backed AI engine.
- Four Qt translation catalogs (EN/HY/RU/FR), runtime language changes, locale
  numeric formatting, dark/light/system themes and metric/imperial presentation.
- New bundled interactive architecture with 24 sections/30 components, inspector,
  relationship details, filtering, search, collapse, mouse pan/wheel zoom, theme,
  responsive layout and actual same-origin health observations. Unknown process,
  hardware/provider/production metrics stay UNKNOWN/UNAVAILABLE.
- Required technical documents, phased roadmap, OpenAPI and maintainable Mermaid
  architecture/flow/sequence/entity/safety/deployment sources. No CI/CD or active
  payment code exists.

## Local validation and scope

The machine-readable current results are in [testing/current-results.json](testing/current-results.json).

| Check | Observed outcome |
|---|---|
| Linux GCC14.2 / Qt6.8.2 build | Core, Qt services, QML client and C++ HTTP host compile |
| C++ domain contracts | 19 named cases passed, 0 failed |
| Qt integration | 4 functional cases plus init/cleanup passed (6 Qt Test entries), 0 failed |
| CTest | 2 test executables passed; do not mistake this for two assertions |
| HTTP smoke | 12 checks passed against actual compiled host and temporary SQLite |
| UI self-test | 13 pages, 4 runtime locales, 3 themes, 2 unit systems and narrow rendering passed |
| Source/catalog contracts | matching completed catalogs, no domain UI dependency/legacy/CI/payment code passed |
| Architecture Chromium | 13 interaction/observation checks passed; direct file:// navigation BLOCKED by managed browser policy |
| ASan + UBSan | domain contracts passed with leak detection enabled |
| Pure domain line coverage | 95.07% (289/304 executable lines) |
| Pure domain GCC branches | 500/722 taken (69.25%, includes exception branches) |
| Qt service/UI/HTTP coverage | NOT MEASURED; do not apply domain coverage to these modules |
| Formatting/compiler/whitespace | current sources checked locally; details in evidence |
| Physical OBD/bench ECU | NOT RUN; loopback is not hardware certification |
| Windows / Android / iOS native releases | NOT RUN / BLOCKED on native SDK/signing/hardware validation |
| PostgreSQL, external providers, signed installers | NOT RUN / NOT CONFIGURED |

Protocol benchmark: 10,000 fixed framed-RPM decodes in the Linux Debug build,
p50 7.582 us, p95 8.823 us, p99 59.918 us in the recorded run. It excludes hardware,
network, LLM and UI work; it is not an acceleration comparison or a vehicle SLA.
See testing/protocol-performance.json for the current measured run.

The dashboard's local HTTP interactions and real backend health checks passed.
This managed Chromium rejects file:// with ERR_BLOCKED_BY_ADMINISTRATOR. That
policy was not bypassed and direct file loading is not reported as PASS. Assets
are bundled locally; no CDN is used.

## API / schema

The new local C++ API is /api/v1 with registration, login/logout, current account,
owner-scoped vehicles, preferences, health and implementation capabilities.
See api/openapi.json. It replaces, rather than preserves compatibility with, old
Python API contracts; old clients are not used by V3. Local schema version 1
covers accounts/roles/tokens/vehicles/settings/audit and rejects unknown newer
schema versions. No PostgreSQL migration or backend-client synchronization exists.

The GUI currently uses its own local account database. The standalone host uses
an explicitly selected separate SQLite file. These are not a synchronized remote
identity system. Local operator CLI role provisioning requires filesystem trust.

## Security findings and remaining gates

The backend is loopback-only with a coarse local auth throttle and bounded JSON
validation; public TLS, MFA/recovery, distributed rate limiting, full lifecycle
privacy/export/delete, sharing consent, detailed privileged audit, load and
penetration testing remain required. Desktop token expiry is rechecked on
commands and periodically; tokens are not persisted in plaintext settings.

Actual writes remain LOCKED: operation-specific verified vehicle/ECU/adapter
profiles, trusted live prerequisites, one-use confirmation, durable staged
execution/audit and authorized bench verification do not exist. The safety
predicate alone must never be used as a hardware trust source. No arbitrary UDS,
security bypass, coding/flashing or scheduled write is implemented.

## Phase status and outstanding work

Phase 0 and the architecture/UI foundation are implemented within the scope
above. Identity/storage, OBD reads, settings, rules and update primitives are
partial slices of later phases. This does NOT complete all three business modes
or the requested ecosystem.

Next work: workshop organizations and explicit owner consent; PostgreSQL and
remote sync; broader capability-bound read operations and hardware recovery;
qualified bench write executor; real scheduler/notifications; licensed diagrams
and repair references; merchant listing/fitment/discount domains; admin workflows;
full LLM/RAG; signed update distribution; native platform builds; production QA.
Payment processing stays strictly deferred. See DEVELOPMENT_PLAN.md for explicit
phase dependencies, APIs/migrations, deliverables and acceptance criteria.

## Reproducible cloud configuration

The saved environment draft now contains the new install_script and start_skill;
old Python/finalbuild startup paths were replaced. scripts/build/cloud_setup.sh
contains the complete setup commands. Dependencies/build output persist; live
processes must restart. Review/save the draft in environment settings and publish
the environment to activate its snapshot. A saved draft is not publication or
proof of restoration in a new task.
