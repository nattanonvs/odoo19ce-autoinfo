# Domain Wave Matrix

## Document Control

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Program |
| Artifact | Domain wave backlog control matrix |
| Artifact status | Active baseline |
| Baseline source | `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md` |
| Owner | Program lead |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Last updated | 2026-10-21 |
| Review cadence | Reconfirm before wave approval, resequencing, or child-spec sign-off |
| Validator expectation | Keep this file present at the manifest path |

## Wave 0
- Foundation platform
- Governance
- KPI and reporting baseline
- Thai Font & UI Localization (ฟอนต์ภาษาไทยและการรองรับภาษาไทยในทุกส่วนของระบบ)
- Thai Localization Strategy (กลยุทธ์การพัฒนา localization ของไทย: ใช้ OCA เป็นฐาน, ลดโมดูลซ้ำซ้อน, QWeb First, ฟอนต์ใหม่, Odoo standard menu)

## Wave 1
- Contacts
- Sales
- Project & Analytic Accounting
- Purchase
- Inventory
- Accounting

## Wave 2
- Advance
- Cheque
- Money In Analysis
- Withholding Tax (WHT)
- Petty Cash
- Fiscal Year & Year-End Closing
- Fixed Assets
- Jasper Reports Foundation

## Wave 3
- Sales Services
- Claims
- Warranty
- Service Card
- Product Return
- Quality Control

## Wave 4
- Stock Requests
- Transportation
- Logistics extensions
- Stock Valuation Adjustment
- Landed Cost

## Wave 5
- Employees
- Attendances
- Time Off
- HR Expense
- Fleet

## Wave Delivery Focus

### Wave 0 Focus
- Build the foundation platform, governance, and KPI/reporting baseline.
- **Thai Font & UI Localization**: ระบบ Odoo 19 CE ต้องรองรับฟอนต์ภาษาไทยใน **ทุกส่วนของระบบ** โดยใช้ฟอนต์หลักมาตรฐานของบริษัท (1-2 ชุด) พร้อมสไตล์ Regular, Bold, Italic, Bold Italic:
  - **Web UI (Backend/Frontend)**: ใช้ฟอนต์ Sarabun หรือ Noto Sans Thai เป็นค่าเริ่มต้น รองรับสไตล์ Regular, Bold, Italic, Bold Italic
  - **QWeb Reports (รูปแบบ Odoo 19 Native)**: ใช้ฟอนต์เดียวกับ Web UI และ **ต้องติดตั้งฟอนต์บน server** เพื่อให้ PDF แสดงผลภาษาไทยได้ถูกต้อง
  - **JasperReports (รูปแบบ Odoo 15 Legacy Compatible)**: ใช้ **ฟอนต์เดิมที่บริษัทใช้อยู่ใน Odoo 15** เพื่อให้รูปแบบเหมือนเดิม 100% และต้อง embed ฟอนต์ลงใน `.jasper` file หรือติดตั้งบน server ที่รัน jasperstarter
  - **Email Templates**: ใช้ฟอนต์ web-safe ที่รองรับไทย (Sarabun, Tahoma, Arial Unicode MS) พร้อม fallback font stack
  - **ไม่แนะนำ** ให้ผู้ใช้งานเปลี่ยนฟอนต์ได้ทุกสไตล์ เพราะจะทำให้ UI ไม่สอดคล้องและยากต่อการบำรุงรักษา
