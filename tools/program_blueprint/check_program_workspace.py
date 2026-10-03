from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("required_paths", [])
    return data


def find_missing_paths(root: Path, required_paths: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for rel_path in required_paths:
        if not (root / rel_path).exists():
            missing.append(rel_path)
    return missing


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml"
    manifest = load_manifest(manifest_path)
    missing = find_missing_paths(repo_root, manifest["required_paths"])
    if missing:
        print("Missing required program files:")
        for path in missing:
            print(f"- {path}")
        return 1
    print("Program workspace is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
