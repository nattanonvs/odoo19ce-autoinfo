# Domain Spec Index

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Program |
| Artifact | Child-spec control index |
| Artifact status | Active baseline |
| Baseline source | [2026-10-04-odoo19-ce-enterprise-blueprint-design.md](../../../specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md) |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-10-13 |
| Review cadence | Update whenever a child spec is created, approved, or resequenced |
| Validator expectation | Keep this file present at the manifest path |

## Required Child Specs

- [x] Wave 0 - Foundation platform, governance, and KPI/reporting baseline
- [ ] Wave 1 - Commercial and financial core
- [ ] Wave 2 - Custom finance controls
- [ ] Wave 3 - Sales Services and after-sales
- [ ] Wave 4 - Logistics extensions
- [ ] Wave 5 - HR and operational enablement

## Wave 1 Baseline Snapshot

| Domain | Current baseline status | Primary evidence | Remaining gap before Wave 1 closure |
| --- | --- | --- | --- |
| Contacts | Approved and implemented | `custom_addons/od19_contacts_partner_roles/` | No major design gap; keep regression-free while closing Accounting |
| Sales | Approved and implemented; customer risk gate implemented and verified on `odoo19_pdev` (24/24 tests pass, 2026-10-11); owner KPI menu actions added and verified (2026-10-12) | `custom_addons/od19_sales_project_context/`, `custom_addons/od19_sales_contract_core/`, `custom_addons/od19_sales_billing_evidence/`, `custom_addons/od19_sales_reporting/`, `custom_addons/od19_sales_oca_bridge_workflow/`, `custom_addons/od19_sales_customer_risk_gate/`, [2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md) | No major design gap; keep regression-free while closing Wave 1 |
| Project &amp; Analytic Accounting | **Implemented 2026-10-20** (W1-PROJECT-ANALYTIC, D1–D7); Project P&amp;L now reads `account.analytic.line` + `analytic_profitability`; 65 domain tests pass (`0 failed, 0 error(s)`) | Odoo 15 legacy: `autoinfo_project`, `autoinfo_project_form`, `autoinfo_project_risk_report`, `dtr_project`, `project_type`; Odoo 19 current: `custom_addons/od19_project_analytic/`, `custom_addons/od19_project_document_sequence/`, `custom_addons/od19_project_enhanced/`, `custom_addons/od19_sales_project_context/`, [2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md](../../../specs/2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md) | No major design gap; keep regression-free while closing Wave 1 |
| Purchase | Approved and implemented | `custom_addons/od19_purchase_procurement_core/` | Keep stable and verify handoff into Inventory and Accounting |
| Inventory | Approved and implemented | `custom_addons/od19_inventory_execution_control/`, `custom_addons/od19_inventory_audit_count/`, `custom_addons/od19_inventory_reporting/` | Keep stable and harden lot/serial plus adjustment governance without reopening Wave 1 scope |
| Accounting | Approved and implemented; merged to 19.0 mainline and verified on `odoo19_pdev` (35/35 tests pass, 2026-10-11) | `custom_addons/od19_accounting_operational_closure/`, `custom_addons/od19_accounting_reporting/`, [2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md), [2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md](../../../plans/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md), master-plan backlog decisions, and the split defined in [2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md](../../../specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md) | Keep regression-free; deep finance controls, credit limits, overdue holds, and approval tiers stay in Wave 2 |

## Wave 0

| Item | Status | Primary artifact |
| --- | --- | --- |
| Foundation and governance baseline | Approved | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) |
| Implementation pack | Released baseline package | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md](../../../plans/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md) |
| Handoff to Wave 1 | Active baseline | [wave-1-handoff-baseline.md](../governance/wave-1-handoff-baseline.md) |

Wave 0 is packaged and citable for Wave 1 planning, but the linked discovery artifacts remain active partial baselines rather than completed evidence packs.

## Child Spec Register

