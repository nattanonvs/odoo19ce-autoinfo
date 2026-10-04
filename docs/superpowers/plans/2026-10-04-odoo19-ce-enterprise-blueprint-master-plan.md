# Odoo 19 CE Enterprise Blueprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved enterprise blueprint into an executable delivery program with validated workspace structure, discovery artifacts, governance documents, and wave-based child specs before any business-domain build starts.

**Architecture:** This is a master orchestration plan, not a direct business-module implementation plan. It creates the durable program workspace, validates required artifacts with a lightweight checker, captures current-state discovery from Odoo 15 CE, and prepares domain-level specs and review gates so later build plans can stay modular, upgrade-safe, and OCA-first.

**Tech Stack:** Markdown, YAML, Python 3, pytest, git, Odoo 19 CE repository docs structure

---

## Scope Guard

This blueprint covers multiple independent subsystems across the whole company. Do **not** try to implement business modules from this master plan. This plan only creates the execution system for the program:

- program workspace
- discovery pack
- engineering/governance documents
- wave backlog
- child domain spec templates

Every business domain in later waves must get its own spec and its own implementation plan.

### Task 1: Create Program Workspace Validator

**Files:**
- Create: `tools/program_blueprint/check_program_workspace.py`
- Create: `tools/program_blueprint/tests/test_check_program_workspace.py`
- Create: `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from tools.program_blueprint.check_program_workspace import load_manifest, find_missing_paths


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tools/program_blueprint/tests/test_check_program_workspace.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing symbol errors because the validator file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `tools/program_blueprint/check_program_workspace.py` with:

```python
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
```

Create `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml` with:

```yaml
required_paths:
  - docs/superpowers/programs/odoo19-enterprise/README.md
  - docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md
  - docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md
  - docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md
  - docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md
  - docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md
  - docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tools/program_blueprint/tests/test_check_program_workspace.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/program_blueprint/check_program_workspace.py tools/program_blueprint/tests/test_check_program_workspace.py docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml
git commit -m "chore: add program workspace validator"
```

### Task 2: Create Program Workspace Index

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/README.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml`

- [ ] **Step 1: Write the document**

Create `docs/superpowers/programs/odoo19-enterprise/README.md` with:

```markdown
# Odoo 19 CE Enterprise Program Workspace

This directory contains the executable planning workspace for the company-wide Odoo 19 CE rebuild program.

## Purpose

- Keep all program-level artifacts in one place
- Separate blueprint/governance from domain implementation
- Track discovery, standards, backlog, and review gates

## Subdirectories

- `discovery/` - evidence from Odoo 15 CE
- `foundation/` - engineering and platform rules
- `governance/` - gates, decision records, operating model
- `backlog/` - wave sequencing and domain spec index

## Working Rules

1. No domain build starts without an approved domain spec.
2. Standard Odoo and OCA options are evaluated before custom build.
3. No direct Odoo core modifications are allowed.
4. Every artifact in this workspace must be reviewable and versioned.
```

- [ ] **Step 2: Run validator to verify it still fails for the remaining missing files**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected: FAIL and print the remaining missing files, but **not** `docs/superpowers/programs/odoo19-enterprise/README.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/programs/odoo19-enterprise/README.md
git commit -m "docs: add enterprise program workspace index"
```

### Task 3: Create Discovery Pack Documents

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md`

- [ ] **Step 1: Write the current-state inventory**

Create `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md` with:

```markdown
# Current-State Inventory

## Objective

Capture the minimum evidence required from Odoo 15 CE before redesign decisions are locked in.

## Required Sections

### System Facts
- Odoo edition and version
- Companies in scope
- Admin access status
- Developer mode status

### Custom Landscape
- Custom modules by namespace
- Custom models by namespace
- Menu-to-action-to-model map
- Automated actions, server actions, scheduled actions

### Domain Inventory
- Finance
- Sales
- Service
- Logistics
- HR and operations

### Reports and Owner Information Needs
- Operational reports in use
- Management reports in use
- KPI expectations
- Alerts/signals needed by owner

### Data Conditions
- Master data health
- Duplicate patterns
- Orphaned records
- Archival and migration decisions
```

- [ ] **Step 2: Write the access readiness checklist**

Create `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md` with:

```markdown
# Access and Readiness Checklist

## Application Access
- [ ] Odoo 15 admin access confirmed
- [ ] Developer mode access confirmed
- [ ] Technical menu access confirmed

## Infrastructure Access
- [ ] Read-only production access approved
- [ ] Clone or staging shell access approved
- [ ] Odoo configuration files available
- [ ] Addon paths available

## Data Access
- [ ] Full database dump provided
- [ ] Sanitized copy provided
- [ ] Master data extraction approved

