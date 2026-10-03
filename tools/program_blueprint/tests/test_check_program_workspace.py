from pathlib import Path

import pytest

from tools.program_blueprint.check_program_workspace import (
    find_missing_paths,
    load_manifest,
)


def test_find_missing_paths_reports_absent_files(tmp_path: Path) -> None:
    manifest = tmp_path / "program-manifest.yaml"
    manifest.write_text(
        "required_paths:\n"
        "  - docs/a.md\n"
        "  - docs/b.md\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# A\n", encoding="utf-8")

    data = load_manifest(manifest)
    missing = find_missing_paths(tmp_path, data["required_paths"])

    assert missing == ["docs/b.md"]


def test_load_manifest_rejects_non_mapping_root(tmp_path: Path) -> None:
    manifest = tmp_path / "program-manifest.yaml"
    manifest.write_text("- docs/a.md\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a mapping"):
        load_manifest(manifest)


def test_load_manifest_rejects_invalid_required_paths_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "program-manifest.yaml"
    manifest.write_text("required_paths: docs/a.md\n", encoding="utf-8")

    with pytest.raises(ValueError, match="required_paths"):
        load_manifest(manifest)


def test_find_missing_paths_rejects_absolute_required_paths(tmp_path: Path) -> None:
    absolute_path = str(tmp_path / "docs" / "a.md")

    with pytest.raises(ValueError, match="repo-relative"):
        find_missing_paths(tmp_path, [absolute_path])


def test_find_missing_paths_rejects_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repo root"):
        find_missing_paths(tmp_path, ["../outside.md"])
