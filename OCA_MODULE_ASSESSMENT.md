# OCA Module Assessment — Odoo 19 CE (`odoo19`)

**Role:** Senior Odoo Technical Architect / OCA Module Auditor
**Scope:** Analysis and recommendation only — **no module installed, upgraded, removed, or executed.**
**Evidence basis:** `odoo.conf`, `.gitmodules`, `custom_addons/*`, `third_party/oca/*` manifests, `docs/superpowers/**` governance artifacts, `OCA_MODULE_MATCHING.md`, `GAP_ANALYSIS_OD15_to_OD19.md`.
**Assessment date:** 2026-10-15

> Compatibility note: every OCA submodule referenced below was verified to **declare a `19.0.x` manifest version on branch `19.0`** (291 manifests checked). This is *manifest-level* verification only. It does **not** prove runtime/functional correctness. Where runtime behavior could not be confirmed from source, entries are marked **COMPATIBILITY NOT VERIFIED (runtime)**.

---

# PHASE 1 — CURRENT SYSTEM ANALYSIS

## 1.1 Platform facts

| Item | Finding |
| --- | --- |
| Odoo version | 19.0 (Community Edition) |
| DB schema series | 19.0.1.3 |
| Database | `odoo19` (PostgreSQL 16.15), `dbfilter = ^odoo19$` |
| Edition | **Community (CE)** — no Enterprise modules present |
| HTTP | Nginx 1.27.2 → `http_port = 8070`, `gevent_port = 8072`, `proxy_mode = True` |
| Public URL | `https://pdev-erp.auto-info.com` (Cloudflare Flexible SSL + DDNS) |
| OS | Windows (Local/Pre-UAT); Linux `/var/odoo` (server target) |
| Workers | `workers = 0` (threaded/prefork disabled) |
| Cron threads | `max_cron_threads = 2` |
| Memory guard | soft 2 GB / hard 2.5 GB |
| Time guard | `limit_time_real = 120`, `limit_time_cpu = 60` |
| Logging | `log_level = info`, `logfile = C:\odoo-dev\odoo19\odoo_server.log` |
| DB manager | `list_db = True` ⚠️ |
| Secrets | `db_password` present in `odoo.conf`; `admin_passwd` hashed (pbkdf2) ⚠️ |

## 1.2 Addon architecture

- `addons_path` (absolute, comma-separated): Odoo core `addons`, `custom_addons`, and **13 OCA Git submodules** under `third_party/oca`.
- OCA repositories (all branch `19.0`): `l10n-thailand`, `sale-blanket`, `sale-workflow`, `server-backend`, `server-tools`, `server-ux`, `helpdesk`, `account-financial-tools`, `purchase-workflow`, `tier-validation`, `reporting-engine`, `knowledge`, `website`.
- **Custom modules:** ~80 modules under `custom_addons` with prefix `od19_*`.
- **Installed modules:** ~234 (custom + a subset of OCA + core).

## 1.3 Installed OCA (already present — do NOT re-recommend as "new")

`base_user_role`, `base_exception`, `base_revision`, `base_tier_validation`, `purchase_request_tier_validation`, `sale_blanket_order`, `sale_delivery_state` (sale_stock_delivery_state), `sale_exception`, `sale_order_revision`, `sale_company_currency`, `account_asset_management`, `account_fiscal_year`, `l10n_th_account_tax`, `l10n_th_amount_to_text`, `l10n_th_base_sequence`, `l10n_th_base_utils`, `helpdesk_mgmt`, `helpdesk_mgmt_project`, `helpdesk_product`, `purchase_request`, `report_xlsx`, `report_xlsx_helper`, `document_knowledge`, `document_page`.

## 1.4 Security / access architecture

- **Role-based groups** via `base_user_role` (good baseline).
- **Team-scoped security** in custom helpdesk extensions (`od19_helpdesk_extension`, `od19_internal_issue`) using `security/*.xml` group + record rules.
- **ISO control modules** (9) with departmental document sequences.
- **No record-level audit trail** — `auditlog` is present in the repo but **not installed**.
- **No user/permission change history** — `base_user_role_history` present but not installed.
- **No export restriction** — `base_export_manager` present but not installed.
- **DB manager exposed** (`list_db = True`).
- **Secrets in config file** (`db_password`).

## 1.5 Reporting mechanisms

- Odoo native QWeb PDF + XLSX (`report_xlsx`, `report_xlsx_helper` installed).
- Custom Jasper bridge (`od19_reporting_jasper`), Thai tax reports (`od19_thai_tax_reports`), WHT reports, payment voucher reports, many report-only custom modules.
- **No user-configurable SQL reporting layer** (`bi_sql_editor` / `sql_request_abstract` available but not installed).
- **No report parameterisation** (`report_qweb_parameter` not installed).

## 1.6 Monitoring / logging / automation

- Logging is file-only at `info` level; **no log rotation configured** in Odoo.
- **No error monitoring** (`sentry` not installed).
- **No cron failure alerting** (`scheduler_error_mailer` not installed).
- **No automated backup** (`auto_backup` not installed) — while the production-readiness baseline requires backup + restore evidence before go-live.
- Automation exists via Odoo scheduled/server actions and are explicitly recorded as a **known risk hotspot** in discovery docs.

## 1.7 Identified weaknesses (Phase 1 output)

