from __future__ import annotations

"""Client-independent global diagnostic data.

The backend owns canonical data. Desktop, Android, web and tests consume the
same repository/API contract and never own a second copy of diagnostic cases.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "global"


@dataclass(frozen=True)
class GlobalDataSnapshot:
    version: str
    vehicles: list[dict]
    diagnostic_cases: list[dict]

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "vehicles": deepcopy(self.vehicles),
            "diagnostic_cases": deepcopy(self.diagnostic_cases),
        }


class GlobalDataStore:
    def __init__(self, root: Path = DATA_ROOT):
        self.root = root

    def _read(self, name: str, default):
        path = self.root / name
        if not path.exists():
            return deepcopy(default)
        return json.loads(path.read_text(encoding="utf-8"))

    def snapshot(self) -> GlobalDataSnapshot:
        manifest = self._read("manifest.json", {"version": "0.1.0"})
        return GlobalDataSnapshot(
            version=str(manifest.get("version", "0.1.0")),
            vehicles=self._read("vehicles.json", []),
            diagnostic_cases=self._read("diagnostic_cases.json", []),
        )

    def case(self, case_id: str) -> dict | None:
        return next(
            (case for case in self.snapshot().diagnostic_cases
             if case.get("case_id") == case_id),
            None,
        )


global_data = GlobalDataStore()
