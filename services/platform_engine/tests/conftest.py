import os
import sys
from pathlib import Path

# Keep the default unit/regression suite isolated from developer databases.
# The API's persistence singleton initializes schema when DATABASE_URL is set,
# which can stall test collection if PostgreSQL is unavailable. Set
# AI_CAR_TEST_USE_DATABASE=1 explicitly when running DB-backed integration tests.
if os.getenv("AI_CAR_TEST_USE_DATABASE", "").strip().lower() not in {"1", "true", "yes"}:
    os.environ.pop("DATABASE_URL", None)

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for p in (BACKEND, ROOT):
    if str(p) not in sys.path:
        sys.path.append(str(p))
