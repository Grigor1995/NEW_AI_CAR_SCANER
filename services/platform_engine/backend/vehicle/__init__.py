"""Compatibility import shim to one canonical vehicle-core implementation.

The authoritative shared Python vehicle core is finalbuild/vehicle/ and is
used by FastAPI. This prevents backend/vehicle stub modules from shadowing real
ELM327/UDS/J2534 modules when PYTHONPATH order changes at startup.
"""
from pathlib import Path

_SHARED_CORE = Path(__file__).resolve().parents[2] / "vehicle"
# Source tree resolves as a normal directory. PyInstaller may package these
# modules inside PYZ without extracting their source directories, so do NOT
# fail solely because the runtime __file__ parent is not a real directory.
if __name__ == "vehicle":
    __path__ = [str(_SHARED_CORE)]
from .interfaces import *  # noqa: F401,F403
