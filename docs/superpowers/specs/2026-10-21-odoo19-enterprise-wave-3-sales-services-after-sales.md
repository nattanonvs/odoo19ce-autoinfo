# Odoo 19 CE Wave 3: Sales Services and After-Sales

## Control Metadata
- Child spec ID: W3-AFTER-SALES
- Wave: Wave 3 (Sales Services and after-sales)
- Status: Implemented — Quality Control, Digital Signature, Service Card, Warranty, Product Return, Sales Services (helpdesk), ISO Customer Satisfaction, and the after-sales KPI aggregation (`od19_after_sales_reporting`) are present on disk; residual work is verification on `odoo19_pdev`
- Owner: Service operations lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Canonical path: `docs/superpowers/specs/2026-10-21-odoo19-enterprise-wave-3-sales-services-after-sales.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-21
- Primary readers: ฝ่ายขาย, ฝ่ายบริการลูกค้า (Service), ฝ่ายเทคนิคภาคสนาม, ฝ่ายคลัง, ฝ่ายบัญชี, ผู้จัดการแผนก, ทีมเทคนิค

## Approval Traceability
- Scope baseline (Sales Services, Claims, Warranty, Service Card, Product Return, Quality Control) approved in the Wave Control Register on 2026-10-12.
- Scope expanded 2026-10-12 to include Quality Control and Digital Signature.
- Quality Control implemented as `od19_quality_control`; Digital Signature delivered as `od19_document_sign` on 2026-10-19.
- After-sales KPI aggregation delivered as `od19_after_sales_reporting` on 2026-10-21 (closes the §6.7 residual).
- 2026-10-21: ผู้ใช้อนุมัติแนวทางเขียนสเปกตามสภาพจริงบนดิสก์ และให้อัปเดตเอกสารกำกับให้สอดคล้องพร้อมกัน

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` (Wave 3 scope and focus)
  - `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md` (reporting contract)
  - `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md` (invoicing/refund handoff)
  - `Odoo15Backup/` legacy landscape (module names only; legacy after-sales source is not on disk)
- Verified current state on disk (2026-10-21):
  - `custom_addons/od19_helpdesk_extension/` — Sales Services via OCA `helpdesk_mgmt`; `helpdesk.ticket.team.team_type` (internal / customer_service); ticket fields `service_type`, `product_id`, `lot_id`, `technician_id`, `sale_order_id`, `invoice_id`, `action_create_invoice()`; depends `helpdesk_mgmt, sale, stock, hr, account`
  - `custom_addons/od19_service_warranty/` — `od19.warranty.claim` (state `draft → confirmed → in_progress → done / rejected / cancelled`), `_compute_under_warranty()`, `action_create_repair_order()`; extends `stock.lot` (warranty dates/status), `product.template` (warranty_duration/type), `repair.order`; depends `repair, product_expiry, stock`
  - `custom_addons/od19_service_card/` — `od19.service.card` (preventive/corrective/inspection/installation; SLA fields `sla_hours`, `sla_deadline`, `is_sla_breached`; `next_service_date`); extends `product.template.service_interval`; depends `stock, product, hr, sale`
  - `custom_addons/od19_product_return/` — `od19.product.return` (state `draft → confirmed → approved → returned → refunded / rejected`), `action_return()` creates a return picking, `action_refund()` creates a credit note; reject wizard; depends `stock, sale, account, od19_service_warranty, od19_delivery_label`
  - `custom_addons/od19_quality_control/` — `od19.qc.inspection` (incoming/outgoing/in_process; state `draft → in_progress → passed / failed / cancelled`), `action_create_nonconformity()` linking `od19_iso_nonconformity`; depends `stock, product, od19_iso_nonconformity`
  - `custom_addons/od19_document_sign/` — `od19.document` + `od19.document.signer` + `od19.document.template` (state `draft → sent → signed / refused / expired`), portal controller, access tokens, expiry cron, QWeb PDF report; depends `mail, portal`
  - `custom_addons/od19_internal_issue/` — `helpdesk.ticket` extension for internal issues with `base_tier_validation` approval; depends `helpdesk_mgmt, base_tier_validation, hr, mail, od19_notification_multi_channel`
  - `custom_addons/od19_iso_customer_satisfaction/` — `od19.iso.customer.satisfaction` + survey items + period report (ISO 9001 clause 9.1.2)
  - `custom_addons/od19_after_sales_reporting/` — read-only KPI aggregation (`_auto = False` SQL views): `od19.report.after.sales.ticket`, `.warranty.claim`, `.service.card`, `.product.return`, `.qc.inspection`, `.csat.period`; pivot/graph/list menus (2026-10-21)
  - `custom_addons/od19_delivery_label/` — delivery label (FM-PU-12); shared with Wave 4 logistics
  - OCA module present in `third_party/oca/`: `helpdesk_mgmt` (19.0.1.3.0, `third_party/oca/helpdesk/helpdesk_mgmt/`)
  - Core module present: `addons/repair/` (Repair Orders; depends `sale_stock, sale_management`)
