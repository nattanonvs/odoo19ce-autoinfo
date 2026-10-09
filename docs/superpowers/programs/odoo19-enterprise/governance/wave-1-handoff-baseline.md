# Wave 1 Handoff Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md` |
| Artifact owner | Program delivery lead |
| Required reviewers | Program engineering lead, architecture lead, domain owner representatives |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before each Wave 1 child spec enters detailed planning and when the Wave 0 package changes materially |
| Last updated | 2026-10-09 |

## Purpose

Define the minimum package that Wave 1 receives from Wave 0 so domain teams can start detailed business design without reopening foundational governance and platform decisions.

This handoff is an active planning baseline. It does not mean every discovery item is closed; Wave 1 teams must keep using the linked discovery artifacts as the source of truth for partial, blocked, or open evidence.

## Scope

- Applies to the transition from Wave 0 foundation work into Wave 1 domain-specific design.
- Applies to baseline artifacts, review rules, and expected downstream responsibilities.
- Does not define business transaction detail, field mapping detail, implementation logic, or final dashboard construction.
- Uses `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml` as the canonical package index for the Wave 0 baseline pack and the active governed control artifacts currently kept with the program workspace.

## What Wave 1 Receives

- Approved Wave 0 child spec
- Program manifest pointer in `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml`
- Active discovery baselines from `discovery/current-state-inventory.md` and `discovery/access-readiness-checklist.md`, usable for planning but still partial where those files say so
- Engineering standards
- Review gates
- Repository and addon baseline
- Environment and delivery baseline
- Production readiness baseline
- KPI and reporting baseline
- Dashboard blueprint
- Active sales governance references in `sales/addon-boundaries.md`, `sales/oca-fit-gap.md`, and `sales/oca-installation-recommendations.md`

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
- Every Wave 1 child spec should use `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml` as the first lookup for the required Wave 0 artifact package before following deeper links.
- Every Wave 1 child spec must cite the active discovery baseline and call out where discovery evidence is still partial, blocked, or open.
- Do not translate "handoff released" into "discovery complete"; child specs must keep open evidence gaps visible until the source artifacts are updated.
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
| Wave 0 baseline accepted for Wave 1 use | Program delivery lead | 2026-10-04 | Approved Wave 0 spec `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md`, linked artifact pack in `README.md`, and `program-manifest.yaml` |
| Discovery baseline accepted for planning use | Program discovery lead | 2026-10-04 | `discovery/current-state-inventory.md` and `discovery/access-readiness-checklist.md` as the active discovery references for Wave 1 planning |
| Platform baseline accepted | Program engineering lead | 2026-10-04 | `foundation/repository-and-addon-baseline.md`, `foundation/environment-and-delivery-baseline.md`, and `foundation/production-readiness-baseline.md` |
| Reporting baseline accepted | Business sponsor | 2026-10-04 | `reporting/kpi-reporting-baseline.md` and `reporting/role-based-dashboard-blueprint.md` |
| Handoff package released for Wave 1 planning use | Program delivery lead | 2026-10-04 | This handoff document, `governance/wave-0-readiness-assessment.md`, `program-manifest.yaml`, and the referenced Wave 0 artifact pack |

## Release Note

- Wave 0 packaged the baseline artifacts for Wave 1 planning use on 2026-10-04.
- This release note means the package is reviewable and citable by domain teams; it does not mean the known unknowns in this document are closed.
- Any Wave 1 team that finds a missing approval, discovery gap, or policy conflict must raise an explicit exception instead of silently overriding the handoff package.

## Entry Questions For Wave 1 Teams

- Which approved baseline artifacts apply directly to this domain?
- Which domain flows, records, and roles require further design before build planning?
- What discovery evidence from the legacy system still affects this domain's assumptions?
- Which migration and reporting questions remain open and need domain-owner review?