- **Thai Localization Strategy (กลยุทธ์การพัฒนา localization ของไทย)**: ตัดสินใจ 2026-10-13 — แนวทางพัฒนา localization ของไทยเพื่อลดงานพัฒนาและง่ายต่อการอัปเกรดเวอร์ชัน:
  - **หลักการ 1 — ใช้ OCA เป็นฐาน**: ไม่เขียนเองทั้งหมด ใช้ประโยชน์จาก OCA modules ที่มีแล้ว เช่น `l10n_th_account_tax` (WHT+VAT, มี v19.0), `base_tier_validation` (approval workflow), `currency_rate_update` (อัปเดตอัตราแลกเปลี่ยนอัตโนมัติ), `account_financial_report` (รายงานทางการเงิน)
  - **หลักการ 2 — ลดจำนวนโมดูล**: รวมโมดูลเล็กๆ ที่ทำงานเกี่ยวข้องกันเข้าไปในโมดูลหลักของโดเมนนั้น (เช่น รวม `dtr_payment_filter`, `dtr_account_filter`, `dtr_inventory_filter` เข้ากับโมดูลหลัก) ไม่แยกเป็นโมดูลของตัวเอง
  - **หลักการ 3 — QWeb First**: รายงานพิมพ์ใช้ QWeb Reports (Odoo Native) เป็นหลักสำหรับรูปแบบ Odoo 19 เก็บ JasperReports สำหรับรูปแบบ Odoo 15 Legacy เท่านั้น (ตาม Dual Report Format)
  - **หลักการ 4 — ฟอนต์ใหม่ทันที**: ไม่ใช้ฟอนต์ "DB Ozone X" (ยุคเก่า) แล้ว เปลี่ยนเป็น **Sarabun** หรือ **Noto Sans Thai** ตั้งแต่ Wave 0
  - **หลักการ 5 — Odoo Standard Menu**: ใช้เมนูมาตรฐานของ Odoo 19 ไม่สร้างเมนูแยกของตัวเองเหมือน DTR
  - **หลักการ 6 — ลด Tier Validation แยก**: ไม่สร้างโมดูล tier_validation แยกทุกโดเมน (7 โมดูลใน DTR) ใช้ OCA `base_tier_validation` รวมเป็นหนึ่งเดียว แล้วแต่ละโดเมนแค่ configure validation rules
  - **หลักการ 7 — รวมรายงาน**: รวมรายงานทั้งหมดเข้าโมดูล `od19_accounting_reporting` เดียว แยกตาม report action ภายใน ไม่แยกเป็นโมดูลรายงานหลายตัว
  - **หลักการ 8 — รวม Cheque Reports**: ไม่แยก cheque report ต่อธนาคาร (KBank, Bangkok Bank, SCB) รวมเป็น Cheque Template เดียว ที่กำหนดธนาคาร/เลย์เอาต์ผ่าน configuration
  - **หลักการ 9 — ลด dependency chain**: ลดการขึ้นอยู่ซ้อนกันของโมดูล (เช่น `dtr_accounting_form` → `dtr_cheque` → `dtr_advance` → `dtr_taxation`) ให้เหลือแค่ที่จำเป็น โดยใช้ inheritance และ hooks แทน

### Wave 1 Focus
- Close the commercial core on top of the approved Contacts, Sales, Purchase, Inventory, and approved Accounting design baselines.
- Add **Project & Analytic Accounting** as a Wave 1 domain: extend Odoo standard `project.project` (not a custom model) with Job Numbering (`job_no`), Job Type, Department, Project Owner, Contractor links, and auto-create `analytic_account_id` on project creation so Sales, Purchase, and Accounting can share a single project/analytic truth source. Bridge `od19_sales_project_context` to the standard project model.
- Treat Inventory and Accounting as implemented and merged baselines, but do not mark the wave complete until Project &amp; Analytic Accounting is verified on `odoo19_pdev`, the owner KPI closeout is confirmed on the mainline workspace, and the migration assumptions are accepted.
- Add the customer risk gate baseline so `Blacklist` customers are blocked from both `Quotation` and `Sales Order`, and `Credit Pending` customers remain cash-only until Accounting approval is complete. (Implemented and verified 2026-10-11.)
- Add **Purchase Revision (W1-PURCHASE-REVISION)** as a Wave 1 child spec: ISO 9001 revision control on confirmed Purchase Orders by creating a new linked copy (`/R00`, `/R01`, …) and locking the superseded copy read-only. Design approved 2026-10-16; document review pending. Scope is the Purchase Order only and must not alter the existing ISO document footer.
- Close Accounting as an operational-closure baseline that covers AR, AP, payment, reconciliation, and essential posting/tax mapping without pulling deep finance controls forward from Wave 2.
- Keep Wave 1 limited to commercial-core truth, readiness, and owner-facing KPIs.
- Do not pull advanced finance controls, after-sales process logic, or logistics extensions forward unless a documented dependency forces it.