- Evidence findings:
  - There is **no** OCA `quality_control_oca` and no OCA `repair`; QC is in-house (`od19_quality_control`) and repair uses **core** `addons/repair`.
  - "Claims" is intentionally **distributed**: warranty claims in `od19_service_warranty` and RMA/return claims in `od19_product_return` — there is no standalone Claims module.
  - "Sales Services" is intentionally delivered through `od19_helpdesk_extension` (`team_type = customer_service`) rather than a separate model.
- Evidence coverage gaps:
  - Legacy Odoo 15 after-sales addon source (`dtr_qc`, legacy service/return flows) is not on disk for field-by-field mapping.
  - No signed SLA/OT policy document for service card SLA targets.
  - No consolidated after-sales **dashboard** (chart/KPI board) yet; the underlying read-only KPI aggregation is delivered (`od19_after_sales_reporting`).

## Delivery Controls
- Dependencies:
  - Wave 1 customer / project / product baseline (Sales, Contacts, Project & Analytic, Inventory)
  - OCA `helpdesk_mgmt` (present) and core `addons/repair` (present)
  - Wave 2 accounting operational-closure for refund/credit-note posting
- Gate readiness:
  - Spec-ready: ✅ scope, boundary (service returns kept out of Inventory core), QC and signature scope defined
  - Plan-ready: ✅ addon boundaries, state flows, security model defined; KPI aggregation delivered as `od19_after_sales_reporting`
  - Build-ready: ⏳ verify all Wave 3 modules install and pass tests on `odoo19_pdev`

---

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบแกน `Sales Services and After-Sales` ของ Wave 3 ให้เป็น bounded context ของงานบริการหลังการขาย ครอบคลุม:

- `Sales Services` (งานบริการลูกค้า ผ่าน Helpdesk)
- `Claims` (การเรียกร้อง — กระจายใน warranty claim และ product return)
- `Warranty` (ประกันสินค้า)
- `Service Card` (บัตรบริการ/บำรุงรักษาเชิงป้องกัน)
- `Product Return` (การคืนสินค้า / RMA)
- `Quality Control` (ตรวจสอบคุณภาพเข้า–ออก)
- `Digital Signature` (ลายเซ็นดิจิทัล)

หัวใจของ Wave นี้คือทำให้ระบบตอบได้ว่า:

- งานบริการลูกค้าถูกบันทึกและติดตามสถานะครบหรือไม่
- สินค้าที่ส่งคืน/เคลม มีผลต่อสต็อกและใบลดหนี้ถูกต้องหรือไม่
- การรับประกันสินค้าตรวจสอบจาก Lot/Serial ได้หรือไม่
- การบำรุงรักษาเชิงป้องกันแจ้งเตือนตามรอบและ SLA หรือไม่
- เอกสารสำคัญถูกลงนามอิเล็กทรอนิกส์และตรวจสอบย้อนหลังได้หรือไม่

โดเมนนี้ต้องเป็นแหล่งความจริงของ `service process` และ `after-sales stock behavior` โดยไม่ดึง logic เหล่านี้กลับไปไว้ใน Inventory core

