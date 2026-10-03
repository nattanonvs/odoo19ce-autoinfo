# Role-Based Dashboard Blueprint

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md` |
| Artifact owner | Program analytics lead |
| Required reviewers | Business sponsor, delivery lead, UX or reporting reviewer |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before each dashboard build scope, after major role feedback, and when KPI priorities change materially |
| Last updated | 2026-10-04 |

## Purpose

Define the minimum role-based dashboard structure for Wave 0 so later domain waves can build dashboards that match decision needs for owner, management, and operational audiences.

## Scope

- Applies to information hierarchy, decision zones, alert placement, and drill-down boundaries for the first dashboard baseline.
- Applies to dashboard concepts that may later be implemented in Odoo views, BI tooling, or supporting reporting layers.
- Does not prescribe final UI components, exact chart libraries, or production visualization tooling.

## Owner Dashboard

| Zone | Intent | Example content |
| --- | --- | --- |
| Executive summary | Show the shortest business status view first. | Revenue trend, margin health, cash exposure, backlog posture |
| Risk and alert zone | Surface the few issues that justify executive attention now. | Critical overdue exposure, control breaches, major delivery risk |
| Drill-down entry | Provide a controlled path from executive summary or alert signals into exception detail without forcing the owner into daily operational triage. | Top exceptions by business unit, overdue exposure detail, margin variance detail |
| Trend zone | Show whether performance is improving or degrading. | 30/60/90 day trend lines, comparative period change |
| Business unit comparison | Show relative performance across units or domains. | Sales versus service versus logistics comparison |
| Decision support | Present the next action or question to review. | Open exceptions requiring sponsor decision, follow-up queue |

### Owner Dashboard Low-Fidelity First Screen Mock

- Header: reporting period, selected business unit scope, and data freshness cue
- Top summary row: revenue trend, gross margin health, overdue exposure, and backlog posture
- Alert row: top 3 red or yellow issues requiring sponsor attention
- Trend row: 30/60/90 day business trend with brief variance note
- Comparison row: business-unit comparison with one-click drill-down into top exception detail
- Decision row: sponsor review queue with named owner and next decision needed

## Management Dashboard

| Zone | Intent | Example content |
| --- | --- | --- |
| Performance summary | Show current outcome against plan or target. | SLA attainment, throughput, collections, conversion |
| Pipeline and workload | Show incoming versus completed demand. | Team pipeline aging, workload balance, queue growth |
| Exception zone | Show bottlenecks and recurring failures. | Rework hotspots, overdue approvals, repeated blockers |
| SLA and timeliness | Show timeliness and risk of future misses. | Approaching deadlines, missed SLA count, delay distribution |
| Manager action zone | Focus the manager on assignable follow-up work. | Escalation list, owner assignment, unresolved team issues |

### Management Dashboard Low-Fidelity First Screen Mock

- Header: team or domain scope, current operating period, and freshness cue
- Summary row: throughput, SLA attainment, collections or conversion, and workload pressure
- Pipeline row: incoming demand, aging pipeline, and queue movement
- Exception row: top bottlenecks, overdue approvals, and repeated failure patterns
- Timeliness row: near-breach items and trend in missed targets
- Action row: manager escalation list with assignee, due date, and expected next step

## Operational Lead Dashboard

| Zone | Intent | Example content |
| --- | --- | --- |
| Today's priority queue | Show the most important tasks first. | Items due today, urgent tasks, blocked approvals |
| Pending and stuck workflows | Expose work that has stopped moving. | Pending documents, stalled requests, failed validations |
| Near deadline zone | Prevent avoidable lateness. | Items nearing SLA breach, aging queue segments |
| Execution health | Show whether the team is keeping pace. | Queue inflow versus throughput, completion rate, work-in-progress |
| Operational actions | Allow immediate follow-up. | Assign, re-prioritize, escalate, or request missing data |

### Operational Lead Dashboard Low-Fidelity First Screen Mock

- Header: queue scope, current shift or day, and data freshness cue
- Priority row: today's highest-priority work items and urgent blockers
- Pending row: stuck workflows, failed validations, and missing-data cases
- Deadline row: near-SLA-breach items sorted by urgency
- Health row: inflow versus throughput, work-in-progress, and completion pace
- Action row: immediate actions for assign, re-prioritize, escalate, or request missing information

## Shared Dashboard Rules

- Summary first
- Alerts second
- Trend third
- Drill-down after that
- Keep each role focused on the smallest set of indicators needed for action
- Prevent one role from inheriting every metric intended for another role

## Red / Yellow / Green Logic

| Status | Meaning | Action cue |
| --- | --- | --- |
| Red | Must be handled immediately because the issue is already breaching control, deadline, or business tolerance. | Escalate now and assign an owner. |
| Yellow | Requires close monitoring because the indicator is drifting or approaching a breach. | Review within the current operating cycle. |
| Green | Within acceptable operating range for the intended audience. | No escalation needed unless trend changes. |
| Grey | Data is unavailable, delayed, or intentionally not used for the current context. | Verify data readiness before acting. |

## Drill-Down Rules

| Audience | Allowed drill-down depth | Not intended for |
| --- | --- | --- |
| Owner | Summary and exception detail | Daily document triage or queue management |
| Management | Team, domain, and comparative detail | Broad executive-only portfolio view or raw transaction overload |
| Operational lead | Queue and document-level detail | Cross-program strategic analysis without action context |

## Information Design Rules

- Put the highest-value decision signal in the first visible zone.
- Limit each dashboard to a manageable number of primary signals so users do not lose the action path.
- Pair trend with current status so users do not overreact to a single-day change.
- Show exception context near the signal that triggered it.
- Use comparison views only when they help the role choose where to intervene.

## Review Questions

- Does the first screen answer what this role should do next?
- Are alerts limited to actionable exceptions rather than general noise?
- Can the user move from summary to the right level of detail without skipping context?
- Is any metric present only because it is easy to display rather than useful for a decision?

## Deferred Topics

- Final screen layout and wireframe polish
- Exact chart selection
- Real-time streaming behavior
- Permission model implementation for dashboard access