### Wave 2 Focus
- Extend from the stable Wave 1 commercial core into finance-specific controls.
- Prioritize Advance, Cheque, Money In Analysis, Withholding Tax (WHT), Petty Cash, Fiscal Year & Year-End Closing, Fixed Assets, and Jasper Reports Foundation together with reporting that directly improves owner decision-making.
- Absorb deep credit controls such as credit limits, overdue holds, exception approvals, and finance-led exposure reporting after the Wave 1 customer risk gate is stable.
- Rebuild only the finance and inventory reports that still carry decision value from the Odoo 15 legacy system.
- **WHT**: ใช้ **OCA `l10n_th_account_tax` (v19.0)** เป็นฐานสำหรับ WHT (ภาษีหัก ณ ที่จ่าย) และ VAT — ไม่ต้องพัฒนาเอง โมดูลนี้รองรับ WHT บนบรรทัดใบแจ้งหนี้, คำนวณอัตโนมัติตอนจ่าย, Tax Invoice Number/Date, Undue VAT (VAT ตอนจ่าย), PIT (Personal Income Tax)
- **Payment Preparation (Prepare Payment) — วิธีที่ 3 (ตัดสินใจ 2026-10-13)**: **ไม่สร้างโมเดล `account.payment.voucher` เอง** แต่ใช้ Odoo standard + OCA เป็นหลัก เพื่อลดงานพัฒนาและง่ายต่อการอัปเกรด:
  - **ตั้งหนี้**: ใช้ Vendor Bill / Customer Invoice (Odoo standard) — ไม่ต้องพัฒนา
  - **จัดกลุ่มใบแจ้งหนี้**: ใช้ Odoo standard `account.payment.register` (จัดกลุ่มได้ partner เดียวกัน ซึ่งเป็นกรณีส่วนใหญ่) — ไม่ต้องพัฒนา
  - **WHT คำนวณอัตโนมัติ**: ใช้ OCA `l10n_th_account_tax` — ไม่ต้องพัฒนา
  - **Tax Invoice**: ใช้ OCA `l10n_th_account_tax` (มี `tax_invoice_number`, `tax_invoice_date`) — ไม่ต้องพัฒนา
  - **PND (PND3/PND53)**: ใช้ Odoo 19 standard `l10n_th` (มี CSV export สำหรับ RD) — ไม่ต้องพัฒนา
  - **Custom ที่ต้องพัฒนาเพียงอย่างเดียว** (✅ พัฒนาแล้ว 2026-10-21 ในโมดูล `od19_accounting_payment_voucher_reports`):
    1. รายงานใบสำคัญจ่าย (Payment Voucher) — QWeb report
    2. รายงานใบสำคัญรับเงิน (Payment Receipt) — QWeb report
    3. เลขที่เอกสารไทยสำหรับ payment (PV-2569-0001) — sequence field `od19_voucher_no` บน `account.payment` (รัน PV/RV ตอน `action_post()` ผ่าน sequence จาก `od19_accounting_document_sequence`)
  - **Optional (ถ้าต้องการ)**:
    - อนุมัติก่อนชำระ (Approval): ใช้ OCA `base_tier_validation` (~50 บรรทัด config)
    - จัดกลุ่มหลาย partner: ใช้ OCA `account_payment_order` (~100 บรรทัดปรับให้เข้ากับไทย)
    - WHT Certificate PDF: พัฒนา custom (~200 บรรทัด)
  - **เหตุผล**: วิธีนี้พัฒนาน้อยที่สุด (~300 บรรทัด custom) และง่ายต่อการอัปเกรดที่สุด เพราะใช้ OCA + Odoo standard เป็นหลัก โค้ด custom น้อยมาก
