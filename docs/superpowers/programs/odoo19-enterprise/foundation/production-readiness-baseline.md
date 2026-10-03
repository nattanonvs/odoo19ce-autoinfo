# Production Readiness Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md` |
| Artifact owner | Architecture lead |
| Required reviewers | Program engineering lead, security reviewer, delivery lead |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before go-live, before major topology change, and after any production incident with platform impact |
| Last updated | 2026-10-04 |

## Purpose

Define the minimum production controls, ownership, release evidence, and operational stop conditions required before the program can treat a delivery slice as production-ready.

## Scope

- Applies to runtime topology, secrets handling, backups, restore validation, logging, monitoring, release execution, and incident readiness for the production environment.
- Applies to go-live decisions, production change approval, and major platform adjustments that affect service continuity.
- Complements `environment-and-delivery-baseline.md` and the build-focused controls in `engineering-standards.md`.

## Production Topology Expectations

| Layer or concern | Minimum expectation | Decision cue |
| --- | --- | --- |
| App layer | Odoo application nodes, services, or containers are identifiable, support controlled rollout, and have documented configuration ownership. | If the team cannot state how to restart, scale, or verify the app layer safely, the platform is not ready. |
| Database layer | PostgreSQL ownership, backup method, restore target, and maintenance expectations are defined. | If database recovery depends on undocumented operator knowledge, stop go-live approval. |
| Worker and cron layer | Background execution responsibilities, schedule ownership, and failure visibility are documented. | If queued jobs can fail silently or pile up without alerting, readiness is incomplete. |
| Reverse proxy and ingress | Entry points, TLS ownership, routing behavior, and upstream dependency expectations are defined. | If traffic control or certificate handling is unclear, release risk remains uncontrolled. |
| File storage and backup scope | Filestore location, retention expectation, and backup inclusion are explicit. | If the filestore is excluded from backup or restore planning, production readiness fails. |

## Ownership and Response Roles

| Role | Minimum responsibility |
| --- | --- |
| Config owner | Maintains runtime configuration source, environment variables, and approved operational overrides. |
| Deployment owner | Executes releases, confirms pre-release evidence, and records release outcomes. |
| Security reviewer | Reviews secrets handling, privileged access, and production exposure risks. |
| Incident first responder | Owns first diagnosis, escalation, and service-restoration coordination during incidents. |
| Backup or platform owner | Confirms backup completion, restore capability, and platform housekeeping requirements. |

## Safety Baselines

- Secrets must not live in source code, committed configuration, or review artifacts intended for broad distribution.
- Backups must cover both the database and the filestore for every production release scope.
- Restore must be testable on a defined target and reviewed often enough that the team trusts the recovery path.
- Logging and monitoring must exist before go-live, not as a post-release intention.
- Rollback or forward-fix strategy must be defined before release approval.

## Go-Live Control Block

| Decision question | Ready when | Block when |
| --- | --- | --- |
| Can the system be operated safely? | Named owners exist for config, release, security, incident response, and backup scope. | Ownership is implied, split informally, or missing for a critical production area. |
| Can the system be recovered? | Backup scope, retention expectation, and restore path are documented and previously exercised or explicitly validated. | Restore has never been demonstrated, backup coverage is partial, or recovery depends on undocumented steps. |
| Can the system be observed? | Logs, key health signals, and alert routes exist for the app, database, workers, and ingress path. | Failures would be discovered only by end users or manual log inspection after damage occurs. |
| Can the release be reversed or contained? | Rollback or containment actions are defined, owned, and feasible within the release window. | The team can only say "we will fix it live" with no bounded rollback or containment plan. |

## Minimum Release Evidence

| Evidence area | Minimum requirement |
| --- | --- |
| Topology summary | Short record of the active production shape and which components are in scope for the release. |
| Secrets control | Evidence showing secrets are externalized and access is limited to named operators. |
| Backup and restore | Current backup confirmation plus restore procedure or recent restore proof. |
| Monitoring and alerting | Named signals, alert route, and response owner for key production failure modes. |
| Release plan | Deployment steps, rollback expectation, post-release checks, and release owner. |

## Production Approval Rules

- Approve production release only when the release package shows operational ownership, backup coverage, observability, and rollback readiness together.
- Delay approval when the application change is ready but the platform evidence is stale, partial, or owned by people who are unavailable for the release window.
- Reject approval when secrets handling, backup scope, restore confidence, or incident response ownership is still unresolved.
- Treat "we will monitor manually" as insufficient unless the manual check is named, time-bounded, and assigned to a responsible operator.

## Incident and Recovery Expectations

- Every production-impacting release must identify who declares rollback, who performs it, and who confirms service health afterward.
- Incident notes should capture which layer failed, what signal detected it, and whether the documented recovery path matched reality.
- Repeated incidents caused by the same missing evidence should trigger an update to this baseline before the next release.

## Exception Path

- Production readiness exceptions are rare and must be approved in writing by the architecture lead and delivery lead with security input when relevant.
- Exceptions cannot waive backup coverage, secrets hygiene, or the need for a named recovery path.
- Any approved exception must define scope, compensating control, owner, expiry date, and the next review checkpoint.

## Review Cadence

- Review this baseline before first go-live, before major release types, and after any material platform or incident change.
- Reconfirm the evidence model whenever topology, backup tooling, or monitoring architecture changes.
- Update this baseline when the program learns a recurring operational lesson that should become standard policy.