## 2. เป้าหมายของ Child Spec นี้

- ทำให้ after-sales เป็น bounded context ของตัวเอง
- แยก service returns / warranty-linked stock behavior / claims / service-card flows ออกจาก Inventory core
- ใช้ OCA `helpdesk_mgmt` และ core `addons/repair` เป็นฐาน (OCA-First) โดยไม่แก้ core
- ให้ทุก addon ติดตั้ง/ถอนได้โดยไม่กระทบเสถียรภาพระบบ
- เตรียม KPI ของงานบริการสำหรับเจ้าของกิจการ

## 3. ขอบเขตของ Child Spec

### 3.1 อยู่ใน scope (ในก้อนนี้)
- Sales Services ผ่าน `od19_helpdesk_extension` (`team_type = customer_service`) รวมถึง Internal Issue ที่ใช้ base เดียวกัน
- Warranty: `od19_service_warranty` (claim + lot-level warranty + repair integration)
- Service Card: `od19_service_card` (preventive/corrective + SLA)
- Product Return: `od19_product_return` (RMA workflow + picking + credit note)
- Quality Control: `od19_quality_control` (incoming/outgoing/in_process inspection)
- Digital Signature: `od19_document_sign` (templates, multi-signer, portal, PDF report)
- ISO Customer Satisfaction: `od19_iso_customer_satisfaction`
- Reporting/KPI ของงานบริการและ after-sales

### 3.2 ไม่อยู่ใน scope (Out of scope)
- การแก้ไขไฟล์ core ของ Odoo
- การย้าย service-linked returns กลับเข้า Inventory core
- โมดูล "Claims" แยกต่างหาก (ตัดสินใจกระจายตามบริบทแล้ว)
- Payroll / HR (Wave 5)
- Transportation / logistics (Wave 4)
- การ re-implement ระบบซ่อม (`repair`) ที่ core มีอยู่แล้ว

## 4. Current-State Summary

Wave 3 มีการพัฒนาบนดิสก์ค่อนข้างครบแล้ว (2026-10-21):

| โดเมน | โมดูล/แหล่ง | สถานะบนดิสก์ |
| --- | --- | --- |
| Sales Services | `od19_helpdesk_extension` (OCA `helpdesk_mgmt`) | Implemented — ticket/team extension + create invoice |
| Claims | `od19_service_warranty` + `od19_product_return` | Implemented (distributed) |
| Warranty | `od19_service_warranty` | Implemented — claim + lot warranty + repair order |
| Service Card | `od19_service_card` | Implemented — preventive/corrective + SLA |
| Product Return | `od19_product_return` | Implemented — RMA + picking + credit note |
| Quality Control | `od19_quality_control` | Implemented — in/out/in-process inspection + NC link |
| Digital Signature | `od19_document_sign` | Delivered 2026-10-19 — templates + multi-signer + portal |
| Internal Issue | `od19_internal_issue` | Implemented — tier validation |
| ISO Customer Satisfaction | `od19_iso_customer_satisfaction` | Implemented |

## 5. Keep / Refactor / Replace / Retire

- Keep
  - OCA `helpdesk_mgmt`; core `addons/repair`
  - `od19_helpdesk_extension`, `od19_service_warranty`, `od19_service_card`, `od19_product_return`, `od19_quality_control`, `od19_document_sign`, `od19_internal_issue`, `od19_iso_customer_satisfaction`, `od19_after_sales_reporting`
- Refactor
  - รวม and intelligence ของ after-sales ให้มีมุมมอง/KPI รวม — **delivered** เป็นโมดูล read-only `od19_after_sales_reporting` (SQL views + pivot/graph/list) ยังไม่ใช่ dashboard เต็มรูปแบบ
  - ตรวจสอบว่า QC ต่อกับ Nonconformity และ Warranty/RMA ต่อกับการเงิน (credit note) ไหลได้ครบ
