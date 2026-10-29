"""Run source-compatible API on loopback; requires platform-engine dependencies."""
from pathlib import Path
import argparse
import os
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8001)
parser.add_argument('--ecosystem', action='store_true', help='Enable migrated consent/ownership APIs on a separate database')
parser.add_argument('--ephemeral', action='store_true', help='Do not set a default SQLite database')
args = parser.parse_args()
if not 1 <= args.port <= 65535:
    parser.error('Port must be 1..65535')
engine = root / 'services/platform_engine'
local = root / 'local'
local.mkdir(exist_ok=True)
if not args.ephemeral:
    filename = 'platform-ecosystem.sqlite' if args.ecosystem else 'platform-engine.sqlite'
    os.environ.setdefault('DATABASE_URL', 'sqlite:///' + (local / filename).as_posix())
os.chdir(engine)
sys.path[:0] = [str(engine), str(engine / 'backend')]
if args.ecosystem:
    os.environ['AI_CAR_ECOSYSTEM_ENABLED'] = '1'
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(engine / 'backend/alembic.ini')), 'head')
import uvicorn
uvicorn.run('app:app', host='127.0.0.1', port=args.port, access_log=False)