- **Petty Cash**: Build a dedicated petty cash workflow separate from HR Expense, with cash box management, replenishment, and reconciliation.
- **Fiscal Year & Year-End**: Replace `om_fiscal_year` with OCA `account_fiscal_year` (periods) and handle year-end closing as **Manual no-code** on Odoo 19 core lock dates (`fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` / `sale_lock_date` + `account.lock_exception`) — **no custom closing module** (decided 2026-10-21; replaces `dtr_year_end`).
- **Fixed Assets**: Replace `om_account_asset` and `dtr_fixed_assets` with OCA `account_asset_management` (`third_party/oca/account-financial-tools/`) or custom asset management.
- **Jasper Reports Foundation**: Establish JasperReports + jasperstarter infrastructure for all printable forms (invoice, quotation, PO, project, receipt).
- **Dual Report Format Mandate**: เงื่อนไขนี้ใช้เฉพาะ **รายงานที่พิมพ์ออกมาจากระบบ (printable reports / printed forms)** เท่านั้น ไม่รวม KPI Dashboard หรือรายงานบนหน้าจอ ทุกรายงานพิมพ์ต้องมีทั้งรูปแบบ Odoo 19 CE Native (QWeb) และรูปแบบ Odoo 15 CE Legacy Compatible (JasperReports/JRXML) พร้อมกัน (ดูรายละเอียดใน `reporting/kpi-reporting-baseline.md` ส่วน Dual Report Format Requirement).

- **โมดูลที่เสนอสำหรับ Thai Localization (แบ่งตาม Wave)**:
  - **Wave 0**: `od19_thai_font_support` (ติดตั้งฟอนต์ Sarabun/Noto Sans Thai + CSS สำหรับ Web UI และ QWeb), `od19_thai_localization_base` (ฐานสำหรับ localization ของไทย: menu, term, config)
  - **Wave 1**: `od19_partner_thai_fields` (ฟิลด์ไทยสำหรับ partner: เลขประจำตัวผู้เสียภาษี, สาขา, หมายเลขสำนักงานใหญ่), `od19_document_sequence` (เลขที่เอกสารไทย: INV, PO, SO, PV ตามปีงบประมาณ), `od19_thai_tax_reports` (VAT Register, WHT Register, PND export — ขยายจาก OCA `l10n_th_account_tax`), `od19_accounting_dncn` (Debit Note / Credit Note / Remaster Invoice), `od19_accounting_cheque` (เช็ค: รายการเช็ค, เงื่อนไข, รายงานพิมพ์เช็ครวมธนาคาร)
  - **Wave 2**: `od19_accounting_reporting` (รายงานทางการเงินทั้งหมด: AR/AP Aging, Trial Balance, P&L, Balance Sheet — QWeb), `od19_accounting_payment_voucher_reports` (รายงานใบสำคัญจ่าย/ใบสำคัญรับเงิน — **reports only, ไม่สร้าง model ใหม่** ตาม Payment Preparation วิธีที่ 3)
  - **หมายเหตุ**: ไม่มีโมดูล custom `od19_accounting_wht` บนดิสก์ — WHT GL สร้างโดย OCA `l10n_th_account_tax` (`_handle_withholding_taxes()`) และฟิลด์แสดงผล (advisory) อยู่ใน `od19_accounting_features` (compute-only) จึงไม่ต้องพัฒนาโมดูล WHT แยก
- **OCA Modules ที่จะใช้เป็นฐาน (ไม่พัฒนาเอง)**: `l10n_th` (มาตรฐาน Odoo: CoA, VAT 7%, WHT types, PND3/PND53 CSV, PromptPay QR, Tax Invoice PDF), `l10n_th_account_tax` (WHT บนบรรทัดใบแจ้งหนี้, auto-calc ตอนจ่าย, Tax Invoice Number/Date, Undue VAT, PIT), `base_tier_validation` (approval workflow รวมศูนย์เดียว), `account_financial_report` (รายงานทางการเงินมาตรฐาน)

