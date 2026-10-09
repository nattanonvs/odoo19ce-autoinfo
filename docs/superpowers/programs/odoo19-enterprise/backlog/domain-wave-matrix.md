# Domain Wave Matrix

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Program |
| Artifact | Domain wave backlog control matrix |
| Artifact status | Active baseline |
| Baseline source | `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md` |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-10-09 |
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

## Wave Delivery Focus

### Wave 1 Focus
- Close the commercial core on top of the approved Contacts, Sales, Purchase, Inventory, and approved Accounting design baselines.
- Treat Inventory as an implemented and merged baseline, but do not mark the wave complete until Accounting implementation is merged, verified, and the owner KPI closeout is confirmed on the mainline workspace.
- Add the customer risk gate baseline so `Blacklist` customers are blocked from both `Quotation` and `Sales Order`, and `Credit Pending` customers remain cash-only until Accounting approval is complete.
- Close Accounting as an operational-closure baseline that covers AR, AP, payment, reconciliation, and essential posting/tax mapping without pulling deep finance controls forward from Wave 2.
- Keep Wave 1 limited to commercial-core truth, readiness, and owner-facing KPIs.
- Do not pull advanced finance controls, after-sales process logic, or logistics extensions forward unless a documented dependency forces it.

### Wave 2 Focus
- Extend from the stable Wave 1 commercial core into finance-specific controls.
- Prioritize Advance, Cheque, and Money In Analysis together with reporting that directly improves owner decision-making.
- Absorb deep credit controls such as credit limits, overdue holds, exception approvals, and finance-led exposure reporting after the Wave 1 customer risk gate is stable.
- Rebuild only the finance and inventory reports that still carry decision value from the Odoo 15 legacy system.

### Wave 3 Focus
- Build the after-sales operating model as its own bounded context.
- Keep service returns, warranty-linked stock behavior, claims, and service-card flows out of Inventory core.
- Use the stable customer, project, and product baseline from earlier waves.

### Wave 4 Focus
- Build logistics extensions only after the Inventory baseline is stable in production-like use.
- Re-evaluate legacy warehouse and issue flows, including `Goods Issue`, against the new standard movement baseline before approving any rebuild.
- Default to redesign over direct migration for transportation and non-standard warehouse convenience logic.

## Wave Control Register

| Wave | Baseline scope | Child spec ID | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Gate readiness cue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | Foundation platform; Governance; KPI and reporting baseline | W0-FOUNDATION | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-0-foundation-governance.md` | Approved and packaged for Wave 1 planning | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; Engineering standards; Review gates | Ready and released for Wave 1 planning use; discovery evidence remains partial where the linked discovery artifacts still say so |
| Wave 1 | Contacts; Sales; Purchase; Inventory; Accounting | W1-COMMERCIAL-CORE | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In execution | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Purchase baseline approved; Wave 1 Inventory baseline approved and merged on mainline; Wave 1 Accounting child spec approved and implementation active in delivery branch | Ready when Accounting implementation is merged and verified on the mainline workspace and the Wave 1 owner KPI set is confirmed against the established Sales, Contacts, Purchase, Inventory, and Accounting baseline |
| Wave 2 | Advance; Cheque; Money In Analysis | W2-FINANCE-CONTROLS | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-2-custom-finance-controls.md` | Not started | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 stable baseline; finance discovery evidence | Ready when finance control design and approvals are complete |
| Wave 3 | Sales Services; Claims; Warranty; Service Card; Product Return | W3-AFTER-SALES | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-3-sales-services-after-sales.md` | Not started | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer/product baseline; service domain evidence; confirmed separation between inventory core and after-sales returns | Ready when after-sales process, service-linked stock implications, and KPI impacts are approved |
| Wave 4 | Stock Requests; Transportation; Logistics extensions | W4-LOGISTICS-EXT | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-4-logistics-extensions.md` | Not started | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Inventory baseline; transport workflow evidence; decision on whether legacy `Goods Issue` remains a real business process after Wave 1 | Ready when logistics extension scope, non-standard warehouse flow decisions, and rollout dependencies are approved |
| Wave 5 | Employees; Attendances; Time Off | W5-HR-ENABLEMENT | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-5-hr-operational-enablement.md` | Not started | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance; people operations evidence | Ready when HR enablement scope, approvals, and rollout assumptions are complete |

## Reviewability Cues

- Keep the baseline wave lists above unchanged so the plan-approved scope remains visible.
- Keep every wave in this file aligned with one row in `backlog/domain-spec-index.md`, including Wave 0.
- Use role-based owners, one technical reviewer, and shared approvers until named assignees are formally assigned.
- Update `Status` and `Gate readiness cue` only after a recorded review meeting or approval checkpoint.
- Treat Wave 0 as an approved planning package, not as a claim that every discovery line item is fully evidenced.
- If wave sequencing changes, update both this matrix and the spec index in the same commit.
- Keep this matrix aligned with the master-plan section `Wave Planning Update After Inventory Baseline` whenever post-review backlog decisions change.
