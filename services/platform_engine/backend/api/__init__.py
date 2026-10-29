"""Load shared environment defaults before API modules initialize services."""
from pathlib import Path
import sys

_project = str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])))
if _project not in sys.path:
    sys.path.append(_project)
from shared.environment import apply_environment  # noqa: E402

apply_environment()
