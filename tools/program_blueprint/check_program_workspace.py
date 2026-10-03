from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable


def load_manifest(path: Path) -> dict:
    data: dict[str, object] = {}
    current_list_key: str | None = None
    manifest_lines = path.read_text(encoding="utf-8").splitlines()
    for lineno, raw_line in enumerate(manifest_lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indented = raw_line.lstrip()
        indent = len(raw_line) - len(indented)

        if indented.startswith("- "):
            if current_list_key is None or indent == 0:
                raise ValueError(
                    f"Manifest {path} must contain a mapping at the YAML root."
                )
            list_value = data.setdefault(current_list_key, [])
            if not isinstance(list_value, list):
                raise ValueError(
                    f"Manifest {path} line {lineno} has an invalid list item."
                )
            item = indented[2:].strip()
            if not item:
                raise ValueError(
                    f"Manifest {path} line {lineno} contains an empty list item."
                )
            list_value.append(item)
            continue

        if indent != 0:
            raise ValueError(
                f"Manifest {path} line {lineno} has unsupported indentation."
            )

        key, separator, remainder = stripped.partition(":")
        if not separator or not key.strip():
            raise ValueError(
                f"Manifest {path} line {lineno} is not valid manifest syntax."
            )

        key = key.strip()
        remainder = remainder.strip()
        if remainder:
            data[key] = remainder
            current_list_key = None
        else:
            data[key] = []
            current_list_key = key

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
