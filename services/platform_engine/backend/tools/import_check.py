from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Absolute package roots owned by this backend.
INTERNAL_ROOTS = {
    "acquisition", "ai", "api", "device", "diagnostic", "multi_ecu",
    "network_discovery", "observability", "platform", "professional_platform",
    "obd", "catalog_sources", "security", "simulator", "telemetry", "vehicle", "vehicle_diagnostic",
}

def module_exists(module: str) -> bool:
    parts = module.split(".")
    base = ROOT.joinpath(*parts)
    if parts[0] == "vehicle" and len(parts) > 1:
        canonical = ROOT.parent.joinpath(*parts)
        if canonical.with_suffix(".py").is_file() or (canonical / "__init__.py").is_file():
            return True
    return base.with_suffix(".py").is_file() or (base / "__init__.py").is_file()

def check() -> list[str]:
    errors: list[str] = []
    for path in ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path}: syntax error: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                root = name.split(".", 1)[0]
                if root in INTERNAL_ROOTS and not module_exists(name):
                    errors.append(f"{path}: missing internal module '{name}'")
    return errors

if __name__ == "__main__":
    errors = check()
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("Internal import graph: OK")
