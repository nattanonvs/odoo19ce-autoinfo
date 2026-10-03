# Wave 1 Handoff Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md` |
| Artifact owner | Program delivery lead |
| Required reviewers | Program engineering lead, architecture lead, domain owner representatives |
| Artifact status | Draft handoff baseline |
| Review cadence | Reconfirm before each Wave 1 child spec enters detailed planning and when the Wave 0 package changes materially |
| Last updated | 2026-10-04 |

## Purpose

Define the minimum package that Wave 1 receives from Wave 0 so domain teams can start detailed business design without reopening foundational governance and platform decisions.

## Scope

- Applies to the transition from Wave 0 foundation work into Wave 1 domain-specific design.
- Applies to baseline artifacts, review rules, and expected downstream responsibilities.
- Does not define business transaction detail, field mapping detail, implementation logic, or final dashboard construction.

## What Wave 1 Receives

- Approved Wave 0 child spec
- Engineering standards
- Review gates
- Repository and addon baseline
- Environment and delivery baseline
- Production readiness baseline
- KPI and reporting baseline
- Dashboard blueprint

## What Wave 1 Still Must Define

- Domain transaction flows
- Field-level mapping
- Domain-specific security details
- Migration details by domain

## Deferred Items

- UI detail
- Implementation code
- Dashboard build in Odoo

## Handoff Rules

- Every Wave 1 child spec must cite the approved Wave 0 spec and relevant baseline artifacts instead of redefining them locally.
- If a Wave 1 domain needs to deviate from Wave 0 policy, the deviation must be raised as an explicit exception or spec decision record rather than hidden in implementation detail.
- Wave 1 planning may extend the reporting and dashboard baseline for a domain, but it must preserve the role-based intent already defined in Wave 0.

## Entry Questions For Wave 1 Teams

- Which approved baseline artifacts apply directly to this domain?
- Which domain flows, records, and roles require further design before build planning?
- What discovery evidence from the legacy system still affects this domain's assumptions?
- Which migration and reporting questions remain open and need domain-owner review?
