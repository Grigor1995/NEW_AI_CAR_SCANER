# Cloud development workflow

Use /workspace/NEW_AI_CAR_SCANER, the existing isolated checkout. Do not create a Git worktree unless explicitly requested.
The .venv and .build-tools/obd are retained dependencies/output; processes must restart.
For local native-client development, launch from /workspace/NEW_AI_CAR_SCANER/finalbuild:
AI_CAR_BACKEND_HOST=127.0.0.1 AI_CAR_BACKEND_PORT=8001 AI_CAR_DISABLE_LLM_AUTOSTART=1 AI_CAR_ECOSYSTEM_ENABLED=0 PYTHONPATH=/workspace/NEW_AI_CAR_SCANER/.build-tools/obd ../.venv/bin/python -m apps.desktop.backend_worker
Keep this legacy API loopback-only. Do not enable ecosystem mode for the existing unauthenticated clients. No external LLM or physical device is required for deterministic/simulator development.
Verify GET /health returns status=ok; GET /api/v1/obd/plan has read_only=true and 010C in commands; GET /api/v1/vehicle-catalog/makes returns a nonempty list. Use local HTTP requests, not user-facing loopback preview links.
C++ is opt-in with native_tcp=true in an existing Wi-Fi connection config. Linux TCP/IPv4 only is validated; use original transports elsewhere. Physical hardware is untested.
For headless desktop validation: from finalbuild run QT_QPA_PLATFORM=offscreen ../.venv/bin/python scripts/run_desktop_tests.py. For GUI use an appropriate display and the existing apps.desktop.main launcher; do not replace UI/assets.
For account/consent validation, from finalbuild run ../.venv/bin/python scripts/check_ecosystem_smoke.py; it uses a temporary SQLite database, explicit migration and isolated local server. Do not apply migrations to an operator database without reviewing deployment instructions.
Shared suite: from repository root run QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.build-tools/obd" .venv/bin/python -m pytest finalbuild/tests -q.
See docs/IMPLEMENTATION_REPORT.md and native/obd/README.md for current evidence and limitations. Windows/iOS packaging, Android build, live PostgreSQL, external providers and real adapters have not been validated in this machine.

The complete installation commands are in `native/obd/cloud_setup.sh` and the
environment configuration draft. Configuration fields saved: `install_script`
and `start_skill`. Review and save the draft in environment settings, then
publish the environment to activate its snapshot. Draft saving does not itself
publish or prove fresh-task restoration.