| Wave | Child spec ID | Canonical child spec title | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Discovery evidence | Gate readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | W0-FOUNDATION | Foundation platform, governance, KPI/reporting baseline, and **Thai Font & UI Localization** | [2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md](../../../specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md) | Approved — Thai Font & UI Localization scope added 2026-10-13 | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; engineering standards; review gates; **Thai font standard from Odoo 15 legacy** | [current-state-inventory.md](../discovery/current-state-inventory.md); [access-readiness-checklist.md](../discovery/access-readiness-checklist.md); [engineering-standards.md](../foundation/engineering-standards.md); [review-gates.md](../governance/review-gates.md); **Odoo 15 legacy font configuration** | Ready when the foundation child spec is approved, execution order is agreed, **and Thai font standard is confirmed across Web UI, QWeb Reports, JasperReports, and Email Templates** |
| Wave 1 | W1-COMMERCIAL-CORE | Commercial and financial core | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In execution — customer risk gate merged/verified (2026-10-11), owner KPIs confirmed with menu actions (2026-10-12); Project &amp; Analytic Accounting gap identified and added to scope (2026-10-12); migration assumptions pending business-owner acceptance | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Project &amp; Analytic Accounting baseline implemented 2026-10-20 (W1-PROJECT-ANALYTIC); Wave 1 Purchase baseline approved; Wave 1 Inventory baseline approved and merged on mainline; Wave 1 Accounting child spec approved, merged on mainline, and verified | Discovery baselines remain partial for access, integration, and data-quality evidence, while implementation evidence is active for the commercial core | Ready when the customer risk gate is implemented ✅, Wave 1 owner KPIs are confirmed ✅, Project &amp; Analytic Accounting is implemented ✅ (2026-10-20) and verified on `odoo19_pdev` ⏳, and migration assumptions for the commercial core are accepted ⏳ |
| Wave 1 | W1-PROJECT-ANALYTIC | Project &amp; Analytic Accounting | [2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md](../../../specs/2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md) | **Implemented 2026-10-20** — D1–D7 delivered in `od19_project_analytic`, `od19_project_document_sequence`, `od19_project_enhanced`; 65 domain tests pass (`0 failed, 0 error(s)`); awaiting business-owner verification on `odoo19_pdev` | Project &amp; Analytic domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved (`od19_sales_project_context`); Wave 1 Contacts baseline approved; Wave 1 Accounting baseline approved; existing Odoo 19 Project modules (`od19_project_analytic`, `od19_project_document_sequence`, `od19_project_enhanced`) are in an uncommitted refactor and are treated as baseline, not as approved design | Odoo 15 legacy `autoinfo_project`, `autoinfo_project_form`, `autoinfo_project_risk_report`, `dtr_project`, `project_type`; Odoo 19 `custom_addons/od19_project_analytic/`, `custom_addons/od19_project_document_sequence/`, `custom_addons/od19_project_enhanced/`, `custom_addons/od19_sales_project_context/`; `Odoo15Backup/odoo15_oca_mapping.xlsx` | ✅ 2026-10-20 — implemented and regression-tested; next gate is business-owner verification on `odoo19_pdev` |
| Wave 2 | W2-FINANCE-CONTROLS | Custom finance controls | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-2-custom-finance-controls.md` | Not started — scope expanded 2026-10-12 to include WHT, Petty Cash, Fiscal Year &amp; Year-End Closing, Fixed Assets, Jasper Reports Foundation, **Dual Report Format (Odoo 19 Native + Odoo 15 Legacy compatible) for all printable reports**; **Thai Localization modules** and **Payment Preparation วิธีที่ 3** added 2026-10-13 | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 approved or explicitly decoupled; confirmed Wave 2 scope for Advance, Cheque, Money In Analysis, WHT, Petty Cash, Fiscal Year, Fixed Assets, Jasper Reports, **Dual Report Format for printable reports**, **Thai Localization modules (โมดูลที่เสนอ)** | Discovery evidence for advance, cheque, money-in, WHT, petty cash, fiscal year, fixed assets, jasper reports, **Odoo 15 legacy printable report templates**, **Odoo 15 legacy payment preparation flow (dtr_billing, dtr_prepayment)**, and high-value legacy finance reports | Ready when custom control rationale, WHT/Petty Cash/Fiscal Year/Asset designs, reporting scope, **dual report format design (printable reports only)**, **Thai Localization module list**, **Payment Preparation design (วิธีที่ 3: ไม่สร้าง model ใหม่, ใช้ Odoo standard + OCA)**, dependencies, and approvals are complete |
| Wave 3 | W3-AFTER-SALES | Sales Services and after-sales | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-3-sales-services-after-sales.md` | Not started — scope expanded 2026-10-12 to include Quality Control and Digital Signature evaluation | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer/project/product baseline; confirmed separation of service returns from Inventory core | Discovery evidence for sales services, claims, warranty, service card, service-linked returns, quality control, digital signature | Ready when service flows, QC workflow, digital signature scope, stock implications, owner-reporting impact, and training implications are approved |
| Wave 4 | W4-LOGISTICS-EXT | Logistics extensions | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-4-logistics-extensions.md` | Not started — scope expanded 2026-10-12 to include Stock Valuation Adjustment and Landed Cost | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 inventory baseline; decision on legacy `Goods Issue`; Wave 3 dependencies as applicable | Discovery evidence for stock requests, transportation, logistics extensions, stock valuation adjustment, landed cost, non-standard warehouse flows | Ready when logistics dependencies, non-standard warehouse flow decisions, valuation adjustment design, landed cost integration, approval model, and rollout sequencing are approved |
| Wave 5 | W5-HR-ENABLEMENT | HR and operational enablement | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-5-hr-operational-enablement.md` | Not started — scope expanded 2026-10-12 to include HR Expense and Fleet | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance baseline; standard hr_expense and fleet modules available | Discovery evidence for employees, attendances, time off, HR expense, fleet | Ready when HR operations scope, expense/fleet integration, security posture, and training plan are approved |

