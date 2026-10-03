# Current-State Inventory

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md` |
| Artifact owner | Program discovery lead |
| Artifact status | In progress |
| Review status | Pending discovery review |
| Evidence completeness | Partial |
| Source system | Odoo 15 CE |
| Last updated | 2026-10-04 |

## Objective

Capture the minimum evidence required from Odoo 15 CE before redesign decisions are locked in.

## How To Use This Artifact

- Record observed facts from Odoo 15 CE only; do not mix future-state design into discovery evidence.
- Attach evidence references for every completed subsection, including menu path, export filename, query output, screenshot, or repository path.
- Mark unknown items explicitly as `Open`, `Blocked`, or `Not Started` so review can separate evidence gaps from redesign decisions.
- Update this inventory after each discovery pass through Odoo Technical menus, repositories, infrastructure access, or database inspection.

## Evidence and Source Guidance

- Prefer primary evidence from Odoo Technical menus, module source repositories, configuration files, scheduled action definitions, and approved database extracts.
- For each evidence item, capture who collected it, when it was collected, and whether it came from production, staging, or a sanitized copy.
- Separate confirmed evidence from assumptions using labels such as `Confirmed`, `Needs validation`, or `Blocked by access`.
- Link findings back to the legacy namespaces and high-risk domains already known to exist, especially `AUTO-INFO`, `DTR`, Sales Services, Advance, Cheque, and Transportation.

## Status Summary

| Area | Status | Notes |
| --- | --- | --- |
| System Facts | Partial | Admin and Developer Mode access are known; version and company scope still need cited evidence. |
| Custom Landscape | Partial with Gate 1 equivalent attached | Prior technical scan identified `AUTO-INFO`, `DTR`, and named hotspot domains; the concrete interim custom map below is reviewable now, while full exports are still pending attachment. |
| Domain Inventory | Partial | Several hotspot domains are now named in the Gate 1 equivalent map below, but company-wide domain coverage is not complete. |
| Reports and Owner Information Needs | Open | Owner-facing KPI and alert inventory still needs direct evidence capture. |
| Data Conditions | Open | Data quality and archival decisions still need database-level evidence. |
| Integrations and Security-Risk Hotspots | Open | Explicit interface, credential, and privileged-automation review is still pending. |

## Required Sections

### System Facts
- Odoo edition and version
- Companies in scope
- Admin access status
- Developer mode status

#### Review Notes

- Status: `Partial`
- Evidence/source guidance:
  - Capture the exact Odoo 15 CE version string from the About dialog, module metadata, or server package information.
  - Export the companies list in scope from configuration or `res.company` with evidence attached.
  - Record the named admin account or access path used for discovery and whether the access is direct, delegated, or temporary.
- Known findings:
  - Admin access has been confirmed for discovery.
  - Developer Mode and Technical menu access have been used successfully in prior scans.
- Open questions/blockers:
  - Exact edition/version evidence still needs a cited source artifact.
  - Final company scope list has not yet been attached to this document.

### Custom Landscape
- Custom modules by namespace
- Custom models by namespace
- Menu-to-action-to-model map
- Automated actions, server actions, scheduled actions

#### Review Notes

- Status: `Partial`
- Evidence/source guidance:
  - Export addon/module inventory grouped by namespace, including repository or filesystem location.
  - Extract the menu-to-action-to-model map from Odoo Technical menus so domain owners can trace UI entry points to custom models.
  - Record every automated action, server action, and scheduled action with trigger, scope, and execution user.
- Gate 1 custom map equivalent:

| Discovery slice | Current status | Confirmed scope/evidence wording | Evidence basis already known | Follow-up still required before build planning closes discovery |
| --- | --- | --- | --- | --- |
| `AUTO-INFO` namespace | `Confirmed namespace / partial inventory` | Prior discovery confirms `AUTO-INFO` as a legacy custom namespace with custom models and UI entry points already observed; this is sufficient to treat it as in-scope custom landscape, but not yet sufficient to claim a complete module export. | Admin and Technical-menu discovery passes; prior custom-model and UI-entry-point mapping noted in discovery summaries. | Attach module/export list, repository paths, and exact menu-action-model references. |
| `DTR` namespace | `Confirmed namespace / partial inventory` | Prior discovery confirms `DTR` as a legacy custom namespace with business-unit extensions and custom models; scope is known, but the namespace inventory is still incomplete. | Admin and Technical-menu discovery passes; prior summaries explicitly identify `DTR` as a major customization source. | Attach addon inventory, code/repository paths, and automation usage by domain. |
| Sales Services / Claims / Warranty / Service Card / Product Return | `Confirmed hotspot domain / partial map` | Prior discovery confirms Sales Services as one of the most complex custom domains, with Claims, Warranty, Service Card, and Product Return flows already identified as follow-on design scope. | Technical-menu scan and prior domain summaries naming Sales Services and related after-sales flows. | Capture menu tree, model list, approvals, reports, and automation points. |
| Advance / Cheque / Money In Analysis | `Confirmed hotspot domain / partial map` | Prior discovery confirms finance-control customization around Advance and Cheque, with Money In Analysis named as a follow-on wave; this is enough to classify Finance Controls as a custom hotspot pending detailed export. | Prior domain summaries and wave planning artifacts naming Advance, Cheque, and Money In Analysis. | Attach workflow evidence, model-level inventory, reconciliation reports, and privileged action review. |
| Stock Requests / Transportation / logistics extensions | `Confirmed hotspot domain / partial map` | Prior discovery confirms Transportation and related logistics extensions as custom hotspots, including links to Purchase/Inventory-adjacent behavior; this is a real custom area, not a hypothetical placeholder. | Prior domain summaries identifying Transportation, logistics extensions, and custom transport scope. | Capture source modules, operational flows, external touchpoints, and approval boundaries. |
| Employees / Attendances / Time Off | `Known operational domain / evidence still shallow` | Prior discovery confirms active use of Attendances and HR operational data; this domain is in scope for discovery, but the custom-versus-standard boundary remains less clear than the finance and service hotspots above. | Prior product scan, Attendances access confirmation, and wave planning artifacts. | Distinguish standard behavior from custom overlays and capture security/access-risk evidence. |
| Menu-to-action-to-model traceability | `Partial evidence` | The discovery process has already used Technical menus to trace UI entry points to models, so Gate 1 can review this as an evidence-backed method already exercised, but the program package still lacks the exported trace matrix. | Prior discovery notes explicitly state Technical-menu scanning was used to map UI entry points and custom models. | Attach export or table of menus, actions, models, and owning domains. |
| Automated / server / scheduled actions | `Known risk area / explicit inventory pending` | Prior discovery confirms the environment uses server actions and automated actions; therefore automation risk is known and in scope, but the executable inventory is not yet attached. | Prior discovery notes explicitly mention server actions and automated actions in use. | Attach the full automation inventory with trigger, user, target model, and side-effect notes. |
- Known findings:
  - Prior discovery identified extensive customization under the `AUTO-INFO` and `DTR` namespaces.
  - Technical-menu scanning has already been used to map custom models and UI entry points.
  - The table above is the current Gate 1 custom-map equivalent: it is concrete enough for review, but it does not replace the need for later evidence exports.
- Open questions/blockers:
  - The full namespace inventory has not yet been attached as exported evidence.
  - Privileged actions and cron jobs still need explicit risk review for financial, HR, and integration side effects before discovery can claim full completeness.

### Domain Inventory
- Finance
- Sales
- Service
- Logistics
- HR and operations

#### Review Notes

- Status: `Partial`
- Evidence/source guidance:
  - Capture active models, menus, workflows, approvals, and reporting outputs for each domain.
  - Distinguish standard Odoo behavior from OCA behavior and custom behavior so later keep/refactor/replace/retire decisions are evidence-based.
  - Highlight dependencies between domains, especially where shared master data or approvals cross Finance, Logistics, Service, and HR.
- Known findings:
  - Sales Services appears to be one of the most complex custom domains.
  - Finance-related customizations include Advance and Cheque flows.
  - Transportation and other logistics-related extensions are known hotspots for later analysis.
- Open questions/blockers:
  - Full domain-by-domain evidence is not yet complete for all business areas.
  - Shared data ownership and approval boundaries between domains still need confirmation.

### Reports and Owner Information Needs
- Operational reports in use
- Management reports in use
- KPI expectations
- Alerts/signals needed by owner

#### Review Notes

- Status: `Open`
- Evidence/source guidance:
  - Capture each report with business owner, audience, source model, refresh frequency, and whether it is standard, custom, spreadsheet-based, or external.
  - Record which KPIs are used for owner decision-making versus day-to-day operations.
  - Note any alerts, escalation thresholds, or exception signals that trigger management intervention.
- Known findings:
  - The program requires explicit owner-value reporting and KPI visibility as a standing project rule.
- Open questions/blockers:
  - No evidence-backed report catalog is attached yet.
  - Owner-critical alerts and management exception views still need discovery interviews or report exports.

### Data Conditions
- Master data health
- Duplicate patterns
- Orphaned records
- Archival and migration decisions

#### Review Notes

- Status: `Open`
- Evidence/source guidance:
  - Profile key master data sets for duplicates, inactive records, broken references, and cross-company inconsistencies.
  - Record archival candidates, legal retention constraints, and data sets that should not be migrated into Odoo 19 CE.
  - Cite whether findings come from production, staging, or sanitized copies.
- Known findings:
  - The legacy system is being used as a reference source, not as a template to clone directly into the target design.
- Open questions/blockers:
  - Database-level evidence has not yet been attached for duplicate and orphan analysis.
  - Migration cutoff and archive policy still need owner and technical confirmation.

## Additional Review Coverage

### Integration Hotspots

- Capture every external integration, file drop, import/export routine, bank interface, email flow, API dependency, and scheduled sync that touches Odoo 15 CE.
- For each integration, record the system owner, auth method, direction of data flow, failure handling, and whether replacement or redesign is likely in Odoo 19 CE.
- Flag integrations that depend on custom models under `AUTO-INFO` or `DTR`, because these may hide business rules outside standard Odoo flows.

### Security-Risk Hotspots

- Review automated actions, server actions, and scheduled actions that run with elevated users or modify finance, HR, approval, or inventory records.
- Identify shared technical accounts, embedded credentials, direct SQL usage, shell scripts, and unrestricted exports/imports.
- Record any menu, record-rule, or approval bypass behavior that would create migration or audit risk if carried forward without redesign.

## Open Questions and Blockers

- Which evidence repository or naming convention should reviewers use for screenshots, exports, and query outputs linked from this file?
- Has a safe staging or sanitized environment been approved for deeper data-quality profiling?
- Which business owners will sign off the reporting and KPI expectations for each domain?
- Are there legacy integrations or scheduled jobs outside Odoo that must be inventoried here as part of discovery scope?
