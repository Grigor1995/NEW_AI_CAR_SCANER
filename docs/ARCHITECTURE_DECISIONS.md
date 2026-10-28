# Architecture decisions

| ADR | Decision | Reason / consequence |
|---|---|---|
| 001 | Retain Python, Kotlin, Swift and PySide6 | Existing proven clients and p95 deterministic baseline below 90 ms; no whole-language rewrite |
| 002 | One DiagnosticSession and evidence engine | Keep backend models and test-result recalculation; new account layer must call existing services |
| 003 | Separate primary modes and workshop staff roles | USER/CUSTOMER/ADMIN differ from owner/admin/technician/viewer; MARKET stays a portal role |
| 004 | Feature-gated v2 boundary | Default local clients continue working; enabled ecosystem blocks legacy API bypasses until authenticated native clients migrate |
| 005 | Durable opaque bearer sessions | Random 256-bit credentials stored only as SHA-256 hashes; role/status/expiry resolved from DB, immediate logout/account revocation; legacy JWT helper remains for old tests, not reused as public auth |
| 006 | Scrypt N=32768, r=8, p=3 using stdlib | No plaintext or reversible passwords; bounded input, random salt, constant-time comparison; measure auth separately from diagnostic p95 |
| 007 | Additive Alembic migrations | Existing SQL bootstrap has no versioned migration setup; preserve anonymous data without inventing owners |
| 008 | Explicit owner consent, read-only by default | Invitations are not access; grants are per vehicle, scope and expiry; check DB on every read |
| 009 | Default read-only hardware | Existing protocol/capability checks retained; no LLM-to-unrestricted ECU command path |
| 010 | Real provider availability | Do not send SMS/email or claim verification without configured providers; queue/defer future scans when ignition/device/OS conditions prevent execution |
| 011 | Keep UI/assets unchanged in foundation | Account workspace UI is a separate native milestone, using current icons/colors and EN/HY/RU resources |
| 012 | No CI/CD | Local tests/builds only, following the existing user constraint |

Opaque sessions complement the existing `security` package; they do not change
legacy token behavior silently. Production MFA, recovery, distributed throttles,
retention jobs, transport TLS and security review remain explicit release gates.

## ADR: Optional native TCP boundary

User requires C++ for OBD connections. Add an explicit opt-in transport behind
DiagnosticTransport; retain shared Python protocol/diagnostic logic and default
transport. C++20/pybind11 is used for the current desktop/backend bridge. Linux
loopback is validated; POSIX-only code must not be presented as Windows/mobile
compatibility. No acceleration claim is made without comparison measurements.
