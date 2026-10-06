# Domain Spec Index

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise Program |
| Artifact | Child-spec control index |
| Artifact status | Active baseline |
| Baseline source | [2026-10-04-odoo19-ce-enterprise-blueprint-design.md](../../../specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md) |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-10-06 |
| Review cadence | Update whenever a child spec is created, approved, or resequenced |
| Validator expectation | Keep this file present at the manifest path |

## Required Child Specs

- [x] Wave 0 - Foundation platform, governance, and KPI/reporting baseline
- [ ] Wave 1 - Commercial and financial core
- [ ] Wave 2 - Custom finance controls
- [ ] Wave 3 - Sales Services and after-sales
- [ ] Wave 4 - Logistics extensions
- [ ] Wave 5 - HR and operational enablement

## Wave 0

| Item | Status | Primary artifact |
| --- | --- | --- |
| Foundation and governance baseline | Approved | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) |
| Implementation pack | In progress | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md](../../../plans/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md) |
| Handoff to Wave 1 | Draft | [wave-1-handoff-baseline.md](../governance/wave-1-handoff-baseline.md) |

## Child Spec Register

| Wave | Child spec ID | Canonical child spec title | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Discovery evidence | Gate readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | W0-FOUNDATION | Foundation platform, governance, and KPI/reporting baseline | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) | Approved | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; engineering standards; review gates | [current-state-inventory.md](../discovery/current-state-inventory.md); [access-readiness-checklist.md](../discovery/access-readiness-checklist.md); [engineering-standards.md](../foundation/engineering-standards.md); [review-gates.md](../governance/review-gates.md) | Ready when the foundation child spec is approved and execution order is agreed |
| Wave 1 | W1-COMMERCIAL-CORE | Commercial and financial core | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In discovery | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 approved; Wave 1 Sales and Contacts baselines approved | Discovery evidence exists for sales and contacts; purchase, inventory, and accounting evidence still incomplete | Ready when the remaining Wave 1 child specs align with the approved Sales and Contacts baseline, reporting KPIs, and migration assumptions |
| Wave 2 | W2-FINANCE-CONTROLS | Custom finance controls | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-2-custom-finance-controls.md` | Not started | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 approved or explicitly decoupled | Discovery evidence for advance, cheque, and money-in workflows | Ready when custom control rationale, dependencies, and approvals are complete |
| Wave 3 | W3-AFTER-SALES | Sales Services and after-sales | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-3-sales-services-after-sales.md` | Not started | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer baseline | Discovery evidence for sales services, claims, warranty, service card, and returns | Ready when service flows, owner-reporting impact, and training implications are approved |
| Wave 4 | W4-LOGISTICS-EXT | Logistics extensions | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-4-logistics-extensions.md` | Not started | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 inventory baseline; Wave 3 service dependencies as applicable | Discovery evidence for stock requests, transportation, and logistics extensions | Ready when logistics dependencies, approval model, and rollout sequencing are approved |
| Wave 5 | W5-HR-ENABLEMENT | HR and operational enablement | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-5-hr-operational-enablement.md` | Not started | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance baseline | Discovery evidence for employees, attendances, and time off | Ready when HR operations scope, security posture, and training plan are approved |

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

## Review Checkpoints

- Business owner approval required before a child spec is marked ready
- Technical supervisor approval required before an implementation plan is written
- Owner-reporting impact must be confirmed before build starts