### Wave 3 Focus
- Build the after-sales operating model as its own bounded context.
- Keep service returns, warranty-linked stock behavior, claims, and service-card flows out of Inventory core.
- Use the stable customer, project, and product baseline from earlier waves.
- **Quality Control**: Replace `dtr_qc` with an in-house QC workflow for incoming/outgoing inspection — delivered as custom module `od19_quality_control` (no OCA `quality_control_oca` exists in `third_party/oca`).
- **Digital Signature**: Delivered by in-house `od19_document_sign` (2026-10-19). Uses the built-in Odoo 19 CE signature infrastructure (`signature` widget + `portal.signature_form` + `portal.mixin` access tokens) instead of OCA `sign_oca`, so no external dependency is required.
- **After-Sales KPI Aggregation**: Delivered as the read-only module `od19_after_sales_reporting` (2026-10-21). Six `_auto = False` SQL view models aggregate service tickets (by team type/service type), warranty claims (rate + turnaround), service cards (due/overdue + SLA breach), product returns (reason + refund value), QC inspections (pass/fail + rejected qty + NC link) and CSAT by period, exposed through pivot/graph/list menus under an "After-Sales Reporting" root menu.
- **After-Sales Dashboard**: Delivered in the same module (2026-10-21). The six KPI views are registered as `od19_dashboard` data sources and combined into a single **After-Sales Service Dashboard** (KPI cards, alert cards, breakdown charts) reachable from the "After-Sales Dashboard" menu item under the After-Sales Reporting root.
- **Cross-Module Flow Gap Closure**: Closed on 2026-10-21 — Ticket→Invoice made idempotent and company-scoped, Claim→Repair blocked for rejected/cancelled claims, Return→Picking/Credit Note company-scoped, idempotent, with the refund unit price falling back to the linked invoice line. QC→NC needed no change (guards already present).

### Wave 4 Focus
- Build logistics extensions only after the Inventory baseline is stable in production-like use.
- Re-evaluate legacy warehouse and issue flows, including `Goods Issue`, against the new standard movement baseline before approving any rebuild.
- Default to redesign over direct migration for transportation and non-standard warehouse convenience logic.
- **Stock Valuation Adjustment**: Replace `dtr_stock_valuation_adjustment` with Odoo 19 standard inventory value adjustments plus audit trail.
- **Landed Cost**: Enable standard `stock_landed_costs` for shipping/import cost allocation.
- **Internal Stock Request (ขอเบิก/ขอโอนสินค้าภายใน)**: Adopt **OCA `stock_request`** (repo `OCA/stock-logistics-request`, branch 19.0) — added as submodule `third_party/oca/stock-logistics-request` and wired into `odoo.conf` (decided 2026-10-21). Includes `stock_request` + `stock_request_purchase` (`auto_install=True`). Purchase **requisition** (ขอซื้อ) remains OCA `purchase_request*` + `od19_purchase_request_extend`.

### Wave 5 Focus
- Build HR and operational enablement on top of the Wave 0 governance baseline.
- **HR Expense**: Replace `autoinfo_hr_expense`, `autoinfo_hr_expense_cash_tracking` with Odoo 19 standard `hr_expense` plus custom cash reimbursement and multi-tier approval.
- **Fleet**: Replace `autoinfo_fleet` with Odoo 19 standard `fleet` module; integrate with accounting and HR where needed.

## Wave Control Register