## Wave Sequencing Notes

- Wave 1 remains the active closure target. Accounting and the customer risk gate are both merged/verified on the mainline workspace (2026-10-11); owner KPI menu actions were added and verified on 2026-10-12. Remaining Wave 1 work is migration-assumption acceptance by the business owner.
- Wave 0 is already released as the planning baseline package for Wave 1, but that does not convert the discovery artifacts into complete evidence; keep open discovery gaps visible until they are actually closed.
- Wave 1 should absorb only the customer risk gate baseline needed to stop blacklist sales and unapproved credit sales; it should not become the home of full finance-led credit control.
- Wave 1 must include **Project &amp; Analytic Accounting** (gap identified 2026-10-12; child spec **W1-PROJECT-ANALYTIC** drafted 2026-10-20): use standard `project.project` with `job_no`, project type (`od19_project_type`), owning department (`od19_department_id`), project owner, contractor links, and auto-created `analytic_account_id`. This is required for Sales (contract context), Purchase (project on PO lines), and Accounting (project P&amp;L). The bridge to the standard project model is already in place — `od19_sales_project_context` links `sale.order.od19_project_id` to `project.project`, so no custom `od19.sales.project` model exists. The 2026-10-12 wording that described `job_type` and a `department` Char field is superseded by the approved field-ownership map. **Implemented 2026-10-20** (W1-PROJECT-ANALYTIC): Job Type is Sale/Service/PM/Job (Job `J`, PM `PM`, Service `S`, Sales `S`); the Sales-type job number is built as `S + initials + YY + running number` (e.g. `SNV26-0001`), where the initials are derived automatically from the salesperson name (overridable with `od19_initials`) and the salesperson sequence supplies only the running counter (its prefix is ignored). Project P&amp;L is read from `account.analytic.line` + the core `analytic_profitability` classification (single P&amp;L contract, no re-implementation), and the risk levels are high ≥ 70 / medium ≥ 40 with the margin rule skipped while revenue is 0.
- Wave 1 Accounting should close AR, AP, payment, reconciliation, and essential posting/tax mapping as an operational baseline without absorbing Wave 2 control depth.
- Wave 2 should absorb finance controls and legacy reports only when they extend owner decision quality without re-opening Wave 1 boundaries.
- Wave 2 should take over deep credit-control behavior such as credit limits, overdue holds, approval tiers, and exception governance after the Wave 1 customer risk gate stabilizes.
- Wave 3 should own service-linked returns, warranty-linked stock behavior, and after-sales process complexity rather than pushing that logic back into Inventory.
- Wave 4 should own logistics extensions and the decision whether legacy `Goods Issue` still exists as a distinct future-state business process.
- **Dual Report Format (ทุก Wave)**: ทุกรายงานที่ **พิมพ์ออกมาจากระบบ (printable reports)** ต้องมีทั้งรูปแบบ Odoo 19 CE Native (QWeb) และรูปแบบ Odoo 15 CE Legacy Compatible (JasperReports/JRXML) พร้อมกัน ไม่รวม KPI Dashboard หรือรายงานบนหน้าจอ (on-screen) ดูรายละเอียดใน `reporting/kpi-reporting-baseline.md` ส่วน Dual Report Format Requirement
- **Thai Font & UI Localization (Wave 0, ใช้ได้ทุก Wave)**: ระบบต้องรองรับฟอนต์ภาษาไทยในทุกส่วน โดยใช้ฟอนต์หลักมาตรฐาน (1-2 ชุด) พร้อมสไตล์ Regular, Bold, Italic, Bold Italic — Web UI/QWeb ใช้ Sarabun/Noto Sans Thai; JasperReports (Legacy) ใช้ฟอนต์เดิมจาก Odoo 15; ฟอนต์ต้องติดตั้งบน server สำหรับ PDF; ไม่แนะนำให้ผู้ใช้เปลี่ยนฟอนต์ทุกสไตล์เพื่อรักษาความสอดคล้อง
- **Payment Preparation — วิธีที่ 3 (Wave 2, ตัดสินใจ 2026-10-13)**: ไม่สร้างโมเดล `account.payment.voucher` เอง ใช้ Odoo standard + OCA เป็นหลัก: (1) ตั้งหนี้ใช้ Vendor Bill/Customer Invoice มาตรฐาน, (2) จัดกลุ่มใบแจ้งหนี้ใช้ `account.payment.register` มาตรฐาน, (3) WHT ใช้ OCA `l10n_th_account_tax`, (4) Tax Invoice ใช้ OCA `l10n_th_account_tax`, (5) PND ใช้ Odoo standard `l10n_th`. Custom เพียงอย่างเดียว: รายงานใบสำคัญจ่าย (QWeb), รายงานใบสำคัญรับเงิน (QWeb), และเลขที่เอกสารไทยบน `account.payment` (~300 บรรทัด custom)
- **Thai Localization Modules (ทุก Wave)**: Wave 0 — `od19_thai_font_support`, `od19_thai_localization_base`; Wave 1 — `od19_partner_thai_fields`, `od19_document_sequence`, `od19_thai_tax_reports`, `od19_accounting_dncn`, `od19_accounting_cheque`; Wave 2 — `od19_accounting_reporting`, `od19_accounting_payment_voucher_reports` (reports only). ใช้ OCA เป็นฐาน: `l10n_th`, `l10n_th_account_tax`, `base_tier_validation`, `account_financial_report`