## Source and Integration Access
- [ ] Custom addon repositories available
- [ ] Deployment scripts available
- [ ] Integration inventory available
- [ ] Test credentials available where needed
```

- [ ] **Step 3: Run validator to verify it still fails only for later workspace files**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected: FAIL and list only the remaining missing foundation/governance/backlog files.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md
git commit -m "docs: add discovery pack templates"
```

### Task 4: Create Foundation and Governance Documents

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md`

- [ ] **Step 1: Write the engineering standards summary**

Create `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md` with:

```markdown
# Engineering Standards

## Core Rules
- No direct Odoo core modifications
- OCA first, custom second
- One bounded responsibility per addon
- Install, upgrade, and uninstall safety required

## Code Rules
- Readable names
- Small focused methods
- Explicit security model
- Test coverage for critical business logic

## Required Checks
- Lint
- Tests
- Module dependency review
- Upgrade note
- Security review
```

- [ ] **Step 2: Write the review gates document**

Create `docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md` with:

```markdown
# Review Gates

## Gate 1: Discovery Approved
- Current-state inventory reviewed
- Access checklist completed
- Custom map reviewed

## Gate 2: Blueprint Approved
- Architecture approved
- OCA policy approved
- Engineering rules approved

## Gate 3: Domain Spec Approved
- Future-state process approved
- Reporting impact reviewed
- Migration assumptions reviewed

## Gate 4: Build Approved
- Code reviewed
- Tests passed
- Install/uninstall checks passed

## Gate 5: Parallel Run Approved
- Process reconciliation passed
- Report reconciliation passed
- Training package ready
```

- [ ] **Step 3: Run validator to verify only backlog files remain missing**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected: FAIL and list only:

```text
- docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md
- docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md
git commit -m "docs: add foundation and governance guides"
```

### Task 5: Create Backlog and Domain Spec Index

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

- [ ] **Step 1: Write the wave matrix**

Create `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` with:

```markdown
# Domain Wave Matrix

## Wave 0
- Foundation platform
- Governance
- KPI and reporting baseline

## Wave 1
- Contacts
- Sales
- Purchase
- Inventory
- Accounting

## Wave 2
- Advance
- Cheque
- Money In Analysis

## Wave 3
- Sales Services
- Claims
- Warranty
- Service Card
- Product Return

## Wave 4
- Stock Requests
- Transportation
- Logistics extensions

## Wave 5
- Employees
- Attendances
- Time Off
```

- [ ] **Step 2: Write the domain spec index**

Create `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` with:

```markdown
# Domain Spec Index

## Required Child Specs

- [ ] Wave 1 - Commercial and financial core
- [ ] Wave 2 - Custom finance controls
- [ ] Wave 3 - Sales Services and after-sales
- [ ] Wave 4 - Logistics extensions
- [ ] Wave 5 - HR and operational enablement

## Required Fields Per Child Spec

- Scope
- Current-state summary
- Keep/refactor/replace/retire decisions
- Future-state process
- Reporting and KPI needs
- Security and approval model
- Migration assumptions
- Training impact
```

- [ ] **Step 3: Run validator to verify the workspace is complete**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected:

```text
Program workspace is complete.
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
git commit -m "docs: add enterprise wave backlog"
```

### Task 6: Verify, Review, and Handoff

**Files:**
- Modify: `docs/superpowers/programs/odoo19-enterprise/README.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

- [ ] **Step 1: Add execution notes to the program README**

Append this section to `docs/superpowers/programs/odoo19-enterprise/README.md`:

```markdown
## Execution Order

1. Complete discovery pack with evidence from Odoo 15 CE
2. Confirm engineering and governance rules
3. Approve domain wave sequencing
4. Write child specs per wave
5. Generate implementation plans per child spec
```

- [ ] **Step 2: Add owner review checkpoints to the spec index**

Append this section to `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`:

```markdown
## Review Checkpoints

- Business owner approval required before a child spec is marked ready
- Technical supervisor approval required before an implementation plan is written
- Owner-reporting impact must be confirmed before build starts
```

- [ ] **Step 3: Run the final verification suite**

Run:

```bash
python -m pytest tools/program_blueprint/tests/test_check_program_workspace.py -v
python tools/program_blueprint/check_program_workspace.py
git diff --check
```

Expected:

```text
1 passed
Program workspace is complete.
```

Expected from `git diff --check`: no output

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/programs/odoo19-enterprise/README.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
git commit -m "docs: add enterprise program handoff notes"
```

## Coverage Notes

This master plan covers the approved blueprint by turning it into executable program infrastructure:

- Blueprint architecture -> program workspace and engineering standards
- Delivery model -> review gates and execution order
- Access requirements -> discovery access checklist
- Legacy screening -> required child spec fields
- Roadmap and waves -> domain wave matrix
- Success criteria -> verification and gate model

Out of scope for this master plan:

- direct implementation of Sales, Finance, Service, Logistics, or HR addons
- data migration scripts
- integration connectors
- user training content

Those must be handled by child specs and follow-up implementation plans.