| Wave | Baseline scope | Child spec ID | Child spec path placeholder | Status | Owner | Reviewer | Approvers | Dependencies | Gate readiness cue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave 0 | Foundation platform; Governance; KPI and reporting baseline | W0-FOUNDATION | `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md` | Approved and packaged for Wave 1 planning | Program lead | Technical supervisor | Business owner; Technical supervisor | Discovery pack; Engineering standards; Review gates | Ready and released for Wave 1 planning use; discovery evidence remains partial where the linked discovery artifacts still say so |
| Wave 1 | Contacts; Sales; Project &amp; Analytic Accounting; Purchase; Inventory; Accounting | W1-COMMERCIAL-CORE | No single combined spec — Wave 1 rolls up the per-domain child specs (Contacts, Sales, Project &amp; Analytic, Purchase, Inventory, Accounting) | In execution | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 baseline package released; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Project &amp; Analytic Accounting baseline implemented 2026-10-20 (W1-PROJECT-ANALYTIC, 65 domain tests pass); Wave 1 Purchase baseline approved; Wave 1 Inventory baseline approved and merged on mainline; Wave 1 Accounting child spec approved; merged to 19.0 mainline and verified (35/35 tests, 2026-10-11) | Ready when Project &amp; Analytic Accounting is verified on `odoo19_pdev`, the Wave 1 migration assumptions are accepted, and the Wave 1 owner KPI set is confirmed against the established Sales, Contacts, Purchase, Inventory, and Accounting baseline |
| Wave 2 | Advance; Cheque; Money In Analysis; Withholding Tax (WHT); Petty Cash; Fiscal Year &amp; Year-End Closing; Fixed Assets; Jasper Reports Foundation | W2-FINANCE-CONTROLS | `docs/superpowers/specs/2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md` | Implemented — spec synced 2026-10-21 to disk state; core finance controls present (`od19_accounting_advance`, `od19_accounting_cheque`, `od19_accounting_money_in_report`, `od19_accounting_features` WHT, `od19_thai_tax_reports`, `od19_accounting_petty_cash`, `od19_asset_disposal`, `od19_asset_loan`, `od19_reporting_jasper`, `od19_thai_font_support`); OCA `l10n_th_account_tax`/`account_asset_management`/`account_fiscal_year` available; Payment Preparation (วิธีที่ 3) closed by `od19_accounting_payment_voucher_reports` (Payment Voucher PV / Payment Receipt RV QWeb + `od19_voucher_no` on `account.payment` calling sequences from `od19_accounting_document_sequence`); Year-End Closing decided as **Manual no-code** on core lock dates (no custom module) | Finance controls lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 stable baseline; finance discovery evidence; OCA availability `account_asset_management`, `account_fiscal_year`, `l10n_th_account_tax` | Ready when Payment Voucher/Receipt + PV/RV sequence pass post-install tests and finance controls are verified on `odoo19_pdev` |
| Wave 3 | Sales Services; Claims; Warranty; Service Card; Product Return; Quality Control | W3-AFTER-SALES | `docs/superpowers/specs/2026-10-21-odoo19-enterprise-wave-3-sales-services-after-sales.md` | Implemented — spec drafted 2026-10-21 from disk state; Quality Control (`od19_quality_control`), Digital Signature (`od19_document_sign`, 2026-10-19), Service Card (`od19_service_card`), Warranty (`od19_service_warranty`), Product Return (`od19_product_return`), Sales Services via `od19_helpdesk_extension`, and ISO Customer Satisfaction all present on disk; Claims handled in warranty/return modules; after-sales KPI aggregation delivered as read-only module `od19_after_sales_reporting` (2026-10-21, six SQL KPI views covering tickets, warranty, service cards, returns, QC and CSAT); consolidated After-Sales Service Dashboard delivered on `od19_dashboard` (2026-10-21) from the six KPI sources; cross-module flow gaps closed 2026-10-21 (Ticket→Invoice idempotent + company-scoped, Claim→Repair blocked for rejected/cancelled claims, Return→Picking/Credit Note company-scoped + idempotent + invoice-line refund price); residual work is verification on `odoo19_pdev` | Service operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 1 customer/product baseline; OCA `helpdesk_mgmt` present; core `addons/repair` present; confirmed separation between inventory core and after-sales returns | Ready when Wave 3 modules, the `od19_after_sales_reporting` KPI views and the consolidated dashboard are verified on `odoo19_pdev` |
| Wave 4 | Stock Requests; Transportation; Logistics extensions; Stock Valuation Adjustment; Landed Cost | W4-LOGISTICS-EXT | `docs/superpowers/specs/2026-10-21-odoo19-enterprise-wave-4-logistics-extensions.md` | Partially implemented — spec drafted 2026-10-21 from disk state; Transportation (`od19_transportation`), Stock Valuation Adjustment (`od19_stock_valuation_adjustment`), FIFO valuation (`od19_stock_fifo`), picking features (`od19_stock_picking_features`), and delivery label (`od19_delivery_label`) present on disk; core `stock_landed_costs` available; Thai purchase-requisition extension `od19_purchase_request_extend` is **implemented** on disk (extends OCA `purchase_request` with priority, department, budget year, request reason, asset link, and tier-validation notifications — not a stub); dedicated internal Stock Request (ขอเบิก/ขอโอนสินค้าภายใน) resolved by adopting **OCA `stock_request`** — submodule `third_party/oca/stock-logistics-request` (branch 19.0) added 2026-10-21 and wired into `odoo.conf`; Landed Cost activation (core `stock_landed_costs`) still pending | Logistics lead | Technical supervisor | Business owner; Technical supervisor | Inventory baseline; OCA `purchase_request`, `purchase_request_type`, `purchase_request_tier_validation`, `stock_request` + `stock_request_purchase` available; decision on whether legacy `Goods Issue` remains a real business process after Wave 1 | Ready when OCA `stock_request` is installed on `odoo19_pdev`, Landed Cost is enabled/verified, and the legacy `Goods Issue` decision is confirmed |
| Wave 5 | Employees; Attendances; Time Off; HR Expense; Fleet | W5-HR-ENABLEMENT | `docs/superpowers/specs/2026-10-15-odoo19-enterprise-wave-5-hr-operational-enablement.md` | In execution — HR Expense and Fleet already live; Attendances + Time Off enabled and ZKTeco device integration delivered 2026-10-15 | HR operations lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 governance; people operations evidence; standard hr_expense and fleet modules | Attendances/Time Off base modules installed and ZKTeco integration verified on `odoo19` and `odoo19_pdev`; awaiting real-device commissioning and confirmed OT policy |

