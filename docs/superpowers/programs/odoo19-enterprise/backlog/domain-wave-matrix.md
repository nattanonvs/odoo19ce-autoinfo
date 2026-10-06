# Domain Wave Matrix

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise Program |
| Artifact | Domain wave backlog control matrix |
| Artifact status | Active baseline |
| Baseline source | `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md` |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-10-06 |
| Review cadence | Reconfirm before wave approval, resequencing, or child-spec sign-off |
| Validator expectation | Keep this file present at the manifest path |

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

## Wave Control Register

| Wave | Baseline scope | Child spec ID | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Gate readiness cue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | Foundation platform; Governance; KPI and reporting baseline | W0-FOUNDATION | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-0-foundation-governance.md` | Baseline defined | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; Engineering standards; Review gates | Ready when the program foundation pack is approved |
| Wave 1 | Contacts; Sales; Purchase; Inventory; Accounting | W1-COMMERCIAL-CORE | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In discovery | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 complete; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; current-state inventory evidence for purchase, inventory, and accounting still required | Ready when Purchase, Inventory, and Accounting child specs are approved against the established Sales and Contacts baseline |
| Wave 2 | Advance; Cheque; Money In Analysis | W2-FINANCE-CONTROLS | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-2-custom-finance-controls.md` | Not started | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 stable baseline; finance discovery evidence | Ready when finance control design and approvals are complete |
| Wave 3 | Sales Services; Claims; Warranty; Service Card; Product Return | W3-AFTER-SALES | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-3-sales-services-after-sales.md` | Not started | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer/product baseline; service domain evidence | Ready when after-sales process and KPI impacts are approved |
| Wave 4 | Stock Requests; Transportation; Logistics extensions | W4-LOGISTICS-EXT | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-4-logistics-extensions.md` | Not started | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Inventory baseline; transport workflow evidence | Ready when logistics extension scope and dependencies are approved |
| Wave 5 | Employees; Attendances; Time Off | W5-HR-ENABLEMENT | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-5-hr-operational-enablement.md` | Not started | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance; people operations evidence | Ready when HR enablement scope, approvals, and rollout assumptions are complete |

## Reviewability Cues

- Keep the baseline wave lists above unchanged so the plan-approved scope remains visible.
- Keep every wave in this file aligned with one row in `backlog/domain-spec-index.md`, including Wave 0.
- Use role-based owners, one technical reviewer, and shared approvers until named assignees are formally assigned.
- Update `Status` and `Gate readiness cue` only after a recorded review meeting or approval checkpoint.
- If wave sequencing changes, update both this matrix and the spec index in the same commit.
