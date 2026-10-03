# Engineering Standards

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md` |
| Artifact owner | Program engineering lead |
| Required reviewers | Program architecture lead, security reviewer, delivery lead |
| Artifact status | Active baseline |
| Review cadence | Reconfirm at blueprint approval, before each build gate, and whenever an exception is requested |
| Last updated | 2026-10-04 |

## Purpose

Define the minimum engineering contract for every addon, extension, and delivery package produced under the Odoo 19 CE Enterprise program.

## Scope

- Applies to all custom addons, OCA selections, approved third-party modules, migration scripts, data-loading utilities, CI checks, and deployment notes that affect this program.
- Applies from blueprint approval through build, UAT, parallel run, and production cutover preparation.
- Does not waive the standing project constraints of no direct Odoo core modification, OCA-first evaluation, and uninstall-safe delivery.

## Roles and Review Cues

| Role | Responsibility |
| --- | --- |
| Program engineering lead | Maintains this standard and confirms implementation teams understand it before build starts. |
| Architecture lead | Reviews bounded responsibility, dependency shape, and upgrade-path impact. |
| Security reviewer | Reviews explicit security model, privileged behavior, and exception requests. |
| Delivery lead | Confirms required checks and evidence are attached before gate review. |
| Domain implementer | Produces code, notes, and evidence required to satisfy this contract. |

## How To Use This Standard

- Treat every rule and check below as mandatory unless an approved waiver record exists.
- Link delivery evidence to the relevant domain spec, pull request, CI job, test result, dependency review note, and upgrade note.
- If a requirement is not applicable, record `N/A` with rationale and reviewer approval rather than leaving the item blank.
- If evidence is partial, the work item remains open and cannot be declared build-ready.

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

## Evidence Requirements

| Check or area | Minimum evidence |
| --- | --- |
| Core Rules | Design or review note showing no core patching, OCA evaluation result, addon boundary, and install/upgrade/uninstall impact. |
| Code Rules | Pull request or review note showing readable naming, focused methods, explicit security model, and critical logic coverage. |
| Lint | CI job, local run output, or captured command result linked to the delivery artifact. |
| Tests | Automated test output for critical business logic and any targeted manual verification notes when automation is not sufficient. |
| Module dependency review | Addon manifest review, dependency list, and rationale for each non-standard dependency. |
| Upgrade note | Short note describing migration assumptions, data-impact considerations, and any required upgrade follow-up. |
| Security review | Review note covering access rights, record rules, privileged actions, secrets exposure risk, and unsafe side effects. |

## Decision Outcomes

- `Pass`: all applicable core rules, code rules, and required checks are satisfied with reviewable evidence.
- `Conditional pass`: only allowed when every applicable core rule has affirmative evidence, every non-waivable required check is complete, and the remaining gap is a bounded follow-up item with owner, due date, and reviewer approval; conditional pass cannot be used for direct core modification, failed tests, missing security review, missing install/uninstall safety evidence, or a still-pending waiver request.
- `Fail`: any core rule is violated, any non-waivable required check fails or lacks evidence, or a waiver is used outside its approved scope.
- `Blocked`: evidence, access, tooling, or required reviewers are unavailable, so the item cannot proceed to the next gate decision.

## Traceability Requirements

- Every domain delivery must link back to its approved domain spec, applicable program artifacts, and the exact review or CI evidence used to claim compliance.
- Discovery-sensitive implementations should reference relevant evidence from `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md` and `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md` when legacy behavior, access constraints, or migration assumptions influence engineering choices.
- Review gates must reference this document explicitly when deciding whether build work is ready to proceed.

## Waiver and Exception Path

- Exceptions are allowed only for bounded cases where the default rule would block justified program delivery and no safer compliant alternative exists.
- Every exception request must identify the rule or check affected, business reason, scope, risk, mitigation, owner, expiry date, and rollback or cleanup expectation.
- Waivers for direct Odoo core modification are not permitted by this program contract.
- A waiver is valid only after written approval from the program engineering lead plus the relevant functional reviewer, and it must be referenced during gate review.

## Waiver Scope Mapping

| Rule or check | Waiver scope |
| --- | --- |
| No direct Odoo core modifications | Not waivable. Evidence must show no direct core patching or override of Odoo core files. |
| OCA first, custom second | The evaluation step is not waivable. Evidence must show standard and OCA options were considered before approving a custom outcome. |
| One bounded responsibility per addon | Narrow temporary waiver allowed only for a time-bounded transition case with explicit split or remediation plan; the waiver applies only to the named addon scope. |
| Install, upgrade, and uninstall safety required | Not waivable for build readiness. Evidence must show the delivery is operationally safe. |
| Lint | Not waivable for build readiness. |
| Tests | Not waivable for build readiness. |
| Module dependency review | Scope may be conditionally accepted only when the dependency analysis exists and the remaining follow-up is documentation detail, not missing review. |
| Upgrade note | Scope may be conditionally accepted only when the upgrade impact is recorded and the remaining follow-up is bounded editorial refinement. |
| Security review | Not waivable for build readiness. |

## Review Cadence

- Review this document at blueprint approval to confirm the baseline still matches program constraints.
- Reconfirm applicability before each domain build starts and at every Gate 4 review.
- Update this document when a new recurring risk, reviewer expectation, or check type becomes program-wide policy.
