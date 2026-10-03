# KPI and Reporting Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md` |
| Artifact owner | Business sponsor with program analytics lead |
| Required reviewers | Business sponsor, delivery lead, architecture lead |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before each domain spec approval, before KPI scope expansion, and after major reporting feedback from business users |
| Last updated | 2026-10-04 |

## Purpose

Define the minimum KPI and reporting contract for Wave 0 so owner, manager, and operational lead audiences receive information designed for decisions rather than raw transaction noise.

## Scope

- Applies to KPI definitions, reporting intent, signal design, and dashboard-facing information contracts used by the Odoo 19 CE Enterprise program.
- Applies to role-based reporting planned during Wave 0 and refined during later domain waves.
- Does not define final data models, ETL design, or finished dashboard implementation inside Odoo.

## KPI Layers

| Layer | Primary audience | Main question answered | Decision horizon |
| --- | --- | --- | --- |
| Owner level | Owner, sponsor, executive leadership | Is the business healthy, profitable, cash-safe, and trending in the right direction? | Weekly to monthly |
| Management level | Department heads, functional managers, cross-domain leads | Which team, domain, or business unit is underperforming or drifting from plan? | Daily to weekly |
| Operational level | Team leads, supervisors, queue owners | Which work items need action now to prevent delay, SLA breach, or control failure? | Intraday to daily |

## KPI Design Principles

- Every KPI must support a named business decision, not just a visibility preference.
- Every KPI must have a business owner, an intended audience, and a review cadence.
- Every KPI must be traceable to a trusted source or explicitly marked provisional during discovery.
- KPI sets should move from summary to exception to drill-down, not start with document-level detail.
- If a metric cannot trigger a decision, escalation, or follow-up action, it should not be promoted into the baseline set.

## Reporting Contract

Threshold definition is mandatory for every baseline report. A report is not review-ready unless its status boundaries are explicitly defined.

| Contract field | Minimum requirement |
| --- | --- |
| Business question | State the decision question the report answers. |
| Audience | Name the role or team expected to use the output. |
| Decision supported | State what decision, escalation, or follow-up the user can take from the report. |
| Source data | Identify the originating model, dataset, or discovery assumption used for the report. |
| Refresh cadence | Define how often the report should update or be reviewed. |
| Threshold definition | Define the threshold or status logic required to classify the output, including red/yellow/green or equivalent business boundaries. |
| Drill-down depth | Define the deepest level each audience is allowed to inspect. |
| Quality cue | State how the user knows the information is complete, delayed, estimated, or unavailable. |

## Minimum KPI Categories

| Category | Owner view | Management view | Operational view |
| --- | --- | --- | --- |
| Financial health | Revenue trend, gross margin, cash conversion, overdue exposure | Budget variance, receivable aging by team, collection trend | Billing backlog, pending approvals affecting invoicing |
| Delivery performance | On-time fulfillment rate, service backlog trend | SLA compliance by team, cycle time by process | Today's due items, stuck workflow count, near-deadline queue |
| Control and risk | Exception count, unresolved critical alerts, high-risk accounts | Policy breaches, recurring rework, approval bottlenecks | Missing data, blocked documents, failed validations |
| Growth and pipeline | Pipeline conversion, sales mix, business-unit comparison | Funnel stage aging, workload balance, team capacity pressure | Assigned actions, queue inflow versus throughput |

## Reporting Contract Template

Use this minimum template whenever a new KPI report is proposed:

The template is incomplete unless the report owner states a quality cue that tells readers whether the numbers are complete, delayed, estimated, or unavailable.

| Field | Example prompt |
| --- | --- |
| Report name | What is the report called? |
| Business question | What decision does this answer? |
| Consumer | Who uses it first? |
| Trigger or cadence | When is it reviewed? |
| Data source | Which model or source artifact feeds it? |
| Threshold definition (required) | What counts as good, warning, or bad, and where are the exact business boundaries? |
| Quality cue (required) | How should the reader interpret the trust level of this output: complete, delayed, estimated, or unavailable? |
| Drill-down path | How far can the user inspect detail? |
| Owner | Who keeps the report definition correct? |

## Signal and Alert Model

| Signal type | Purpose | Trigger condition | Typical owner | Escalation path | Expected response |
| --- | --- | --- | --- | --- | --- |
| Health signals | Show whether a business area is stable or drifting. | Fires when a KPI crosses its warning or critical threshold, or when negative trend movement persists across the defined review window. | Owner or manager | Escalate from report owner to named business owner, then to sponsor review if the condition remains unresolved through the agreed review cycle. | Review trend, confirm root cause, and decide whether intervention is needed. |
| Control alerts | Show policy, compliance, or approval exceptions that need oversight. | Fires when a policy breach, approval breach, or control exception exceeds allowed tolerance. | Manager or control owner | Escalate from control owner to functional manager, then to executive sponsor or risk authority when the breach is critical, repeated, or unresolved. | Investigate cause, assign action, and confirm containment. |
| Operational alerts | Show work items at risk of delay, failure, or queue congestion. | Fires when queue age, SLA risk, blocked status, or validation failure passes the configured operating threshold. | Operational lead | Escalate from queue owner to team lead, then to functional manager if recovery does not happen within the expected response window. | Reprioritize work, unblock documents, or escalate capacity issues. |

## Severity Ownership

| Severity | Meaning | Escalation owner | Expected response window |
| --- | --- | --- | --- |
| Critical | Immediate business, cash, or control risk | Executive sponsor or named domain lead | Immediate same-day action |
| High | Material underperformance or repeatable process risk | Functional manager | Same day to next working day |
| Medium | Noticeable drift that requires monitoring and follow-up | Team lead or process owner | Within planned review cycle |
| Low | Informational or emerging trend | Report owner | Track and reassess during routine review |

## Baseline Review Rules

- Promote a KPI into the baseline only after its audience, decision use, and source logic are understood well enough to review.
- Mark discovery-dependent metrics as provisional until the domain spec confirms source fields and business logic.
- Remove duplicate measures that restate the same issue at multiple levels without adding a new decision.
- Review alert fatigue risk whenever more than a few exceptions can fire at the same time for one audience.
- Do not approve an alert baseline entry unless trigger condition, threshold definition, and escalation path are all explicitly documented.

## Deferred Topics

- Final dashboard UI implementation
- Final warehouse or ETL architecture
- Automated threshold tuning
- Full metric dictionary for every future business domain
