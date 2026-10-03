from pathlib import Path

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