## Required Fields Per Child Spec

- Scope
- Current-state summary
- Keep/refactor/replace/retire decisions
- Future-state process
- Reporting and KPI needs
- Security and approval model
- Migration assumptions
- Training impact
- Child spec ID and wave reference
- Canonical child spec path and traceability back to [domain-wave-matrix.md](domain-wave-matrix.md)
- Owner, technical reviewer, approvers, and current status
- Discovery evidence references and source locations
- Dependency map, predecessor waves, and known blockers
- Approvers, approval dates, and approval notes
- Gate readiness summary for spec-ready, plan-ready, and build-ready checkpoints

## Child Spec Header Schema

```markdown
# <Child Spec Title>

## Control Metadata
- Child spec ID: <W0-W5 code>
- Wave: <Wave 0-5>
- Status: <Not started | In discovery | Draft | In review | Approved | Ready for plan>
- Owner: <role or named owner>
- Reviewer: <technical reviewer role or named reviewer>
- Approvers: <business owner>; <technical supervisor>
- Canonical path: <docs/superpowers/specs/...>
- Source backlog row: `backlog/domain-wave-matrix.md`

## Discovery Evidence
- Current-state references: <links to discovery artifacts, screenshots, exports, notes>
- Evidence coverage gaps: <known unknowns that must be closed before approval>

## Delivery Controls
- Dependencies: <waves, specs, systems, or data prerequisites>
- Gate readiness:
  - Spec-ready: <criteria>
  - Plan-ready: <criteria>
  - Build-ready: <criteria>
```

## Control Rules

- Do not mark a child spec ready unless its evidence, reviewer input, and approvers are recorded.
- Keep wave naming, child-spec IDs, and path placeholders synchronized with [domain-wave-matrix.md](domain-wave-matrix.md).
- Promote a child spec to `Ready for plan` only after business and technical review are both complete.
- Keep this index synchronized with the master-plan section `Wave Planning Update After Inventory Baseline` when post-review scope or sequencing changes.

## Review Checkpoints

- Business owner approval required before a child spec is marked ready
- Technical supervisor approval required before an implementation plan is written
- Owner-reporting impact must be confirmed before build starts
