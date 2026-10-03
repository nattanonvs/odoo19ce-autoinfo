# Access and Readiness Checklist

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md` |
| Artifact owner | Program discovery lead |
| Artifact status | In progress |
| Overall readiness | Partial |
| Review status | Pending evidence completion |
| Last updated | 2026-10-04 |

## Readiness State Legend

- `Ready`: access is approved, usable, and backed by evidence.
- `Partial`: some access exists, but required evidence, scope, or operational constraints are incomplete.
- `Blocked`: needed for discovery, but waiting on approval, credentials, or environment setup.
- `Not Started`: no evidence has been attached yet.
- `N/A`: explicitly not required for this program or domain.

## Evidence Requirements

- Each line item should capture the approver or provider, date confirmed, environment scope, and a link or reference to the evidence.
- When access is constrained, record the limitation explicitly, such as read-only, time-boxed, sanitized-only, or business-hours-only.
- If a requirement is blocked, capture the blocking owner and next action so program review can escalate quickly.

## Readiness Summary

| Area | Status | Notes |
| --- | --- | --- |
| Application Access | Partial | Admin, Developer Mode, and Technical access are known from prior discovery, but evidence links should be attached here. |
| Infrastructure Access | Not Started | Shell, config, and addon path access still need explicit confirmation or approval. |
| Data Access | Not Started | Dump, sanitized copy, and extraction approvals still need formal tracking. |
| Source and Integration Access | Not Started | Repository, deployment, integration, and test-credential evidence is not attached yet. |
| Security and Risk Access | Not Started | High-risk automation, secret handling, and audit-log access still need explicit review. |

## Application Access
- [ ] Odoo 15 admin access confirmed
- [ ] Developer mode access confirmed
- [ ] Technical menu access confirmed

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Odoo 15 admin access confirmed | Ready | Prior discovery session confirmed admin access in Odoo 15 CE. | Program discovery lead | Add a durable evidence reference, such as screenshot or access approval record. |
| Developer mode access confirmed | Ready | Prior discovery used Developer Mode successfully. | Program discovery lead | Record the exact enablement path and account used. |
| Technical menu access confirmed | Ready | Prior technical scan used Technical menus for models, menus, and actions. | Program discovery lead | Attach menu-path evidence for auditability. |

## Infrastructure Access
- [ ] Read-only production access approved
- [ ] Clone or staging shell access approved
- [ ] Odoo configuration files available
- [ ] Addon paths available

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Read-only production access approved | Not Started | No approval record attached yet. | Infrastructure owner | Confirm whether discovery is limited to application UI or may include read-only server access. |
| Clone or staging shell access approved | Not Started | No shell-access evidence attached yet. | Infrastructure owner | Needed for safer deep inspection if production shell is restricted. |
| Odoo configuration files available | Not Started | No config-file artifact linked yet. | Infrastructure owner | Required to confirm addon paths, workers, mail, and integration settings. |
| Addon paths available | Not Started | No filesystem or config evidence attached yet. | Infrastructure owner | Needed to reconcile deployed code with repositories and namespaces. |

## Data Access
- [ ] Full database dump provided
- [ ] Sanitized copy provided
- [ ] Master data extraction approved

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Full database dump provided | Not Started | No dump handoff record attached yet. | DBA or infrastructure owner | Confirm whether a full dump is permitted for discovery. |
| Sanitized copy provided | Not Started | No sanitized environment evidence attached yet. | DBA or security owner | Preferred for data profiling and wider reviewer access. |
| Master data extraction approved | Not Started | No approval or export evidence attached yet. | Data owner | Required for product, customer, vendor, employee, and financial master-data profiling. |

## Source and Integration Access
- [ ] Custom addon repositories available
- [ ] Deployment scripts available
- [ ] Integration inventory available
- [ ] Test credentials available where needed

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Custom addon repositories available | Not Started | No repository URLs or paths attached yet. | Engineering owner | Needed to review `AUTO-INFO`, `DTR`, and other custom namespaces. |
| Deployment scripts available | Not Started | No deployment artifact linked yet. | DevOps owner | Needed to understand environment drift and non-Odoo automation. |
| Integration inventory available | Not Started | No approved inventory attached yet. | Integration owner | Required to identify APIs, file drops, mail flows, and sync jobs. |
| Test credentials available where needed | Not Started | No credential-access process linked yet. | System owner | Use least-privilege and avoid sharing production credentials directly. |

## Security and Integration Access Readiness

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| High-risk automated actions review approved | Not Started | No approval or export attached yet. | Security or platform owner | Needed for server actions, cron jobs, and privileged automations. |
| Secret and credential storage review approved | Not Started | No evidence attached yet. | Security owner | Confirm where API keys, SMTP credentials, bank credentials, and shared secrets live. |
| Service accounts and elevated users identified | Not Started | No identity inventory attached yet. | Security owner | Needed to assess auditability and least-privilege gaps. |
| Audit-log or operational log access approved | Not Started | No log-access approval attached yet. | Infrastructure owner | Helpful for validating integrations, failures, and unauthorized workarounds. |
| External integration endpoints validated | Not Started | No endpoint inventory attached yet. | Integration owner | Capture owner, auth model, transport, and data sensitivity for each integration. |

## Open Questions and Blockers

- Which owner approves read-only production access, and is there a preferred safer alternative such as staging or sanitized clone?
- Is there an approved evidence repository for screenshots, approvals, config extracts, and repository links used in this checklist?
- Are security owners comfortable exposing secrets indirectly through config review, or is a mediated walkthrough required instead?
- Which integrations require separate third-party approvals or test credentials before discovery can validate them?