**Performance**
- `workers = 0` → no worker/multi-process scaling; long requests block the threaded loop. For a multi-user ERP this is the single largest scalability limiter.
- No `limit_request` set (default 8192) → risk of long-lived requests leaking memory in worker mode.
- No log rotation → unbounded log file growth on both Windows and Linux.
- Cron overlap is uncontrolled (two cron threads; no exclusion guard).

**Redundancy / maintainability**
- Six near-parallel numbering modules: `od19_document_sequence`, `od19_accounting_document_sequence`, `od19_quotation_document_sequence`, `od19_purchase_document_sequence`, `od19_project_document_sequence`, `od19_partner_document_sequence`.
- `od19_misc_features` is a grab-bag (logo ISO, sequence guard, data link, runtime guard, repeat-customer report) — cohesion smell.
- Several modules appear to be **stubs or report-only placeholders** with empty `models/`/`report/`/`wizard/` initialisers (e.g. `od19_accounting_reporting`, `od19_accounting_money_in_report`, `od19_service_card`, `od19_accounting_payment_voucher_reports` is report-only by design). **Verify before treating any as functional.**

**Missing controls**
- No audit trail for write/delete, no permission-change history, no export controls.
- No DB bloat/orphan-object hygiene tooling.
- No session management/visibility (who is logged in where).

**Security weaknesses**
- `list_db = True` exposes the database manager endpoint.
- DB password stored in a plaintext-config file; must confirm it is excluded from VCS.
- No proxy-level DB-filter enforcement (`dbfilter_from_header`) despite Nginx + Cloudflare ingress.
- No "technical user" restriction for a service account.

**Observability gaps**
- No centralised error capture, no cron-failure notification, no audit query surface.

**Data-quality risks**
- Year-based document sequences and partner references are custom; without audit trail, back-dated edits are invisible.

---

# PHASE 2 — OCA MODULE DISCOVERY (classified candidates)

All modules below exist in the pinned `third_party/oca` submodules (branch 19.0). "INSTALLED" flags modules already active.

| # | Category | Technical name | Repo | Installed |
| --- | --- | --- | --- | --- |
| 1 | B Monitoring | `auditlog` | server-tools | no |
| 2 | B Monitoring | `sentry` | server-tools | no |
| 3 | B Monitoring | `scheduler_error_mailer` | server-tools | no |
| 4 | D Prevention | `auto_backup` | server-tools | no |
| 5 | C Troubleshooting | `database_cleanup` | server-tools | no |
| 6 | A/D Performance/Prevention | `base_cron_exclusion` | server-tools | no |
| 7 | G Security | `base_export_manager` | server-ux | no |
| 8 | C/G Troubleshooting/Security | `session_db` | server-tools | no |
| 9 | F Reporting | `bi_sql_editor` (+`sql_request_abstract`) | reporting-engine | no |
| 10 | F Reporting | `date_range` (+`date_range_account`) | server-ux | no |
| 11 | F Reporting | `report_qweb_parameter` | reporting-engine | no |
| 12 | E/F Workflow/Reporting | `base_comment_template` | reporting-engine | no |
| 13 | G Security | `base_user_role_history` | server-backend | no |
| 14 | E Workflow | `server_action_mass_edit` | server-ux | no |
| 15 | F Reporting | `report_qr` | reporting-engine | no |
| 16 | D Prevention | `base_cancel_confirm` | server-ux | no |
| 17 | C Troubleshooting | `upgrade_analysis` | server-tools | no |
| 18 | E Utility | `base_technical_features` | server-ux | no |
| 19 | G Security | `base_technical_user` | server-tools | no |
| 20 | D Prevention | `base_optional_quick_create` | server-ux | no |
| 21 | D Prevention | `base_time_window` | server-tools | no |
| 22 | E/D Workflow | `base_substate` | server-ux | no |
| 23 | G Security | `base_menu_visibility_restriction` | server-ux | no |
| 24 | E Utility | `filter_multi_user` | server-ux | no |
| 25 | E Utility | `document_quick_access` | server-ux | no |
| 26 | A Performance | `base_partition` | server-tools | no |
| 27 | G Security | `dbfilter_from_header` | server-tools | no |
| 28 | F Reporting | `report_async` | reporting-engine | no |
| 29 | F Reporting | `report_qweb_element_page_visibility` | reporting-engine | no |
| 30 | F Reporting | `kpi` | reporting-engine | no |
| 31 | B Monitoring | `tracking_manager` | server-tools | no |
| 32 | E Utility | `base_view_inheritance_extension` | server-tools | no |
| 33 | D Prevention | `module_auto_update` | server-tools | no (see P4) |

---

# PHASE 3–5 — DETAILED MODULE ASSESSMENT (17 fields each)

## 1. `auditlog` — Audit Trail ✅ P1