- Replace
  - Legacy `dtr_qc` → `od19_quality_control` (in-house QC workflow)
  - Legacy QC/signature dependencies → `od19_document_sign` (ใช้ signature infrastructure ของ Odoo 19 แทน OCA `sign_oca`)
- Retire
  - ขั้นตอน QC/อนุมัติเอกสารแบบ manual ที่ซ้ำซ้อน เมื่อ workflow อัตโนมัติครบ
  - โมดูล tier_validation แยกต่อโดเมน (ใช้ OCA `base_tier_validation` รวมศูนย์)

## 6. Future-State Design

### 6.1 Sales Services (Helpdesk)
`helpdesk.ticket` ใช้ OCA `helpdesk_mgmt` เป็นฐาน แยกทีมด้วย `team_type` (internal / customer_service) พร้อมฟิลด์ `service_type`, product/lot, technician, sale order/invoice link และ `action_create_invoice()`

### 6.2 Warranty
`od19.warranty.claim` ผูกกับ Lot/Serial และ product warranty policy; `_compute_under_warranty()` ตัดสินสถานะ; `action_create_repair_order()` ส่งต่อไป core `repair`

### 6.3 Service Card
`od19.service.card` รอบบำรุงรักษาเชิงป้องกัน ใช้ `service_interval` จาก product, คำนวณ `next_service_date`, ติดตาม SLA (`sla_hours` / `sla_deadline` / `is_sla_breached`)

### 6.4 Product Return (RMA)
`od19.product.return` ครบ state `draft → confirmed → approved → returned → refunded / rejected`; `action_return()` สร้าง return picking (แยกจาก Inventory core), `action_refund()` สร้าง credit note ผ่าน `account`

### 6.5 Quality Control
`od19.qc.inspection` รองรับ incoming/outgoing/in_process พร้อม inspection lines; `action_create_nonconformity()` เชื่อม `od19_iso_nonconformity`

### 6.6 Digital Signature
`od19.document` + `od19.document.signer` + `od19.document.template` ใช้ signature infrastructure ของ Odoo 19 CE (signature widget + portal) พร้อม access token, expiry cron และ QWeb PDF report — ไม่ต้องพึ่ง OCA `sign_oca`

### 6.7 Reporting/KPI งานบริการ
Delivered as the read-only module **`od19_after_sales_reporting`** (2026-10-21) — six `_auto = False` SQL view models exposed via pivot/graph/list menus under an "After-Sales Reporting" root menu (read-only; `base.group_user` read access, multi-company record rules):
- จำนวน/สถานะ ticket แยกทีม (internal/service) และแยก `service_type` — `od19.report.after.sales.ticket`
- Warranty claim rate และ turnaround — `od19.report.after.sales.warranty.claim`
- Service card due/overdue และ SLA breach count — `od19.report.after.sales.service.card`
- Product return rate แยก reason และ refund value — `od19.report.after.sales.product.return`
- QC pass/fail rate และ NC ที่เกิดจาก QC — `od19.report.after.sales.qc.inspection`
- Customer satisfaction score (CSAT) ตาม period — `od19.report.after.sales.csat.period`

## 7. Boundary กับโดเมนอื่น

- กับ Inventory (Wave 1/4): return/warranty stock behavior อยู่ใน Wave 3 ไม่ push กลับ Inventory core; การขนย้าย/โลจิสติกส์อยู่ Wave 4
- กับ Accounting (Wave 2): credit note จาก return และค่าใช้จ่าย service post ผ่าน `account` มาตรฐาน
- กับ Sales (Wave 1): ใช้ customer/product/project baseline ร่วมกัน
- กับ HR (Wave 5): technician เป็น employee reference เท่านั้น

## 8. Reporting และ KPI Needs

- Service ticket aging/SLA, warranty claim turnaround, service card due/overdue
- Return rate/reason analysis และ refund value
- QC pass/fail และ NC linkage
- CSAT และ period report
- รายงานที่พิมพ์ออกมา (ถ้ามี) ต้องมี Dual Report Format ตาม Wave 2 (ยกเว้นรายงานออนไลน์)

