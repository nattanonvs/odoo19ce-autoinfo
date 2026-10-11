# Domain Spec Index

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Program |
| Artifact | Child-spec control index |
| Artifact status | Active baseline |
| Baseline source | [2026-10-04-odoo19-ce-enterprise-blueprint-design.md](../../../specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md) |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-10-11 |
| Review cadence | Update whenever a child spec is created, approved, or resequenced |
| Validator expectation | Keep this file present at the manifest path |

## Required Child Specs

- [x] Wave 0 - Foundation platform, governance, and KPI/reporting baseline
- [ ] Wave 1 - Commercial and financial core
- [ ] Wave 2 - Custom finance controls
- [ ] Wave 3 - Sales Services and after-sales
- [ ] Wave 4 - Logistics extensions
- [ ] Wave 5 - HR and operational enablement

## Wave 1 Baseline Snapshot

| Domain | Current baseline status | Primary evidence | Remaining gap before Wave 1 closure |
| --- | --- | --- | --- |
| Contacts | Approved and implemented | `custom_addons/od19_contacts_partner_roles/` | No major design gap; keep regression-free while closing Accounting |
| Sales | Approved and implemented; customer risk gate implemented and verified on `odoo19_pdev` (24/24 tests pass, 2026-10-11) | `custom_addons/od19_sales_project_context/`, `custom_addons/od19_sales_contract_core/`, `custom_addons/od19_sales_billing_evidence/`, `custom_addons/od19_sales_reporting/`, `custom_addons/od19_sales_oca_bridge_workflow/`, `custom_addons/od19_sales_customer_risk_gate/`, [2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md) | No major design gap; keep regression-free while closing Wave 1 |
| Purchase | Approved and implemented | `custom_addons/od19_purchase_procurement_core/` | Keep stable and verify handoff into Inventory and Accounting |
| Inventory | Approved and implemented | `custom_addons/od19_inventory_execution_control/`, `custom_addons/od19_inventory_audit_count/`, `custom_addons/od19_inventory_reporting/` | Keep stable and harden lot/serial plus adjustment governance without reopening Wave 1 scope |
| Accounting | Approved and implemented; merged to 19.0 mainline and verified on `odoo19_pdev` (35/35 tests pass, 2026-10-11) | `custom_addons/od19_accounting_operational_closure/`, `custom_addons/od19_accounting_reporting/`, [2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md), [2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md](../../../plans/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md), master-plan backlog decisions, and the split defined in [2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md) | Keep regression-free; deep finance controls, credit limits, overdue holds, and approval tiers stay in Wave 2 |

## Wave 0

| Item | Status | Primary artifact |
| --- | --- | --- |
| Foundation and governance baseline | Approved | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) |
| Implementation pack | Released baseline package | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md](../../../plans/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md) |
| Handoff to Wave 1 | Active baseline | [wave-1-handoff-baseline.md](../governance/wave-1-handoff-baseline.md) |

Wave 0 is packaged and citable for Wave 1 planning, but the linked discovery artifacts remain active partial baselines rather than completed evidence packs.

## Child Spec Register

| Wave | Child spec ID | Canonical child spec title | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Discovery evidence | Gate readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | W0-FOUNDATION | Foundation platform, governance, and KPI/reporting baseline | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) | Approved | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; engineering standards; review gates | [current-state-inventory.md](../discovery/current-state-inventory.md); [access-readiness-checklist.md](../discovery/access-readiness-checklist.md); [engineering-standards.md](../foundation/engineering-standards.md); [review-gates.md](../governance/review-gates.md) | Ready when the foundation child spec is approved and execution order is agreed |
| Wave 1 | W1-COMMERCIAL-CORE | Commercial and financial core | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In execution | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Purchase baseline approved; Wave 1 Inventory baseline approved and merged on mainline; Wave 1 Accounting child spec approved, merged on mainline, and verified | Discovery baselines remain partial for access, integration, and data-quality evidence, while implementation evidence is active for the commercial core | Ready when the customer risk gate is implemented, Wave 1 owner KPIs are confirmed, and migration assumptions for the commercial core are accepted |
| Wave 2 | W2-FINANCE-CONTROLS | Custom finance controls | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-2-custom-finance-controls.md` | Not started | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 approved or explicitly decoupled; confirmed Wave 2 scope for Advance, Cheque, and Money In Analysis | Discovery evidence for advance, cheque, money-in, and high-value legacy finance reports | Ready when custom control rationale, reporting scope, dependencies, and approvals are complete |
| Wave 3 | W3-AFTER-SALES | Sales Services and after-sales | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-3-sales-services-after-sales.md` | Not started | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer/project/product baseline; confirmed separation of service returns from Inventory core | Discovery evidence for sales services, claims, warranty, service card, and service-linked returns | Ready when service flows, stock implications, owner-reporting impact, and training implications are approved |
| Wave 4 | W4-LOGISTICS-EXT | Logistics extensions | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-4-logistics-extensions.md` | Not started | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 inventory baseline; decision on legacy `Goods Issue`; Wave 3 dependencies as applicable | Discovery evidence for stock requests, transportation, logistics extensions, and non-standard warehouse flows | Ready when logistics dependencies, non-standard warehouse flow decisions, approval model, and rollout sequencing are approved |
| Wave 5 | W5-HR-ENABLEMENT | HR and operational enablement | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-5-hr-operational-enablement.md` | Not started | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance baseline | Discovery evidence for employees, attendances, and time off | Ready when HR operations scope, security posture, and training plan are approved |