## Cross-Cutting Reporting Track

Dashboard and reporting enablement work is **not** a domain wave in the Wave 0–5 roadmap. It builds out the Wave 0 KPI and reporting baseline (`reporting/kpi-reporting-baseline.md`, `reporting/role-based-dashboard-blueprint.md`), so it is tracked here as a cross-cutting track instead of a new wave. This keeps the two specs that label themselves "Wave 6 (Internal Operations)" traceable without changing the approved Wave 0–5 domain scope lists above.

| Track | Spec ID | Status | Notes |
| --- | --- | --- | --- |
| Internal Operations / reporting enablement | W6-DASH-FORMULA-RULES | Implemented | `docs/superpowers/specs/2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md`; extends module `od19_dashboard` |
| Internal Operations / reporting enablement | W6-DASH-PHASE2 | Implemented | `docs/superpowers/specs/2026-10-16-odoo19-dashboard-phase2-presentation-design.md` |

Keep this track aligned with the `## Cross-Cutting Reporting Track` section in `backlog/domain-spec-index.md`.

## Reviewability Cues

- Keep the baseline wave lists above unchanged so the plan-approved scope remains visible.
- Keep every wave in this file aligned with one row in `backlog/domain-spec-index.md`, including Wave 0.
- Use role-based owners, one technical reviewer, and shared approvers until named assignees are formally assigned.
- Update `Status` and `Gate readiness cue` only after a recorded review meeting or approval checkpoint.
- Treat Wave 0 as an approved planning package, not as a claim that every discovery line item is fully evidenced.
- If wave sequencing changes, update both this matrix and the spec index in the same commit.
- Keep this matrix aligned with the master-plan section `Wave Planning Update After Inventory Baseline` whenever post-review backlog decisions change.