1. **Category:** B — Monitoring & Anomaly Detection
2. **Module name:** Audit Log
3. **Technical name:** `auditlog`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/auditlog`
5. **Purpose:** Full ORM-level audit trail of create/write/unlink on configured models.
6. **Current problem it solves:** No write/delete audit trail exists; ISO 9001 and financial integrity require traceability of record changes, including deletions (`auditlog` records `unlink`). Discovery docs list automations and data edits as unresolved risk.
7. **Key features:** Per-model rule configuration; tracks field-level old→new values; logs user, IP, HTTP method; logs deletions; log search/export; optional DB-level triggers.
8. **Compatibility status:** Manifest `19.0.2.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`, `mail`.
10. **Potential conflicts:** Minimal. Adds DB triggers/log tables. Ensure it is not applied to high-volume transient models (e.g. `mail.message`, `bus.*`, `ir.logging`) to avoid write amplification.
11. **Database impact:** Adds `auditlog.*` tables + optional triggers; grows over time — plan retention.
12. **Security impact:** Positive; exposes historical changes to authorised users only (own ACLs).
13. **Risk level:** **MEDIUM**
14. **Risk explanation:** Hooks into ORM write paths for configured models; mis-scoped rules add measurable write latency and DB growth. Reversible by uninstall but historical log tables should be archived first.
15. **Priority:** **P1**
16. **Recommendation:** Install, then scope to financial/ISO-critical models only.
17. **Reason:** Directly closes the largest governance gap (traceability) required by ISO 9001 and the production-readiness baseline.

## 2. `sentry` — Error Monitoring ✅ P1

1. **Category:** B — Monitoring & Anomaly Detection
2. **Module name:** Sentry Integration
3. **Technical name:** `sentry`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/sentry`
5. **Purpose:** Forwards Python/Odoo exceptions (with traceback, user, context) to a Sentry server.
6. **Current problem it solves:** No centralised error capture; production errors are only in a local log file with no alerting.
7. **Key features:** Logger + WSGI exception hooks, user/context enrichment, configurable DSN and environment, breadcrumbs.
8. **Compatibility status:** Manifest `19.0.1.0.1`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`; Python `sentry-sdk` (external pip requirement).
10. **Potential conflicts:** None expected with Odoo core; requires outbound network to the Sentry endpoint.
11. **Database impact:** **None.**
12. **Security impact:** Sends error context off-box — must scrub PII and never send secrets; use a self-hosted DSN if data residency matters.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** No schema change; the only risks are outbound data privacy and a missing `sentry-sdk` dependency blocking module load.
15. **Priority:** **P1**
16. **Recommendation:** Install with a reviewed DSN and PII-scrubbing config.
17. **Reason:** Highest-value observability gain at near-zero DB cost; prerequisite for the "logging and monitoring before go-live" baseline.

## 3. `auto_backup` — Automated Database Backup ✅ P1

1. **Category:** D — Prevention & Protection
2. **Module name:** Database Auto-Backup
3. **Technical name:** `auto_backup`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/auto_backup`
5. **Purpose:** Scheduled dump of the DB (and optionally filestore) with retention.
6. **Current problem it solves:** Production-readiness baseline requires backup **and filestore** coverage plus a testable restore path; no automated backup module is installed.
7. **Key features:** Per-DB cron backups to a configured folder, retention by count/day, optional filestore backup, manual "backup now", email notify.
8. **Compatibility status:** Manifest `19.0.1.0.1`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** None functional. On Windows, target path/permissions must be writable by the Odoo service account.
11. **Database impact:** None on schema; produces dump files on disk (storage growth — set retention).
12. **Security impact:** Backup files contain full data — store on a protected path, exclude from web exposure, restrict access.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** No ORM/schema change; risks are disk exhaustion (no retention) and unsecured backup artifacts.
15. **Priority:** **P1**
16. **Recommendation:** Install; write backups off the app server; validate a restore separately.
17. **Reason:** Backup + restore is a hard go-live gate. Note: module backup is **not** a substitute for a tested restore and off-site copy.

## 4. `scheduler_error_mailer` — Cron Failure Alerting ✅ P1

1. **Category:** B — Monitoring & Anomaly Detection
2. **Module name:** Scheduler Error Mailer
3. **Technical name:** `scheduler_error_mailer`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/scheduler_error_mailer`
5. **Purpose:** Emails administrators when a scheduled job (`ir.cron`) fails.
6. **Current problem it solves:** Baseline warns that "jobs which fail silently" are a readiness blocker; today a failing cron is invisible.
7. **Key features:** Hooks cron error handling, sends mail to configured recipients with the failing job and traceback.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`, `mail`.
10. **Potential conflicts:** None.
11. **Database impact:** None.
12. **Security impact:** Tracebacks may expose internals — send only to internal admins.
13. **Risk level:** **LOW**
14. **Risk explanation:** Mail-only hook; no schema change; no core override beyond cron error path.
15. **Priority:** **P1**
16. **Recommendation:** Install and route to an internal admin alias.
17. **Reason:** Cheap, direct closure of the "silent cron failure" reliability gap.

## 5. `database_cleanup` — DB Hygiene / Troubleshooting ✅ P1

