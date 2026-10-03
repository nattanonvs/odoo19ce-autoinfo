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
- Discovery baseline from `discovery/current-state-inventory.md` and `discovery/access-readiness-checklist.md`
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
- Every Wave 1 child spec must cite the active discovery baseline and call out where discovery evidence is still partial, blocked, or open.
- If a Wave 1 domain needs to deviate from Wave 0 policy, the deviation must be raised as an explicit exception or spec decision record rather than hidden in implementation detail.
- Wave 1 planning must inherit the production readiness baseline as the default platform policy for ownership, backup, restore, monitoring, and rollback expectations.
- Wave 1 planning may extend the reporting and dashboard baseline for a domain, but it must preserve the role-based intent already defined in Wave 0.

## Known Unknowns Handed To Wave 1

| Area | Current uncertainty | Why it still matters in Wave 1 | Baseline evidence to revisit |
| --- | --- | --- | --- |
| Legacy version and company scope | Exact Odoo 15 version evidence and final company list are still not attached in discovery artifacts. | Domain designs can drift if business scope or source-system assumptions are incomplete. | `discovery/current-state-inventory.md` |
| Custom namespace completeness | `AUTO-INFO` and `DTR` are confirmed, but full exported namespace and automation inventory is still incomplete. | Wave 1 domains may miss hidden dependencies, scheduled jobs, or custom model ownership. | `discovery/current-state-inventory.md` |
| Infrastructure and config access | Shell, config-file, and addon-path evidence is still not formally attached. | Technical design may assume platform facts that have not been evidenced yet. | `discovery/access-readiness-checklist.md` |
| Data extraction and sanitized access | Dump, sanitized copy, and master-data extraction approvals remain incomplete. | Migration, profiling, and reconciliation planning can stall without approved data access. | `discovery/access-readiness-checklist.md` |
| Integration and security-risk evidence | Integration endpoint inventory, secrets review, and privileged automation evidence are still pending. | Domain plans may underestimate security review, dependency risk, and cutover complexity. | `discovery/access-readiness-checklist.md` |

## Minimum Handoff Traceability

| Handoff element | Minimum approver role | Decision date | Evidence reference |
| --- | --- | --- | --- |
| Wave 0 baseline accepted for Wave 1 use | Program delivery lead | Record when approved | Approved Wave 0 spec and linked artifact pack |
| Discovery baseline accepted for planning use | Program discovery lead | Record when confirmed | `discovery/current-state-inventory.md` and `discovery/access-readiness-checklist.md` |
| Platform baseline accepted | Program engineering lead | Record when approved | Repository, environment, and production baseline artifacts |
| Reporting baseline accepted | Business sponsor | Record when approved | KPI baseline and dashboard blueprint |
| Handoff package released to domain teams | Program delivery lead | Record when handed off | This handoff document plus referenced Wave 0 artifacts |

## Entry Questions For Wave 1 Teams

- Which approved baseline artifacts apply directly to this domain?
- Which domain flows, records, and roles require further design before build planning?
- What discovery evidence from the legacy system still affects this domain's assumptions?
- Which migration and reporting questions remain open and need domain-owner review?
