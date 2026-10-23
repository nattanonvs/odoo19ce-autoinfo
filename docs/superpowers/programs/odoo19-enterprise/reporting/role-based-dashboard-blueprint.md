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
| Last updated | 2026-10-21 |

## Purpose

Define the minimum role-based dashboard structure for Wave 0 so later domain waves can build dashboards that match decision needs for owner, management, and operational audiences.

## Scope

- Applies to information hierarchy, decision zones, alert placement, and drill-down boundaries for the first dashboard baseline.
- Applies to dashboard concepts that may later be implemented in Odoo views, BI tooling, or supporting reporting layers.
- Does not prescribe final UI components, exact chart libraries, or production visualization tooling.
- Remains a blueprint baseline only; example zones below describe expected structure, not a claim that the dashboards are already built.

## Implementation Status

- This blueprint stays the structural baseline. Dashboards built against it are tracked outside the Wave 0–5 domain roadmap, in the cross-cutting reporting track:
  - [2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md](../../../specs/2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md) (W6-DASH-FORMULA-RULES) — implemented.
  - [2026-10-16-odoo19-dashboard-phase2-presentation-design.md](../../../specs/2026-10-16-odoo19-dashboard-phase2-presentation-design.md) (W6-DASH-PHASE2) — implemented.
- Both are delivered in module `od19_dashboard`; see `backlog/domain-wave-matrix.md` and `backlog/domain-spec-index.md` for the cross-cutting track.

## Owner Dashboard

| Zone | Intent | Example content |
| --- | --- | --- |
| Executive summary | Show the shortest business status view first. | Revenue trend, margin health, cash exposure, backlog posture |
| Risk and alert zone | Surface the few issues that justify executive attention now. | Critical overdue exposure, control breaches, major delivery risk |
| Trend zone | Show whether performance is improving or degrading. | 30/60/90 day trend lines, comparative period change |
| Drill-down detail | Provide a controlled path from summary or alerts into exception detail without forcing the owner into daily operational triage. | Top exceptions by business unit, overdue exposure detail, margin variance detail |
| Decision support | Present the next action or question to review. | Open exceptions requiring sponsor decision, follow-up queue |

### Owner Dashboard Low-Fidelity First Screen Mock

- Header: reporting period, selected business unit scope, and data freshness cue
- Top summary row: revenue trend, gross margin health, overdue exposure, and backlog posture
- Alert row: top 3 red or yellow issues requiring sponsor attention
- Trend row: 30/60/90 day business trend with brief variance note
- Detail row: business-unit comparison with one-click drill-down into top exception detail
- Decision row: sponsor review queue with named owner and next decision needed

## Management Dashboard

| Zone | Intent | Example content |
| --- | --- | --- |
| Performance summary | Show current outcome against plan or target. | SLA attainment, throughput, collections, conversion |
| Exception zone | Show bottlenecks and recurring failures. | Rework hotspots, overdue approvals, repeated blockers |
| Trend and timeliness | Show whether performance is improving or drifting toward misses. | Approaching deadlines, missed SLA trend, delay distribution |
| Pipeline and workload detail | Show incoming versus completed demand at the level needed for intervention. | Team pipeline aging, workload balance, queue growth |
| Manager action zone | Focus the manager on assignable follow-up work. | Escalation list, owner assignment, unresolved team issues |

### Management Dashboard Low-Fidelity First Screen Mock

- Header: team or domain scope, current operating period, and freshness cue
- Summary row: throughput, SLA attainment, collections or conversion, and workload pressure
- Exception row: top bottlenecks, overdue approvals, and repeated failure patterns
- Trend row: near-breach items and trend in missed targets
- Detail row: incoming demand, aging pipeline, and queue movement
- Action row: manager escalation list with assignee, due date, and expected next step

## Operational Lead Dashboard

| Zone | Intent | Example content |
| --- | --- | --- |
| Priority summary | Show the most important work first. | Items due today, urgent tasks, blocked approvals |
| Alert and blocker zone | Expose work that has stopped moving or is already at risk. | Pending documents, stalled requests, failed validations |
| Pace and deadline trend | Prevent avoidable lateness by showing movement, not just queue size. | Items nearing SLA breach, aging queue segments, inflow versus throughput trend |
| Queue detail | Show the actionable list at the depth needed for execution. | Work-in-progress, completion rate, document-level exceptions |
| Operational actions | Allow immediate follow-up. | Assign, re-prioritize, escalate, or request missing data |

### Operational Lead Dashboard Low-Fidelity First Screen Mock

- Header: queue scope, current shift or day, and data freshness cue
- Priority row: today's highest-priority work items and urgent blockers
- Alert row: stuck workflows, failed validations, and missing-data cases
- Trend row: near-SLA-breach items sorted by urgency and inflow-versus-throughput movement
- Detail row: work-in-progress, completion pace, and document-level exception list
- Action row: immediate actions for assign, re-prioritize, escalate, or request missing information

## Shared Dashboard Rules

- Summary first
- Alerts second
- Trend third
- Detail or drill-down after that
- Action last
- Keep each role focused on the smallest set of indicators needed for action
- Prevent one role from inheriting every metric intended for another role
- Every status color shown in a dashboard should inherit the threshold and quality-cue rules defined in `kpi-reporting-baseline.md`, including `Grey` for unavailable or delayed data

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

- Final screen layout and wireframe polish — addressed per domain board in `W6-DASH-PHASE3` (§3/§4)
- Exact chart selection — addressed per domain board in `W6-DASH-PHASE3` (§4/P2)
- Real-time streaming behavior — **remains deferred** (requires websocket/bus; conflicts with the low-resource principle)

> Permission model implementation for dashboard access is **closed**: record rules were added in phase 2 (`od19_dashboard/security/dashboard_security.xml`, spec `W6-DASH-PHASE2`), so the item was removed from this list.