1. **Category:** C — Troubleshooting & Fixes
2. **Module name:** Database Cleanup
3. **Technical name:** `database_cleanup`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/database_cleanup`
5. **Purpose:** Detect and purge orphaned/hidden DB objects (columns, tables, model data) left by removed modules.
6. **Current problem it solves:** ~80 custom + many OCA modules churn over Waves; leftover columns/tables accumulate and complicate maintenance/upgrades.
7. **Key features:** Purge columns/tables, purge orphaned data rows, purge model/field data, preview before purge, DB-only operations.
8. **Compatibility status:** Manifest `19.0.1.0.6`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** None at install; **destructive operations are manual and must be reviewed**.
11. **Database impact:** High when actually used (drops columns/tables) — but only on explicit admin action.
12. **Security impact:** Restrict to superuser/technical group.
13. **Risk level:** **MEDIUM–HIGH**
14. **Risk explanation:** Capable of irreversible data loss if used without review. Installed itself is harmless; the *operations* are the risk. Mitigate: full backup first, dry-run previews, single-admin access.
15. **Priority:** **P1** (install now, use surgically)
16. **Recommendation:** Install for maintenance capability; never run purges without a fresh backup.
17. **Reason:** Essential long-term maintainability tool for a module-heavy custom ERP; prevents schema rot across Waves.

## 6. `base_cron_exclusion` — Cron Overlap Prevention ✅ P1

1. **Category:** A — Performance & Optimization / D — Prevention
2. **Module name:** Base Cron Exclusion
3. **Technical name:** `base_cron_exclusion`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/base_cron_exclusion`
5. **Purpose:** Prevent the same scheduled job from running concurrently (and mutual-exclusion between jobs).
6. **Current problem it solves:** `max_cron_threads = 2` with no exclusion guard → the same long cron can overlap, causing duplicate processing and load spikes.
7. **Key features:** New "exclusive" field on `ir.cron`; skips a run if the same/allowed job is still running.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** None.
11. **Database impact:** None.
12. **Security impact:** None.
13. **Risk level:** **LOW**
14. **Risk explanation:** Small, additive field on `ir.cron`; no core logic replacement.
15. **Priority:** **P1**
16. **Recommendation:** Install and mark long jobs as exclusive.
17. **Reason:** Direct stability/scalability improvement with negligible risk; complements the threaded (`workers=0`) runtime.

## 7. `base_export_manager` — Export Governance ✅ P1

1. **Category:** G — Access Rights & Security
2. **Module name:** Base Export Manager
3. **Technical name:** `base_export_manager`
4. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/base_export_manager`
5. **Purpose:** Control who can export, and restrict which models/fields may be exported.
6. **Current problem it solves:** Any user can mass-export any list today — a data-exfiltration risk for an ERP holding customer/financial data.
7. **Key features:** Per-model export rules, field allow-lists, per-group export permissions, UI for rule maintenance.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`, `web`.
10. **Potential conflicts:** Low; adds ACLs. Changes export UX — brief users.
11. **Database impact:** Adds small `ir.exports.*` rule tables.
12. **Security impact:** **Positive and significant** — reduces mass-export exposure.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** Data-permission model change; mis-configured rules could over-restrict legitimate exports.
15. **Priority:** **P1**
16. **Recommendation:** Install and default-deny sensitive models.
17. **Reason:** Closes a concrete data-exfiltration gap with a light, well-scoped module.

## 8. `session_db` — Session Control / Admin ✅ P1

