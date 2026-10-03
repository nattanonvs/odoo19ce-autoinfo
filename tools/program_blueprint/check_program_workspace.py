from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable

import yaml


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(
            f"Manifest {path} must contain a mapping at the YAML root."
        )
    required_paths = data.get("required_paths", [])
    if not isinstance(required_paths, list) or any(
        not isinstance(rel_path, str) for rel_path in required_paths
    ):
        raise ValueError(
            f"Manifest {path} field 'required_paths' must be a list of path strings."
        )
    data["required_paths"] = required_paths
    return data


def _validate_required_path(root: Path, rel_path: str) -> Path:
    repo_root = root.resolve()
    normalized_path = rel_path.replace("\\", "/")
    if (
        Path(rel_path).is_absolute()
        or PurePosixPath(normalized_path).is_absolute()
        or PureWindowsPath(rel_path).is_absolute()
    ):
        raise ValueError(f"Required path must be repo-relative: {rel_path}")
    if ".." in PurePosixPath(normalized_path).parts:
        raise ValueError(f"Required path must stay within the repo root: {rel_path}")
    candidate = (repo_root / rel_path).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(
            f"Required path must stay within the repo root: {rel_path}"
        ) from exc
    return candidate


def find_missing_paths(root: Path, required_paths: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for rel_path in required_paths:
        candidate = _validate_required_path(root, rel_path)
        if not candidate.exists():
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
