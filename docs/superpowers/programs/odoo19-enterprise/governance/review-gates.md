# Review Gates

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md` |
| Artifact owner | Program delivery lead |
| Required reviewers | Program engineering lead, architecture lead, security reviewer, domain owner |
| Artifact status | Active governance baseline |
| Review cadence | Evaluate at each formal gate review and whenever a waiver affects gate readiness |
| Last updated | 2026-10-04 |

## Purpose

Define the minimum evidence, decision rules, and approval outcomes required to move work through the Odoo 19 CE Enterprise program lifecycle.

## Decision Outcomes

- `Pass`: all applicable core rules, code rules, and required checks are satisfied with reviewable evidence.
- `Conditional pass`: only allowed when every applicable core rule has affirmative evidence, every non-waivable required check is complete, and the remaining gap is a bounded follow-up item with owner, due date, and reviewer approval; conditional pass cannot be used for direct core modification, failed tests, missing security review, missing install/uninstall safety evidence, or a still-pending waiver request.
- `Fail`: any core rule is violated, any non-waivable required check fails or lacks evidence, or a waiver is used outside its approved scope.
- `Blocked`: evidence, access, tooling, or required reviewers are unavailable, so the item cannot proceed to the next gate decision.

## Evidence and Traceability Rules

- Every gate decision must reference the exact artifact, review note, export, CI run, or issue that supports the decision.
- Gate packages must link to the current domain spec, applicable discovery evidence, and the relevant program controls in `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md`.
- If a required artifact does not yet exist, the gate cannot claim a full pass for that criterion.
- Review notes should capture approver, decision date, unresolved actions, and any linked waiver or exception ID.

## Gate 1: Discovery Approved
- Current-state inventory reviewed
- Access checklist completed
- Custom map reviewed

### Gate 1 Evidence Cues

- Review `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md` for current-state evidence, open questions, and blocked areas.
- Review `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md` for access scope, blockers, and evidence links.
- Review the custom map or approved equivalent inventory that traces legacy menus, actions, models, and automation hotspots.

### Gate 1 Pass / Fail Rules

- `Pass` requires the discovery artifacts to be reviewable, scoped to the program, and sufficient to support blueprint work.
- `Fail` applies when key evidence is missing, access blockers are unmanaged, or legacy custom scope remains opaque.

## Gate 2: Blueprint Approved
- Architecture approved
- OCA policy approved
- Engineering rules approved

### Gate 2 Evidence Cues

- Approved architecture or blueprint artifact for the target Odoo 19 CE operating model.
- OCA evaluation policy or equivalent decision record showing standard and OCA-first selection logic.
- Current version of `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md` acknowledged by engineering and governance reviewers.

### Gate 2 Pass / Fail Rules

- `Pass` requires the blueprint to be approved with engineering standards accepted as the active delivery contract.
- `Fail` applies when the architecture is unresolved, OCA policy is unclear, or engineering rules are not yet accepted by required reviewers.

## Gate 3: Domain Spec Approved
- Future-state process approved
- Reporting impact reviewed
- Migration assumptions reviewed

### Gate 3 Evidence Cues

- Approved domain spec describing future-state workflow and bounded scope.
- Reporting and owner-value review notes showing KPI, report, and reconciliation impact.
- Migration assumptions record showing data scope, archive decisions, and dependency on discovery evidence.

### Gate 3 Pass / Fail Rules

- `Pass` requires the domain scope, reporting impact, and migration assumptions to be explicit enough for build work to start without inventing policy mid-stream.
- `Fail` applies when future-state flow is ambiguous, owner reporting impact is unreviewed, or migration assumptions are implicit.

## Gate 4: Build Approved
- Code reviewed
- Tests passed
- Install/uninstall checks passed

### Gate 4 Required Checks From Engineering Standards

- No direct Odoo core modifications evidenced.
- OCA-first evaluation evidenced before any custom outcome.
- One bounded responsibility per addon evidenced.
- Code reviewed with readable names, focused methods, and explicit security model confirmed.
- Lint passed.
- Tests passed.
- Module dependency review completed.
- Upgrade note attached.
- Security review completed.
- Install/uninstall checks passed.

### Gate 4 Evidence Cues

| Required check | Minimum evidence |
| --- | --- |
| No direct Odoo core modifications | Repository diff, review note, or implementation summary showing no direct patching of Odoo core files. |
| OCA-first evaluation | Evaluation record or review note showing standard and OCA options were checked before approving custom implementation. |
| One bounded responsibility per addon | Domain design note, manifest review, or reviewer confirmation that the addon scope remains single-responsibility, or a cited temporary waiver with remediation plan. |
| Code reviewed | Pull request review, review notes, or equivalent approval showing code quality expectations were checked. |
| Lint | CI job or captured local command output linked to the delivery package. |
| Tests | Automated test results for critical business logic and any bounded manual verification notes. |
| Module dependency review | Manifest and dependency review note covering Odoo standard, OCA, third-party, and custom dependencies. |
| Upgrade note | Change note covering migration assumptions, upgrade impacts, and follow-up work if needed. |
| Security review | Review note covering access rights, record rules, privileged actions, and data exposure risks. |
| Install/uninstall checks | Captured validation that the addon installs, upgrades, and uninstalls without destabilizing the environment. |

### Gate 4 Pass / Fail Rules

- `Pass` requires affirmative evidence for the core rules on no direct core modification, OCA-first evaluation, one bounded responsibility per addon, and install/uninstall safety, plus every applicable required check from `engineering-standards.md`.
- `Conditional pass` is limited to the same meaning defined in `engineering-standards.md`: all core-rule evidence must already be affirmative, all non-waivable required checks must already be complete, and only a bounded follow-up item may remain.
- `Fail` applies when any required check fails, any mandatory core-rule evidence is missing, or a cited waiver does not match the named rule or check.

## Gate 5: Parallel Run Approved
- Process reconciliation passed
- Report reconciliation passed
- Training package ready

### Gate 5 Evidence Cues

- Process reconciliation package comparing target behavior to approved business operation expectations.
- Report reconciliation notes showing owner-facing and operational outputs are acceptable.
- Training package or equivalent enablement materials for the affected business users and reviewers.

### Gate 5 Pass / Fail Rules

- `Pass` requires reconciled process and report outcomes plus training readiness for the rollout slice under review.
- `Fail` applies when operational reconciliation is incomplete, reporting differences are unexplained, or training materials are not ready for the target audience.

## Waiver and Exception Path

- A gate may reference a waiver only when the waiver is approved, time-bounded, linked directly in the gate package, and mapped to the exact named rule or check it affects.
- Waivers cannot legitimize direct Odoo core modification, remove the need to document OCA-first evaluation, or skip mandatory security review, tests, lint, or install/uninstall safety for build approval.
- Any waived criterion must name the risk owner, mitigation, expiry date, remediation expectation, and the gate at which the exception will be re-evaluated.

## Review Cadence

- Gate reviews occur at each planned phase boundary and whenever work requests an out-of-sequence progression.
- Re-run the affected gate review when a major scope, dependency, security, or migration assumption changes.
- Keep gate decisions versioned so later reviewers can trace why a domain moved forward.
