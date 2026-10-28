# Deployment and operations

Current supported execution evidence is a Linux development build. Backend is loopback-only; run build/dev/cda_backend --database local/backend.sqlite --port 8081. The UI uses a separate local app-data SQLite file and does not automatically connect to this backend. Never expose this local identity host publicly without TLS, operational limits, security review and remote authentication design. No CI/CD, deployment automation or store upload exists.

Back up SQLite with supported live-backup tooling and verify restore offline before migration. Version 1 rejects newer schemas; do not assume arbitrary database rollback. Signed platform release packaging, PostgreSQL, cross-device sync, trusted signing keys, update endpoints and real-hardware acceptance are pending. Build/SDK instructions are in BUILD_AND_RUN.md and apps/*/README.md.