1. **Category:** C — Troubleshooting / G — Security
2. **Module name:** Session DB
3. **Technical name:** `session_db`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/session_db`
5. **Purpose:** Store HTTP sessions in the database, enabling session listing/termination.
6. **Current problem it solves:** No way to see or terminate active sessions; needed for incident response and to keep sessions alive across restarts.
7. **Key features:** DB-backed session store, admin session view, force-logout, configurable lifetime.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** Sessions persist across restarts (behavior change users may notice); needs a cleanup cron.
11. **Database impact:** Adds `session.db`-style table with periodic cleanup; write volume on every session refresh (modest).
12. **Security impact:** Positive — centralised session kill for incident response.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** Changes session storage location; if not cleaned, table grows. No core logic override beyond session store.
15. **Priority:** **P1**
16. **Recommendation:** Install with a scheduled session-cleanup job.
17. **Reason:** High operational/security value for a Cloudflare-exposed instance; low blast radius.

## 9. `bi_sql_editor` (+ `sql_request_abstract`) — Configurable Reporting ✅ P1

1. **Category:** F — Data Processing & Reporting
2. **Module name:** BI SQL Editor (dependency: SQL Request Abstract)
3. **Technical name:** `bi_sql_editor`, `sql_request_abstract`
4. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/bi_sql_editor`, `.../sql_request_abstract`
5. **Purpose:** Create read-only SQL views and expose them as list/pivot/graph reports with an export, without writing code.
6. **Current problem it solves:** Owner-value KPIs/aggregations currently require custom Python report modules per report; this allows admin-defined analytical outputs.
7. **Key features:** SQL view editor with validation, auto list/pivot/graph, drill-down actions, materialised views, menu/action generation, access ACLs.
8. **Compatibility status:** Manifest `bi_sql_editor` `19.0.2.0.1`, `sql_request_abstract` `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `sql_request_abstract` → `base`.
10. **Potential conflicts:** None with existing report modules (they coexist). If a custom module already exposes the same query, prefer one source.
11. **Database impact:** Creates DB views/materialised views — schema objects owned by the module; document them.
12. **Security impact:** **Elevated** — raw SQL is powerful. Must be restricted to a trusted group; use a **read-only DB role** for the views.
13. **Risk level:** **MEDIUM**
14. **Risk explanation:** Grants SQL authoring to privileged users and creates persistent DB objects. Misuse risks data exposure or heavy queries. Mitigate with a read-only group and query review.
15. **Priority:** **P1**
16. **Recommendation:** Install for a small set of admins; enforce read-only SQL and review queries.
17. **Reason:** Directly supports the program's owner-value reporting goal and reduces per-report custom code; the alternative (one custom module per report) is more maintenance.

## 10. `date_range` (+ `date_range_account`) — Reporting Periods ✅ P2

1. **Category:** F — Reporting
2. **Technical name:** `date_range`, `date_range_account`
3. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/date_range`, `date_range_account`
4. **Purpose:** Reusable, user-defined date ranges (fiscal periods, custom windows) usable in report filters/domains.
5. **Current problem:** Fiscal-period reporting is currently ad-hoc; `date_range_account` is the standard dependency for period-based accounting reports.
6. **Key features:** Named ranges (fixed/window), generator rules, per-company, integration hooks for reports.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`; `date_range_account` → `account`, `date_range`.
9. **Conflicts:** None (may be pulled in as a dependency by other OCA reporting modules).
10. **DB impact:** Small `date_range.*` tables.
11. **Security impact:** Neutral.
12. **Risk:** **LOW** — additive, light.
13. **Risk explanation:** No core overrides; only new reference data.
14. **Priority:** **P2**
15. **Recommendation:** Install when period-based reporting is configured.
16. **Reason:** Standard building block; low value until reports consume it, then high leverage.

## 11. `report_qweb_parameter` — User-Configurable Report Parameters ✅ P2

1. **Category:** F — Reporting
2. **Technical name:** `report_qweb_parameter`
3. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qweb_parameter`
4. **Purpose:** Add validated, user-editable parameters to QWeb reports (avoid manual template edits).
5. **Current problem:** Report tweaks (company header text, footer notes) require developer edits to XML.
6. **Key features:** Per-report parameter definitions with types/validation, editable at print time.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`.
9. **Conflicts:** None expected; complements custom QWeb/ISO footer reports.
10–11. **DB/Security:** Small parameter tables; neutral security.
12–13. **Risk:** **LOW** — no core override.
14. **Priority:** **P2** / 15. **Recommendation:** Install for reports needing runtime parameters.
16. **Reason:** Reduces developer round-trips for routine report changes.

## 12. `base_comment_template` — Reusable Comment Blocks ✅ P2

1. **Category:** E/F — Workflow / Reporting
2. **Technical name:** `base_comment_template`
3. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/base_comment_template`
4. **Purpose:** Define reusable comment blocks attachable to documents and printable on reports.
5. **Current problem:** Terms/notes are duplicated module-by-module (`od19_sale_terms`, `od19_purchase_terms`) — a single template library would reduce duplication.
6. **Key features:** Template model, domain-based applicability, print/placeholder toggle, replace-vs-append modes.
7. **Compatibility:** Manifest `19.0.0.0.2` (note: very early in the 19.0 port). Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
8. **Dependencies:** `base`.
9. **Conflicts:** Potential **overlap** with the existing custom terms modules — decide one source of truth before adopting.
10–11. **DB/Security:** Small template table; neutral.
12–13. **Risk:** **LOW–MEDIUM** — low technical risk, but early-stage port and functional overlap.
14. **Priority:** **P2** / 15. **Recommendation:** Evaluate against `od19_*_terms` before adopting; do not run both.
16. **Reason:** Good deduplication tool, but only if it replaces (not duplicates) existing custom terms.

## 13. `base_user_role_history` — Permission Change Audit ✅ P2

1. **Category:** G — Access Rights & Security
2. **Technical name:** `base_user_role_history`
3. **OCA repository:** `OCA/server-backend` → `third_party/oca/server-backend/base_user_role_history`
4. **Purpose:** Track changes to users/roles (who changed what, when).
5. **Current problem:** Permission changes are untracked; hard to answer "who granted this access?".
6. **Key features:** History log of role/user changes, current/previous role snapshot, chatter-integrated.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**. Depends on installed `base_user_role`.
8. **Dependencies:** `base_user_role`.
9. **Conflicts:** None (extends the installed role model).
10–11. **DB/Security:** Adds history rows; **positive** security value.
12–13. **Risk:** **LOW** — additive on an already-installed base.
14. **Priority:** **P2** / 15. **Recommendation:** Install alongside `auditlog`.
16. **Reason:** Cheap, targeted security auditability for the RBAC layer.

## 14. `server_action_mass_edit` — Bulk Editing ✅ P2

1. **Category:** E — Utilities & Workflow
2. **Technical name:** `server_action_mass_edit`
3. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/server_action_mass_edit`
4. **Purpose:** Server action type to mass-update fields across selected records.
5. **Current problem:** Bulk corrective updates currently need ad-hoc scripts or per-record edits.
6. **Key features:** Domain-based mass update, preview affected records, per-field values, run from a server action.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`.
9. **Conflicts:** None.
10–11. **DB/Security:** Can write many records at once → restrict to trusted groups; adds action config only.
12–13. **Risk:** **MEDIUM** — mass writes can cause wide unintended changes if the domain is wrong.
14. **Priority:** **P2** / 15. **Recommendation:** Install, restrict to admin/technical groups.
16. **Reason:** Genuine productivity for data-correction tasks, but must be access-guarded.

## 15. `report_qr` — QR Codes on Reports ✅ P2

