# Local test methodology

CTest runs a named C++ domain contract harness and Qt Test integration cases. Domain cases cover malformed/partial ISO-TP, service/PID validation, DTC deduplication, supported bitmap boundaries, unit reference values/round trips, all missing write prerequisites, scrypt, real signature tampering, strict versions, scan eligibility and evidence/test-result recalculation. Qt integration uses temporary SQLite and actual loopback sockets. HTTP smoke launches the compiled backend with temporary storage and checks owner isolation, settings, token revocation and restart persistence. UI self-test uses the compiled QML application with offscreen rendering and live locale/theme/unit changes.

source_contracts.py supplements runtime checks with domain dependency direction, no legacy/CI, catalog completeness, canonical icons and payment-disabled assertions. Build sanitize and coverage presets separately. Report measured core lines/branches separately from UI/service coverage. One CTest test binary may contain many cases; retain exact case counts rather than presenting binary counts as feature counts.

Physical adapters and authorized bench ECU tests are NOT RUN. Mobile/Windows packages, live PostgreSQL, external delivery/AI/update providers and production load tests remain separate gates. No simulator result is real-hardware PASS.