## 9. Security และ Control Model

- เข้าถึง ticket และ service records ตามกลุ่มทีม (`helpdesk_mgmt` groups) และ record rules ของ `od19_helpdesk_extension`
- Internal Issue ใช้ `base_tier_validation` อนุมัติก่อนดำเนินการ
- Digital Signature: portal signing ใช้ access token ต่อ signer (`portal.mixin`); เก็บ audit (signed_by/signed_on/refusal)
- QC/Return approval จำกัดเฉพาะ role ที่กำหนด

## 10. Migration Assumptions

- Master data ลูกค้า/สินค้า/Lot อ้างอิงจาก Wave 1 ไม่ยกโครงสร้างตาราง Odoo 15
- ประกันสินค้าคงเหลือ/รอบบำรุงรักษาจากระบบเดิมยกมาเป็นข้อมูลตั้งต้นตามข้อตกลงฝ่ายบริการ
- รูปแบบเอกสารบริการ (ถ้าพิมพ์) ใช้ Odoo 15 เป็นต้นฉบับสำหรับ Legacy Compatible

## 11. Training Impact

- ฝ่ายบริการ: การเปิด/ปิด ticket, service type และการออก invoice จาก ticket
- ช่างเทคนิค: การบันทึกการซ่อม/บำรุงรักษา และการลงนามดิจิทัล
- ฝ่ายขาย/บัญชี: กระบวนการ RMA และ credit note
- QC: การบันทึก inspection และการสร้าง NC

## 12. Test Strategy

- Unit/Integration tests (post-install) ของแต่ละโมดูล: QC states + NC link, Warranty under_warranty computation + repair order creation, Service Card SLA + next_service_date, Product Return picking + refund, Document Sign signer flow + expiry, Helpdesk invoice creation
- Report tests: QWeb PDF ของ Digital Signature และ delivery label (ถ้าอยู่ในขอบเขต) แสดงผลไทยถูกต้อง
- Security tests: ตรวจ record rules และ tier validation
- การรัน Unit Test ต้องรันโดยผู้ใช้ผ่าน Terminal บนเครื่องโดยตรง

## 13. Known Unknowns

- KPI/after-sales dashboard รวม จะสร้างเป็น report นอกขอบเขต printable หรือไม่
- SLA target ที่ยืนยันเป็นลายลักษณ์อักษรจากฝ่ายบริการ
- การยกยอด warranty คงเหลือจากระบบเดิม

## 14. Definition of Done ระดับสเปก

- โมดูล Wave 3 ทั้งหมดติดตั้งได้บน `odoo19_pdev` โดย log ไม่มี warning จากโมดูลเอง
- ทุก flow หลัก (ticket → invoice, claim → repair, return → refund, QC → NC, signature) ทดสอบผ่าน
- มีมุมมอง/KPI งานบริการตามที่นิยาม — ✅ delivered as `od19_after_sales_reporting` (6 KPI views); ยังต้อง verify บน `odoo19_pdev`
- ไม่มีการแก้ไขไฟล์ core ของ Odoo

## 15. Gate Readiness Summary

- Spec-ready: ✅
- Plan-ready: ✅ (KPI aggregation delivered as `od19_after_sales_reporting`)
- Build-ready: ⏳ (รอ verify การติดตั้ง/tests บน `odoo19_pdev`)

## 16. คำตัดสินของ Child Spec นี้

ใช้ OCA `helpdesk_mgmt` และ core `addons/repair` เป็นแกน after-sales ผสานกับโมดูล in-house ที่มีอยู่ (`od19_helpdesk_extension`, `od19_service_warranty`, `od19_service_card`, `od19_product_return`, `od19_quality_control`, `od19_document_sign`) โดยแยก service-linked stock behavior ออกจาก Inventory core อย่างชัดเจน และใช้ signature infrastructure ของ Odoo 19 CE แทน OCA `sign_oca` เพื่อลด dependency ภายนอก เหมาะกับบริบท Auto-Info ที่ต้องการ lean, stable, secure และดูแลรักษาง่าย