1. **Category:** F — Reporting
2. **Technical name:** `report_qr`
3. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qr`
4. **Purpose:** Render QR codes in QWeb reports.
5. **Current problem:** Thai e-tax/e-invoice and verification flows increasingly expect QR content on printed documents.
6. **Key features:** QWeb helper to embed QR images from arbitrary payloads.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**; requires Python `qrcode` (external pip dep).
8. **Dependencies:** `base` (+ `qrcode` library).
9. **Conflicts:** None.
10–11. **DB/Security:** None/minimal.
12–13. **Risk:** **LOW** — display-only helper.
14. **Priority:** **P2** / 15. **Recommendation:** Install when a QR-bearing document is required.
16. **Reason:** Small, standard, enables compliance-ready printed outputs.

## 16. `base_cancel_confirm` — Cancellation Guard ✅ P2

1. **Category:** D — Prevention & Protection
2. **Technical name:** `base_cancel_confirm`
3. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/base_cancel_confirm`
4. **Purpose:** Force an explicit confirmation before cancelling records.
5. **Current problem:** Accidental cancellation of orders/invoices is possible without an extra guard — maps to the project's "prevent operational errors" objective.
6. **Key features:** Confirmation wizard on cancel for enabled models.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`.
9. **Conflicts:** None expected; verify against custom cancel overrides in `od19_sale_wizards`/`od19_purchase_wizards`.
10–11. **DB/Security:** None; additive UX guard.
12–13. **Risk:** **LOW** — UI-level guard.
14. **Priority:** **P2** / 15. **Recommendation:** Install for financially significant models.
16. **Reason:** Directly serves the prevention objective at negligible risk.

---

## PHASE 3–5 — COMPACT ASSESSMENT (P3 / P4)

| Module | Cat | Repo | Version (manifest) | Risk | Why | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| `upgrade_analysis` | C | server-tools | 19.0.1.1.4 | MEDIUM | Compares schema/data across versions; key for OCA/custom upgrade safety; requires a reference revision. | P2 |
| `base_technical_features` | E | server-ux | 19.0.1.0.0 | LOW | Exposes technical fields to a dedicated group; aids troubleshooting. | P3 |
| `base_technical_user` | G | server-tools | 19.0.1.0.0 | LOW | Blocks the "technical" user from being used as an API bypass; hardening. | P3 |
| `base_optional_quick_create` | D | server-ux | 19.0.1.0.0 | LOW | Prevents accidental quick-create duplicates. | P3 |
| `base_time_window` | D | server-tools | 19.0.1.0.0 | LOW–MEDIUM | Validates non-overlapping date windows; useful for contracts/planning. | P3 |
| `base_substate` | E | server-ux | 19.0.1.0.0 | LOW | Sub-states for records; overlaps custom status fields. | P3 |
| `base_menu_visibility_restriction` | G | server-ux | 19.0.1.0.0 | LOW | Hide menus per group — cleaner than duplicated menu items. | P3 |
| `filter_multi_user` | E | server-ux | 19.0.1.0.0 | LOW | Shared team filters; UX gain. | P3 |
| `document_quick_access` | E | server-ux | 19.0.1.0.0 | LOW | Quick document links; minor UX. | P3 |
| `base_partition` | A | server-tools | 19.0.1.0.0 | MEDIUM–HIGH | Table partitioning for very large tables (logs/auditlog). Only if growth is proven. | P3 |
| `dbfilter_from_header` | G | server-tools | 19.0.1.0.0 | MEDIUM | Enforce DB filter at the proxy — but the project already pins `dbfilter` and single-DB; only relevant if multi-DB via Nginx. | P3 |
| `report_async` | F | reporting-engine | 19.0.1.0.0 | MEDIUM | Async heavy report generation; needs queue infra. Useful only for large reports. | P3 |
| `report_qweb_element_page_visibility` | F | reporting-engine | 19.0.1.0.0 | LOW | Show/hide elements on first/last page — supports the ISO footer-placement requirement. | P3 |
| `kpi` | F | reporting-engine | 19.0.1.0.1 | LOW–MEDIUM | KPI computation/display; overlaps BI SQL Editor + dashboards. Pick one. | P3 |
| `tracking_manager` | B | server-tools | 19.0.1.0.1 | LOW | Configure field tracking without code; overlaps `auditlog`. | P3 |
| `base_view_inheritance_extension` | E | server-tools | 19.0.1.0.0 | LOW | Richer XPath in inherited views; dev convenience only. | P3 |
| `base_kanban_stage` | E | server-tools | 19.0.1.0.0 | LOW | Generic stage model; only if building kanban pipelines. | P3 |
| `attachment_unindex_content` | A | server-tools | 19.0.1.0.0 | LOW–MEDIUM | Skip attachment content indexing to reduce load — but the project *wants* PDF indexing (pdfminer.six); potential conflict of intent. | P4 for current intent |
| `sequence_python` | E | server-tools | 19.0.1.0.0 | LOW | Python-based sequence values; custom modules may already cover this. | P3 |
| `module_auto_update` | D | server-tools | 19.0.1.0.1 | **HIGH** | Auto-updates modules on code change — dangerous with 13 OCA submodules + ~80 custom modules; can trigger unintended schema upgrades at load. | **P4** |
| `module_change_auto_install` | D | server-tools | 19.0.1.0.0 | MEDIUM | Auto-install modules on file change; same class of risk as above. | P3–P4 |
| `rpc_helper` | C | server-tools | 19.0.1.0.0 | LOW | RPC/debug URL helpers — developer tool only. | P3 |
| `base_search_fuzzy` | A | server-tools | 19.0.1.0.0 | MEDIUM | Trigram search; adds DB extensions and index cost. Only if search is proven slow. | P4 |
| `base_external_dbsource` | — | server-backend | 19.0.1.0.0 | **HIGH** | Arbitrary external DB connections — an exfiltration/attack surface. Not recommended. | **P4** |
| `bus_alt_connection` | — | server-tools | 19.0.1.0.0 | MEDIUM | Alternate bus/IM connection; no need identified. | P4 |
| `iap_alternative_provider` | — | server-tools | 19.0.1.0.0 | MEDIUM | Only if replacing Odoo IAP providers. | P4 |
| `onchange_helper` | E | server-tools | 19.0.1.0.0 | LOW | Developer helper; no business need. | P4 |
| `base_fontawesome` | E | server-tools | 19.0.1.0.0 | LOW | Icon set packaging; Odoo ships icons. | P4 |
| `base_write_diff` | B | server-tools | 19.0.1.0.0 | LOW | Logs write diffs to a file; overlaps `auditlog`. | P4 |

---

# PHASE 6 — DUPLICATION & CONFLICT CHECK

| Candidate | Core/EE | Installed OCA | Custom modules | Verdict |
| --- | --- | --- | --- | --- |
| `auditlog` | Core has `mail.thread` tracking only (field-level, per-model) — **not** a full write/delete audit trail | — | `tracking=True` used in ISO models (partial) | **Adds capability**, no true duplicate |
| `sentry` | Core logs to file only | — | — | No duplicate |
| `auto_backup` | Core has no built-in backup scheduler | — | — | No duplicate |
| `scheduler_error_mailer` | Core silently logs cron failures | — | — | No duplicate |
| `database_cleanup` | `upgrade_analysis` (different purpose) | — | — | No duplicate |
| `base_cron_exclusion` | Core `ir.cron` has no mutual-exclusion | — | `od19_misc_features.runtime_guard` is unrelated (AR/AP guard) | No duplicate |
| `base_export_manager` | Core export has no ACL | — | — | No duplicate |
| `session_db` | Core filesystem sessions | — | — | No duplicate |
| `bi_sql_editor` | Core "Pivot/Graph" only over existing models | `report_xlsx` (output format only) | multiple custom report modules | No duplicate; **reduces** future custom modules |
| `date_range` | Core has fiscal-year util but not user-defined ranges | — | — | No duplicate |
| `report_qweb_parameter` | Core QWeb edits require code | — | — | No duplicate |
| `base_comment_template` | — | — | `od19_sale_terms`, `od19_purchase_terms` | **OVERLAP** — adopt only if replacing the custom terms modules |
| `base_user_role_history` | — | `base_user_role` (installed) | — | Complements installed base |
| `server_action_mass_edit` | Core has server actions but no mass-edit UI | — | — | No duplicate |
| `report_qr` | Core has no QR helper | — | — | No duplicate |
| `base_cancel_confirm` | Core just cancels | — | custom cancel overrides exist | Verify interaction |
| `module_auto_update` | — | — | — | Risky, redundant with controlled deploys |
| `attachment_unindex_content` | — | — | memory: PDF indexing desired (pdfminer.six) | **Conflict of intent** — skip |
| `base_external_dbsource` | — | — | — | **Security anti-recommendation** |

---

# PHASE 7 — OUTPUT

## EXECUTIVE SUMMARY

The `odoo19` instance is a **well-structured Odoo 19 CE greenfield** with a disciplined "OCA-first, custom-second" posture, 13 pinned OCA submodules, and ~80 custom `od19_*` modules covering sales, purchasing, accounting, ISO, helpdesk, and inventory. The architectural foundation is sound. However, the system has a **clear maturity split**: strong *business* coverage, but a **thin operational/governance layer**. Concretely:

1. **No audit trail, no error monitoring, no cron-failure alerting, no automated backup, no export controls, and no session management** are installed — all of which the project's own *production-readiness baseline* requires before go-live, and which ISO 9001 traceability demands.
2. **Runtime is single-process threaded (`workers = 0`)** with no cron-exclusion guard — the principal scalability/stability limiter for a multi-user ERP.
3. **Security posture has two concrete gaps:** the DB manager is exposed (`list_db = True`) and a DB password sits in a plaintext config file (VCS-exclusion must be confirmed).
4. **Maintainability debt** exists in the custom layer: six parallel numbering modules, one "grab-bag" module (`od19_misc_features`), and several apparent stub/report-only modules that should be verified or consolidated.

The recommended action is **not** breadth. A **tight set of ~9 P1 modules** closes the operational, security, and observability gaps with LOW–MEDIUM risk, plus a short P2 list for reporting and workflow. Several available modules are explicitly **not recommended** (auto-update of modules, external DB sources, fuzzy search, attachment de-indexing) because they either add risk or conflict with existing intent.

## TOP RECOMMENDATIONS (highest value)

| Rank | Module | Value | Risk | Priority |
| --- | --- | --- | --- | --- |
| 1 | `auditlog` | Full write/delete traceability (ISO + finance) | MEDIUM | P1 |
| 2 | `sentry` | Centralised error monitoring | LOW–MEDIUM | P1 |
| 3 | `auto_backup` | Backup automation (go-live gate) | LOW–MEDIUM | P1 |
| 4 | `base_export_manager` | Stops mass data exfiltration | LOW–MEDIUM | P1 |
| 5 | `scheduler_error_mailer` | Ends silent cron failures | LOW | P1 |
| 6 | `base_cron_exclusion` | Prevents overlapping crons | LOW | P1 |
| 7 | `database_cleanup` | Long-term schema hygiene | MEDIUM–HIGH (ops only) | P1 |
| 8 | `session_db` | Session visibility/kill | LOW–MEDIUM | P1 |
| 9 | `bi_sql_editor` | Configurable owner-value reporting | MEDIUM | P1 |

## SECURITY RECOMMENDATIONS

- **`auditlog`** (P1) — write/delete traceability, the foundation of any security/ISO audit.
- **`base_export_manager`** (P1) — restrict mass export of customer/financial data.
- **`session_db`** (P1) — see and terminate active sessions during incidents.
- **`base_user_role_history`** (P2) — audit who changed roles/permissions.
- **`base_technical_user`** (P3) — harden the technical/service-user path.
- **`base_menu_visibility_restriction`** (P3) — hide menus per group instead of duplicating menus.
- **Anti-recommendations:** `base_external_dbsource` (HIGH risk exfiltration surface) → **do not install**.

**PROPOSED CHANGE — NOT EXECUTED (security config, no module):**
- Set `list_db = False` in `odoo.conf` and use `dbfilter` alone.
- Confirm `odoo.conf` (containing `db_password`) is excluded from VCS; prefer an env/secret mechanism.
- Consider Nginx-side rate limiting and Cloudflare WAF rules already implied by the DDNS/proxy setup.

## PERFORMANCE RECOMMENDATIONS

- **`base_cron_exclusion`** (P1) — prevents overlapping long jobs under `max_cron_threads = 2`.
- **`base_partition`** (P3) — only if audit/log tables are proven large; otherwise skip.
- **Anti-recommendation:** `base_search_fuzzy` (P4) — adds trigram indexes/DB extensions without proven need.
- **Anti-recommendation:** `module_auto_update` (P4, HIGH) — uncontrolled auto-upgrades across 13 OCA submodules + ~80 custom modules.

**PROPOSED CHANGE — NOT EXECUTED (runtime/config):**
- Evaluate `workers = N` (multi-process) for production and set `limit_request`; verify against memory limits and the Windows deployment.
- Add log rotation for `odoo_server.log` (Odoo does not rotate by default).
- Review `max_cron_threads` against actual job duration once `base_cron_exclusion` is in place.

## OPERATIONS RECOMMENDATIONS

- **`sentry`** (P1) — error capture and alerting.
- **`scheduler_error_mailer`** (P1) — cron failure notification.
- **`auto_backup`** (P1) — scheduled backup + retention.
- **`database_cleanup`** (P1) — purge orphaned schema objects during maintenance windows.
- **`session_db`** (P1) — operational session control.
- **`upgrade_analysis`** (P2) — evidence-based upgrade safety.
- **`rpc_helper`**, **`base_technical_features`** (P3) — admin/diagnostic conveniences.

## WORKFLOW RECOMMENDATIONS

- **`server_action_mass_edit`** (P2) — controlled bulk data corrections.
- **`base_cancel_confirm`** (P2) — guard against accidental cancellations.
- **`base_comment_template`** (P2) — replace duplicated term/note logic (only if it replaces `od19_*_terms`).
- **`filter_multi_user`**, **`base_menu_visibility_restriction`**, **`document_quick_access`** (P3) — UX/productivity.
- **Consolidation (custom, not OCA):** merge the six `*_document_sequence` modules and split `od19_misc_features` — reduces maintenance surface.

## REPORTING & DATA RECOMMENDATIONS

- **`bi_sql_editor` + `sql_request_abstract`** (P1) — admin-defined analytical views/reports without new code.
- **`date_range` + `date_range_account`** (P2) — standard reporting periods.
- **`report_qweb_parameter`** (P2) — user-editable report parameters.
- **`base_comment_template`** (P2) — consistent printed notes.
- **`report_qr`** (P2) — QR on documents (e-tax/e-invoice readiness).
- **`report_qweb_element_page_visibility`** (P3) — first/last-page element control (supports ISO footer placement).
- **Pick ONE of** `kpi` **or** `bi_sql_editor` for KPI dashboards — do not stack both.

---

# DELIVERY NOTE — WHAT WAS NOT DONE

Per the assessment constraints, **nothing was installed, upgraded, removed, modified, migrated, or restarted.** No source file, configuration file, access right, or record rule was changed. All findings come from reading `odoo.conf`, `.gitmodules`, module manifests, and the `docs/superpowers/**` governance artifacts.

Any configuration or runtime change discussed above is explicitly labelled **"PROPOSED CHANGE — NOT EXECUTED"** and requires separate approval before implementation.

## Limits of this assessment

- Module compatibility was verified only at the **manifest level** (`19.0.x` declared on branch `19.0`). Functional/runtime behaviour was **not** executed and is marked **COMPATIBILITY NOT VERIFIED (runtime)** where relevant.
- The installed-module set was taken from prior discovery (~234 modules); re-confirm from `ir_module_module` before any installation decision.
- Several custom modules appear to be stubs or report-only placeholders and must be verified before being counted as functional coverage.
