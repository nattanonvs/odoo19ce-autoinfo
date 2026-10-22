# Odoo 19 CE Enterprise Blueprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved enterprise blueprint into an executable delivery program with validated workspace structure, discovery artifacts, governance documents, and wave-based child specs before any business-domain build starts.

**Architecture:** This is a master orchestration plan, not a direct business-module implementation plan. It creates the durable program workspace, validates required artifacts with a lightweight checker, captures current-state discovery from Odoo 15 CE, and prepares domain-level specs and review gates so later build plans can stay modular, upgrade-safe, and OCA-first.

**Tech Stack:** Markdown, YAML, Python 3, pytest, git, Odoo 19 CE repository docs structure

## Discovery Evidence

- Approved blueprint spec: `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
- Odoo 15 production reference source code: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
- Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Current-state discovery artifact: `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md`
- Program workspace baseline target: `docs/superpowers/programs/odoo19-enterprise/`

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

## Wave Planning Update After Inventory Baseline

This section records the fit-gap decision after the Wave 1 Inventory baseline was implemented in the dedicated worktree and reviewed against the legacy Odoo 15 inventory landscape. Its purpose is to make the next-wave backlog explicit inside the master plan instead of leaving the decision spread across conversations.

### Current Planning Position

- Wave 1 Inventory baseline is considered implemented at the addon level through `od19_inventory_execution_control`, `od19_inventory_audit_count`, and `od19_inventory_reporting`.
- The Inventory baseline now covers movement execution truth, count variance visibility, and first-line owner reporting.
- Wave 1 is not yet considered complete at the program level: Accounting is merged and verified (35/35 tests, 2026-10-11) and Project &amp; Analytic Accounting was implemented 2026-10-20, but Project &amp; Analytic Accounting still needs business-owner verification on `odoo19_pdev` and the Wave 1 migration assumptions still need acceptance.
- Legacy Odoo 15 inventory features are not migrated wholesale. They are screened using `Keep`, `Refactor`, `Replace`, and `Retire`.

### Legacy Inventory to New Coverage

| Legacy inventory capability | New coverage in Odoo 19 | Decision | Target wave |
| --- | --- | --- | --- |
| `dtr_stock` movement foundation | Covered by `od19_inventory_execution_control` on top of standard `stock`, `purchase_stock`, and `sale_stock` | Keep movement truth, refactor into bounded addons | Wave 1 |
| Receipt, delivery, internal transfer | Covered by computed `flow class` and `execution state` on `stock.picking` | Keep | Wave 1 |
| Return to vendor and customer return baseline | Covered by return classification and return-focused tests | Keep | Wave 1 |
| Reference document traceability | Covered by `od19_reference_document` on `stock.move` | Keep | Wave 1 |
| Lot / serial tracking baseline | Covered only at first level through tracking-required semantics on product templates | Refactor into policy-based governance | Wave 1 |
| Duplicate lot / serial controls from legacy stock customizations | Not yet covered at legacy depth | Refactor, do not migrate directly | Wave 1 |
| Full audit counting | Covered at first level by `od19_inventory_audit_count` session and variance models | Keep and harden | Wave 1 |
| Stock adjustment discipline | Variance exists but full review / approval / adjustment governance is still incomplete | Replace legacy ad-hoc adjustment patterns with controlled adjustment workflow | Wave 1 |
| Inventory accuracy reporting | Covered at first level by `od19_inventory_reporting` | Keep | Wave 1 |
| Movement backlog reporting | Covered at first level by `od19_inventory_reporting` | Keep | Wave 1 |
| Inventory overview screens from legacy system | Not reproduced one-to-one | Replace with KPI-oriented views on canonical models | Wave 1 |
| Monthly stock, aging, dead stock, FIFO as-of reports | Not yet covered in the new baseline | Refactor and rebuild only reports with owner value | Wave 2 |
| `dtr_goods_issue` dedicated issue document | Delivered as `od19_goods_issue` — a Thai document/UX layer (ใบเบิก/ใบหยิบสินค้า) on top of the adopted OCA `stock_request` (decided 2026-10-21) | Keep as document layer, do not copy the legacy model | Wave 4 |
| Split picking custom convenience | No direct replacement yet | Retire unless standard Odoo proves insufficient | Wave 4 |
| Inventory tier approval spread across legacy operations | No direct replacement yet | Replace with approval only for material variance and adjustment events | Wave 1 |
| Stock requests and transportation-linked warehouse flows | Out of scope for Wave 1 Inventory baseline; internal stock request now covered by adopted OCA `stock_request` (2026-10-21) | Refactor into logistics extension scope | Wave 4 |
| Service-linked returns, warranty-linked stock, repair stock effects | Out of scope for Wave 1 Inventory baseline | Refactor into after-sales scope | Wave 3 |
| Jasper-heavy inventory report catalog | Not migrated | Retire direct migration; rebuild only decision-useful outputs | Wave 2 |

### Remaining Work by Wave

#### Wave 1 - Close Commercial Core

- Inventory merge into `19.0` is complete (`od19_inventory_execution_control`, `od19_inventory_audit_count`, `od19_inventory_reporting`), with install/upgrade/uninstall and regression behavior verified.
- Accounting is merged to `19.0` mainline and verified (35/35 tests, 2026-10-11).
- Project &amp; Analytic Accounting (W1-PROJECT-ANALYTIC) was implemented 2026-10-20 (65 domain tests pass); the remaining gate is business-owner verification on `odoo19_pdev`.
- Purchase Revision (W1-PURCHASE-REVISION) is in review — design approved 2026-10-16; scope is the Purchase Order only and must not alter the existing ISO footer.
- Fix the test environment so inventory addon tests can run cleanly in the target workspace.
- Harden lot/serial policy into explicit business rules by product or product group.
- Add review and approval semantics for material count variance and approved stock adjustments.
- Add owner-facing commercial core KPIs that combine Sales, Purchase, Inventory, and Accounting baseline signals.
- Confirm the Wave 1 migration assumptions with the business owner and close the wave in the program control documents.

#### Wave 2 - Finance Controls and Reporting Expansion

- Design and implement Advance controls.
- Design and implement Cheque controls.
- Design and implement Money In Analysis.
- Design and implement Withholding Tax (WHT) on OCA `l10n_th_account_tax` (v19.0) instead of a custom WHT module.
- Design and implement Petty Cash.
- Replace `om_fiscal_year` with OCA `account_fiscal_year` (periods) and handle year-end closing as manual no-code on Odoo 19 core lock dates (`fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` / `sale_lock_date` + `account.lock_exception`) — no custom `dtr_year_end` replacement module (decided 2026-10-21).
- Replace `om_account_asset` and `dtr_fixed_assets` with OCA `account_asset_management` (`third_party/oca/account-financial-tools/`) or custom asset management.
- Establish the Jasper Reports Foundation (JasperReports + jasperstarter) and the Dual Report Format for all printable reports.
- Add the Wave 2 Thai Localization modules (`od19_accounting_reporting`, `od19_accounting_payment_voucher_reports`) and Payment Preparation วิธีที่ 3 (Odoo standard + OCA, ~300 lines custom) — **Payment Voucher/Receipt + PV/RV sequence delivered 2026-10-21** in `od19_accounting_payment_voucher_reports`.
- Rebuild only the inventory and finance reports from Odoo 15 that still provide direct owner value, such as aging, dead stock, monthly stock, and related decision reports.
- Expand management reporting by connecting commercial, inventory, and finance signals into clearer owner dashboards.

#### Wave 3 - After-Sales and Service Return Domain

- Design and implement Sales Services.
- Design and implement Claims.
- Design and implement Warranty.
- Design and implement Service Card.
- Design and implement Product Return in the after-sales context.
- Replace `dtr_qc` with an in-house QC workflow for incoming/outgoing inspection — delivered as custom module `od19_quality_control` (no OCA `quality_control_oca` exists in `third_party/oca`).
- Consolidate Digital Signature on in-house `od19_document_sign` (delivered 2026-10-19) using Odoo 19 CE signature infrastructure.
- Move service-linked return scenarios, warranty-linked stock effects, and repair-related stock implications out of Inventory core and into the after-sales domain.

#### Wave 4 - Logistics Extensions and Non-Standard Warehouse Flows

- Adopt OCA `stock_request` for internal stock requests (ขอเบิก/ขอโอนสินค้าภายใน) — submodule `third_party/oca/stock-logistics-request` (branch 19.0) added 2026-10-21; purchase requisition stays on OCA `purchase_request*` + `od19_purchase_request_extend`.
- Design and implement Transportation.
- Design and implement Logistics extensions.
- Replace `dtr_stock_valuation_adjustment` with Odoo 19 standard inventory value adjustments plus audit trail.
- Enable standard `stock_landed_costs` for shipping and import cost allocation.
- `Goods Issue` remains a real business process — **decided 2026-10-21**: keep it as a logistics/warehouse document/UX layer (`od19_goods_issue`) on top of standard movement truth (OCA `stock_request`), rather than copying the legacy model directly and rather than retiring the process.
- `od19_goods_issue` provides the Thai document layer: department (`hr.department`) / job (`project.project`) / reason fields on `stock.request.order`, a per-department sequence `GI/{DEPT}/` (fallback `GI/GEN/`), and printable ใบเบิกสินค้า (goods issue) + ใบหยิบสินค้า (pick list) QWeb reports.
- Revisit advanced warehouse convenience features, such as split-picking behavior, only if standard Odoo plus redesigned process is proven insufficient.

#### Wave 5 - HR and Operational Enablement

- Replace `autoinfo_hr_expense` and `autoinfo_hr_expense_cash_tracking` with Odoo 19 standard `hr_expense` plus custom cash reimbursement and multi-tier approval.
- Replace `autoinfo_fleet` with the Odoo 19 standard `fleet` module; integrate with accounting and HR where needed.
- Attendances + Time Off are enabled and ZKTeco device integration was delivered 2026-10-15; complete real-device commissioning and confirm the OT policy.

#### Cross-Cutting Reporting Track (Outside Wave 0–5)

- The dashboard/reporting enablement specs (`W6-DASH-FORMULA-RULES`, `W6-DASH-PHASE2`) build out the Wave 0 KPI and reporting baseline in module `od19_dashboard`. They are tracked as a cross-cutting track in `backlog/domain-wave-matrix.md` and `backlog/domain-spec-index.md`, not as a domain wave.

### Planning Rules After Inventory Review

- Do not treat legacy inventory breadth as a requirement to migrate every legacy customization.
- Promote only those legacy behaviors that improve stock truth, auditability, owner value, or cross-domain clarity.
- Keep Wave 1 focused on commercial-core closure. Do not pull finance controls, after-sales, or logistics extensions forward unless a documented dependency forces it.
- If a legacy feature is mostly UI convenience, report duplication, or workaround behavior from Odoo 15, default to retire or redesign instead of migrate.

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
