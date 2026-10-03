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


def test_load_manifest_supports_comments_and_blank_lines(tmp_path: Path) -> None:
    manifest = tmp_path / "program-manifest.yaml"
    manifest.write_text(
        "# Program workspace manifest\n"
        "\n"
        "required_paths:\n"
        "  - docs/a.md\n"
        "  - docs/b.md\n",
        encoding="utf-8",
    )

    data = load_manifest(manifest)

    assert data["required_paths"] == ["docs/a.md", "docs/b.md"]


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


def test_program_manifest_tracks_wave0_foundation_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = (
        repo_root / "docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml"
    )

    data = load_manifest(manifest_path)

    expected_paths = [
        "docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md",
        "docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md",
        "docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md",
    ]

    assert all(path in data["required_paths"] for path in expected_paths)