## Wave Sequencing Notes

- Wave 1 remains the active closure target. Accounting and the customer risk gate are both merged/verified on the mainline workspace (2026-10-11); remaining Wave 1 work is owner-KPI confirmation and migration-assumption acceptance.
- Wave 0 is already released as the planning baseline package for Wave 1, but that does not convert the discovery artifacts into complete evidence; keep open discovery gaps visible until they are actually closed.
- Wave 1 should absorb only the customer risk gate baseline needed to stop blacklist sales and unapproved credit sales; it should not become the home of full finance-led credit control.
- Wave 1 Accounting should close AR, AP, payment, reconciliation, and essential posting/tax mapping as an operational baseline without absorbing Wave 2 control depth.
- Wave 2 should absorb finance controls and legacy reports only when they extend owner decision quality without re-opening Wave 1 boundaries.
- Wave 2 should take over deep credit-control behavior such as credit limits, overdue holds, approval tiers, and exception governance after the Wave 1 customer risk gate stabilizes.
- Wave 3 should own service-linked returns, warranty-linked stock behavior, and after-sales process complexity rather than pushing that logic back into Inventory.
- Wave 4 should own logistics extensions and the decision whether legacy `Goods Issue` still exists as a distinct future-state business process.

## Required Fields Per Child Spec

- Scope
- Current-state summary
- Keep/refactor/replace/retire decisions
- Future-state process
- Reporting and KPI needs
- Security and approval model
- Migration assumptions
- Training impact
- Child spec ID and wave reference
- Canonical child spec path and traceability back to [domain-wave-matrix.md](domain-wave-matrix.md)
- Owner, technical reviewer, approvers, and current status
- Discovery evidence references and source locations
- Dependency map, predecessor waves, and known blockers
- Approvers, approval dates, and approval notes
- Gate readiness summary for spec-ready, plan-ready, and build-ready checkpoints

## Child Spec Header Schema

```markdown
# <Child Spec Title>

## Control Metadata
- Child spec ID: <W0-W5 code>
- Wave: <Wave 0-5>
- Status: <Not started | In discovery | Draft | In review | Approved | Ready for plan>
- Owner: <role or named owner>
- Reviewer: <technical reviewer role or named reviewer>
- Approvers: <business owner>; <technical supervisor>
- Canonical path: <docs/superpowers/specs/...>
- Source backlog row: `backlog/domain-wave-matrix.md`

## Discovery Evidence
- Current-state references: <links to discovery artifacts, screenshots, exports, notes>
- Evidence coverage gaps: <known unknowns that must be closed before approval>

## Delivery Controls
- Dependencies: <waves, specs, systems, or data prerequisites>
- Gate readiness:
  - Spec-ready: <criteria>
  - Plan-ready: <criteria>
  - Build-ready: <criteria>
```

## Control Rules

- Do not mark a child spec ready unless its evidence, reviewer input, and approvers are recorded.
- Keep wave naming, child-spec IDs, and path placeholders synchronized with [domain-wave-matrix.md](domain-wave-matrix.md).
- Promote a child spec to `Ready for plan` only after business and technical review are both complete.
- Keep this index synchronized with the master-plan section `Wave Planning Update After Inventory Baseline` when post-review scope or sequencing changes.

## Review Checkpoints

- Business owner approval required before a child spec is marked ready
- Technical supervisor approval required before an implementation plan is written
- Owner-reporting impact must be confirmed before build starts
