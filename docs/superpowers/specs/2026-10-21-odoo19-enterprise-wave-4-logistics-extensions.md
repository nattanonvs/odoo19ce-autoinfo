# Odoo 19 CE Wave 4: Logistics Extensions

## Control Metadata
- Child spec ID: W4-LOGISTICS-EXT
- Wave: Wave 4 (Logistics extensions)
- Status: Partially implemented — Transportation, Stock Valuation Adjustment, FIFO valuation, picking features, delivery label, and the Thai purchase-requisition extension (`od19_purchase_request_extend`) are present on disk; the Internal Stock Request gap is resolved by adopting OCA `stock_request` (repo `OCA/stock-logistics-request`, branch 19.0 — added as submodule `third_party/oca/stock-logistics-request` and wired into `addons_path`); Landed Cost activation (core `stock_landed_costs`) remains a configuration task; the legacy `Goods Issue` decision is **resolved (2026-10-21) — kept as a Thai document/UX layer (`od19_goods_issue`) on top of OCA `stock_request`**
- Owner: Logistics lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Canonical path: `docs/superpowers/specs/2026-10-21-odoo19-enterprise-wave-4-logistics-extensions.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-21
- Primary readers: ฝ่ายคลังสินค้า, ฝ่ายขนส่ง, ฝ่ายจัดซื้อ, ฝ่ายขาย, ฝ่ายบัญชี, ผู้จัดการแผนก, ทีมเทคนิค

## Approval Traceability
- Scope baseline (Stock Requests, Transportation, Logistics extensions, Stock Valuation Adjustment, Landed Cost) approved in the Wave Control Register on 2026-10-12.
- Stock Valuation Adjustment module `od19_stock_valuation_adjustment` present on disk; Stock Requests, Transportation, Logistics extensions, and Landed Cost were recorded as not started at that time.
- 2026-10-21: ผู้ใช้อนุมัติแนวทางเขียนสเปกตามสภาพจริงบนดิสก์ และให้อัปเดตเอกสารกำกับให้สอดคล้องพร้อมกัน
- 2026-10-21: ผู้ใช้ตัดสินใจ **Internal Stock Request = ดึง OCA `stock_request` เข้ามาใช้** (OCA-First) — เพิ่ม git submodule `third_party/oca/stock-logistics-request` (branch 19.0) และเพิ่ม path เข้า `odoo.conf`; modules `stock_request` (+ `stock_request_purchase` auto-install) พร้อมติดตั้ง
- 2026-10-21: ผู้ใช้ตัดสินใจ **legacy `Goods Issue` = Keep เป็นชั้นเอกสาร (ใบเบิก/ใบหยิบ) ทับบน OCA `stock_request`** — ไม่ก็อปโมเดล legacy และไม่ Retire กระบวนการ; พัฒนาเป็นโมดูล `od19_goods_issue` (เอกสารพิมพ์ได้ + ฟิลด์แผนก/งาน/เหตุผล + รันเลขตามแผนก)

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` (Wave 4 scope and focus)
  - `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md` (Inventory execution baseline)
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-master-plan.md` (Legacy inventory to new coverage table)
  - `Odoo15Backup/` legacy landscape (module names only)
- Verified current state on disk (2026-10-21):
  - `custom_addons/od19_stock_valuation_adjustment/` — `od19.stock.valuation.adjustment` + `.line` (state `draft → confirmed → done → cancelled`), approval restricted to inventory managers, creates journal entries for real-time valuation categories; sequence data, security, tests
  - `custom_addons/od19_transportation/` — `od19.transport.order` (state `draft → waiting_approval → confirmed → in_transit → delivered / cancelled`) + `od19.transport.route`, `stock.picking` link; tier validation (transport cost ≥ 50,000 THB → Stock Manager); depends `stock, delivery, fleet, base_tier_validation`
  - `custom_addons/od19_stock_fifo/` — FIFO valuation service (abstract) + as-of wizard + BF revaluation wizard; monthly XLSX report by email + cron; depends `stock, stock_account, mail` (+ `openpyxl`)
  - `custom_addons/od19_stock_picking_features/` — `stock.picking` signature-chain auto-resolve (salesperson + department manager) + additional print lines (`od19.stock.picking.additional.line`); depends `stock, sale_stock, hr`
  - `custom_addons/od19_delivery_label/` — delivery label (FM-PU-12) with department code (`hr.department.od19_department_code`), delivery reasons, contact fields, QWeb report; depends `stock, sale_stock, project_stock, hr, od19_sales_project_context, od19_inventory_execution_control, od19_iso_document_control`
  - `custom_addons/od19_purchase_request_extend/` — **implemented** (not a stub) — extends OCA `purchase_request` (`purchase.request`) with Thai fields (`od19_request_reason`, `od19_priority`, `department_id`, `od19_budget_year`, `od19_issue_id`) and `purchase.request.line` (`od19_justification`, `od19_asset_id`); raises the request reason for Urgent/Emergency and sends multi-channel notifications on approve/reject; depends `purchase_request, purchase_request_tier_validation, hr, account_asset_management, od19_internal_issue, od19_notification_multi_channel`; views, security, and tests present
  - Core module present: `addons/stock_landed_costs/` (WMS Landed Costs; depends `stock_account, purchase_stock`)
  - OCA modules present in `third_party/oca/purchase-workflow/`: `purchase_request` (19.0.1.0.2), `purchase_request_type`; `purchase_request_tier_validation` under `third_party/oca/tier-validation/`
  - OCA `stock_request*` modules: **adopted 2026-10-21** — submodule `third_party/oca/stock-logistics-request` (branch 19.0) provides `stock_request` (19.0.1.0.2, depends `stock`) and `stock_request_purchase` (19.0.1.0.0, depends `stock_request, purchase_stock`, `auto_install=True`); path added to `odoo.conf` `addons_path`
  - `custom_addons/od19_goods_issue/` — **new 2026-10-21** — Thai Goods Issue document layer on OCA `stock_request`: `od19.goods.issue.type` (master data); extends `stock.request.order` with `od19_issue_type_id`, `department_id`, `od19_employee_id`, `od19_job_id`, `od19_reason` + per-department sequence (`GI/{DEPT}/`, code `od19.goods.issue.<dept_id>`, fallback `GI/GEN/`); extends `stock.picking` with `od19_goods_issue_reason` / `od19_goods_issue_department_id` (computed from the linked request order); two QWeb reports (`ใบเบิกสินค้า` on `stock.request.order`, `ใบหยิบสินค้า` on `stock.picking`, A4, Thai font stack, maroon `#9E2424`, 3 signature blocks each); depends `stock_request, hr, project, od19_iso_document_control`; views, security (ACL + multi-company rule), and tests present
- Evidence findings:
  - Stock Valuation Adjustment is implemented and outward-facing as `od19.stock.valuation.adjustment` (not a direct copy of legacy `dtr_stock_valuation_adjustment`).
  - Landed Cost is available through **core** `stock_landed_costs` — activation is a configuration/enablement task, not new development.
  - Purchase **requisition** (ขอซื้อ) is covered: OCA `purchase_request` is the base and `od19_purchase_request_extend` is implemented.
  - Internal **Stock Request** (ขอเบิก/ขอโอนสินค้าภายใน) is covered by OCA `stock_request` — model `stock.request` / `stock.request.order` with state `draft → open → done → cancel`, allocation to `stock.move`/`stock.picking`, security groups `group_stock_request_user` / `group_stock_request_manager` / `group_stock_request_order`, and its own sequence. No custom stock-request module is required.
  - Legacy **`Goods Issue`** is a real process (ใบเบิก/ใบหยิบสินค้าภายใน) — decided 2026-10-21 to **keep it as a Thai document/UX layer** (`od19_goods_issue`) on top of OCA `stock_request`: the movement truth stays in standard stock moves/pickings, while the module adds printable ใบเบิกสินค้า / ใบหยิบสินค้า, department/job/reason fields, and per-department running numbers. The separate legacy "ส่งของให้ลูกค้า" model (`dtr_sales_services` `goods.issue`) is **not** re-implemented — it is already covered by the standard delivery/picking flow.
- Evidence coverage gaps:
  - Legacy source addons for transportation and non-standard warehouse convenience flows are still not on disk for direct comparison — treat their designs as redesign-from-governance, not migrate.
  - No confirmed non-standard warehouse flow inventory.

## Delivery Controls
- Dependencies:
  - Wave 1 Inventory baseline (`od19_inventory_execution_control`, `od19_inventory_audit_count`, `od19_inventory_reporting`) stable
  - Core `stock_landed_costs`; OCA `purchase_request*` (present); OCA `stock_request` + `stock_request_purchase` (adopted, submodule present); OCA `base_tier_validation` (present)
  - `od19_goods_issue` depends on `stock_request`, `hr`, `project`, and `od19_iso_document_control` (for `hr.department.code`)
  - Wave 3 where service returns interact with pickings
- Gate readiness:
  - Spec-ready: ✅ scope, boundary, valuation adjustment, stock request (OCA), Goods Issue document layer, and landed cost are defined
  - Plan-ready: ✅ Internal Stock Request approach fixed (OCA `stock_request`); `Goods Issue` decision fixed (2026-10-21) = Thai document layer `od19_goods_issue`
  - Build-ready: ⏳ Stock Request + Goods Issue modules approved and wired (installation pending on `odoo19_pdev`); Landed Cost enabled and verified on `odoo19_pdev`

---

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบแกน `Logistics Extensions` ของ Wave 4 ให้ต่อยอดจาก Inventory baseline ของ Wave 1 ครอบคลุม:

- `Stock Requests` (การขอเบิก/ขอโอนสินค้าภายใน)
- `Transportation` (การขนส่ง)
- `Logistics extensions` (ส่วนขยายงานคลัง/ขนส่ง)
- `Stock Valuation Adjustment` (การปรับมูลค่าสต็อก)
- `Landed Cost` (การปันส่วนต้นทุนขนส่ง/นำเข้า)

หัวใจของ Wave นี้คือทำให้ระบบตอบได้ว่า:

- การขอและอนุมัติเบิก/โอนสินค้าภายในมีร่องรอยหรือไม่
- การขนส่งผูกกับ picking และมี tier validation ตามวงเงินหรือไม่
- การปรับมูลค่าสต็อกมี audit trail และกระทบบัญชีถูกต้องหรือไม่
- ต้นทุนขนส่ง/นำเข้าถูกปันส่วนเข้าต้นทุนสินค้าถูกต้องหรือไม่
- legacy `Goods Issue` ถูกจัดวางเป็นชั้นเอกสาร (ใบเบิก/ใบหยิบ) บน standard movement truth แล้วหรือไม่

โดเมนนี้ต้องรอให้ Inventory baseline เสถียรในสภาพการใช้งานจริงก่อน แล้วจึงขยาย โดยยึดหลัก redesign มากกว่า migrate ตรงสำหรับงานขนส่งและงานคลังที่มิใช่มาตรฐาน

## 2. เป้าหมายของ Child Spec นี้

- ขยายงานโลจิสติกส์บนพื้นฐาน Inventory ที่เสถียร โดยไม่รื้อ Inventory core
- ใช้ core `stock_landed_costs` และ OCA `purchase_request*` เป็นฐาน (OCA-First)
- ให้การปรับมูลค่าสต็อกมี audit trail และกระทบบัญชีครบ
- ให้ทุก addon ติดตั้ง/ถอนได้โดยไม่กระทบเสถียรภาพระบบ
- คง legacy `Goods Issue` ไว้เป็นชั้นเอกสาร/UX (`od19_goods_issue`) บน OCA `stock_request` โดยไม่ก็อปโมเดล legacy และตัดสินใจเรื่อง non-standard warehouse flows อย่างมีหลักฐาน

## 3. ขอบเขตของ Child Spec

### 3.1 อยู่ใน scope (ในก้อนนี้)
- Stock Requests:
  - **Purchase Requisition (ขอซื้อ)** — ใช้ OCA `purchase_request*` + `od19_purchase_request_extend`
  - **Internal Stock Request (ขอเบิก/ขอโอนสินค้าภายใน)** — ใช้ OCA `stock_request` (ตัดสินใจแล้ว 2026-10-21)
  - **Goods Issue document layer (ใบเบิก/ใบหยิบสินค้า)** — `od19_goods_issue` ทับบน OCA `stock_request` (ตัดสินใจแล้ว 2026-10-21)
- Transportation: `od19_transportation` (transport order + route + tier validation)
- Logistics extensions: `od19_stock_picking_features` (signature chain + additional print lines), `od19_delivery_label` (FM-PU-12), `od19_stock_fifo` (FIFO valuation + monthly report)
- Stock Valuation Adjustment: `od19_stock_valuation_adjustment`
- Landed Cost: เปิดใช้ core `stock_landed_costs` + configuration สำหรับปันส่วนต้นทุน
- การตัดสินใจ legacy `Goods Issue` (ปิดแล้ว 2026-10-21) และ non-standard warehouse flows

### 3.2 ไม่อยู่ใน scope (Out of scope)
- การแก้ไขไฟล์ core ของ Odoo
- การรื้อ Inventory execution/audit/reporting baseline ของ Wave 1
- การก็อปโมเดล legacy `dtr.goods.issue` / `dtr.goods.picking` ตรง ๆ หรือสร้าง stock request model ใหม่ซ้ำกับ OCA
- การทำ "goods issue" สำหรับส่งของให้ลูกค้า (legacy `dtr_sales_services` `goods.issue`) — ปกคลุมด้วย delivery/picking มาตรฐานแล้ว
- Service-linked returns (อยู่ Wave 3)
- การทำ warehouse management (WMS) เต็มรูปแบบเกินความจำเป็น
- การทำ transportation engine ที่ซ้ำกับ `fleet` โดยไม่จำเป็น

## 4. Current-State Summary

Wave 4 มีการพัฒนาบนดิสก์บางส่วนแล้ว (2026-10-21):

| โดเมน | โมดูล/แหล่ง | สถานะบนดิสก์ |
| --- | --- | --- |
| Stock Valuation Adjustment | `od19_stock_valuation_adjustment` | Implemented — approval workflow + JE + tests |
| Transportation | `od19_transportation` | Implemented — transport order/route + tier validation + tests |
| Logistics extensions | `od19_stock_picking_features`, `od19_delivery_label`, `od19_stock_fifo` | Implemented |
| Landed Cost | core `addons/stock_landed_costs` | Available — ต้องเปิดใช้/ตั้งค่า |
| Purchase Requisition | OCA `purchase_request*` + `od19_purchase_request_extend` | Implemented — Thai extension บน OCA purchase_request (priority/department/budget year/reason/asset link + tier-validation notifications) |
| Internal Stock Request | OCA `stock_request` (+ `stock_request_purchase`) — submodule `third_party/oca/stock-logistics-request` | **Adopted** — ดึง OCA เข้ามาใช้ (ตัดสินใจ 2026-10-21); รอติดตั้งบน `odoo19_pdev` |
| `Goods Issue` | `od19_goods_issue` — Thai document layer บน OCA `stock_request` | **Keep — ชั้นเอกสารใบเบิก/ใบหยิบ** (ตัดสินใจ 2026-10-21) — ฟิลด์แผนก/งาน/เหตุผล + รันเลขตามแผนก `GI/{DEPT}/` + รายงาน ใบเบิกสินค้า/ใบหยิบสินค้า; รอติดตั้งบน `odoo19_pdev` |

## 5. Keep / Refactor / Replace / Retire

- Keep
  - Wave 1 Inventory baseline (`od19_inventory_execution_control`, `od19_inventory_audit_count`, `od19_inventory_reporting`)
  - Core `stock_landed_costs`; OCA `purchase_request*`, `stock_request` + `stock_request_purchase`, `base_tier_validation`
  - `od19_stock_valuation_adjustment`, `od19_transportation`, `od19_stock_picking_features`, `od19_delivery_label`, `od19_stock_fifo`
  - **`od19_goods_issue`** — คงกระบวนการ ใบเบิก/ใบหยิบสินค้า ไว้เป็นชั้นเอกสาร/UX บน OCA `stock_request` (ตัดสินใจ 2026-10-21); ไม่อยู่ใน Retire อีกต่อไป
- Refactor
  - `od19_purchase_request_extend` — ตรวจสอบ/คงไว้เป็น Thai extension ของ purchase requisition (implemented แล้ว ไม่ใช่ stub); หากต้องการ internal Stock Request (ขอเบิก/ขอโอน) ให้เพิ่มแยกต่างหาก
  - `stock.request.order` — เติมฟิลด์ไทย (department/job/reason/issue type) และรันเลขตามแผนก โดยไม่แตะ logic การ allocate ของ OCA
  - รวม non-standard warehouse convenience logic เป็น standard movement flow
- Replace
  - Legacy `dtr_stock_valuation_adjustment` → `od19_stock_valuation_adjustment` (standard inventory value adjustment + audit trail)
  - Legacy transportation flow → redesign (`od19_transportation`) ไม่ migrate ตรง
  - Legacy `dtr.goods.issue` / `dtr.goods.picking` (document + numbering + approval) → `od19_goods_issue` บน OCA `stock_request` + standard stock moves
- Retire
  - Legacy โมเดลเอกสาร `dtr.goods.issue` / `dtr.goods.picking` (ก็อปตรง) — แทนด้วยชั้นเอกสารบน OCA `stock_request`
  - ขั้นตอนคลังแบบ manual/ชั่วคราวที่ซ้ำกับ standard movement

## 6. Future-State Design

### 6.1 Stock Requests
- **Purchase Requisition (ขอซื้อ) — Implemented แล้ว**: ใช้ OCA `purchase_request` (+ `purchase_request_type`) เป็นฐาน และ `od19_purchase_request_extend` เติมฟิลด์ไทย (priority/department/budget year/request reason) + asset link + tier-validation notifications
- **Internal Stock Request (ขอเบิก/ขอโอนสินค้าภายใน) — ตัดสินใจแล้ว: ใช้ OCA `stock_request`** (2026-10-21)
  - Repository: `OCA/stock-logistics-request` branch `19.0` — เพิ่มเป็น submodule `third_party/oca/stock-logistics-request` และเพิ่ม path เข้า `odoo.conf`
  - Modules: `stock_request` (depends `stock`) + `stock_request_purchase` (depends `stock_request, purchase_stock`, `auto_install=True` → เปิดใช้ขอเบิกที่กลายเป็นใบสั่งซื้ออัตโนมัติ)
  - Model: `stock.request` / `stock.request.order` — state `draft → open → done → cancel`; allocation ไปยัง `stock.move` / `stock.picking`; sequence ของตัวเอง
  - Security: `group_stock_request_user` / `group_stock_request_manager` / `group_stock_request_order`
  - งานที่เหลือ: ติดตั้งโมดูลบน `odoo19_pdev`, ตั้งค่า warehouse/route/sequence และตรวจ log ให้ไม่มี warning (configuration task ไม่ใช่ development)
- **Goods Issue document layer (ใบเบิก/ใบหยิบสินค้า) — ตัดสินใจแล้ว: Keep เป็นชั้นเอกสารบน OCA `stock_request`** (2026-10-21) → โมดูล `od19_goods_issue`
  - หลักคิด: "movement truth" อยู่ใน standard stock move / picking; โมดูลนี้เติม **เอกสาร + ฟิลด์ธุรกิจไทย + เลขรันตามแผนก** เท่านั้น (ไม่ก็อปโมเดล legacy)
  - Master data: `od19.goods.issue.type` (ประเภทการเบิก)
  - ขยาย `stock.request.order`: `od19_issue_type_id`, `department_id` (compute/store/readonly=False จาก `requested_by`), `od19_employee_id` (ผู้ขอเบิก), `od19_job_id` (`project.project`), `od19_reason`; prefill แผนก/พนักงานจากผู้ใช้ปัจจุบันผ่าน `default_get`
  - เลขที่เอกสาร: sequence **ต่อแผนก** — code `od19.goods.issue.<department_id>`, prefix `GI/{DEPT_CODE}/`, padding 5 (fallback `GI/GEN/` เมื่อไม่มีแผนก) โดยใช้ `hr.department.code` จาก `od19_iso_document_control`
  - ขยาย `stock.picking`: `od19_goods_issue_reason` และ `od19_goods_issue_department_id` (compute+store, readonly=False) ดึงจาก `stock_request_ids.order_id`
  - รายงาน QWeb (A4, Thai font stack, maroon `#9E2424`, ลายเซ็น 3 ช่อง): **ใบเบิกสินค้า** (`stock.request.order`) และ **ใบหยิบสินค้า** (`stock.picking`)
  - Security: ACL ของ `od19.goods.issue.type` + global multi-company `ir.rule`; สิทธิ์เอกสารใช้กลุ่ม OCA `stock_request` เดิม
  - งานที่เหลือ: ติดตั้งบน `odoo19_pdev` และตรวจ log ให้ไม่มี warning

### 6.2 Transportation
`od19.transport.order` ครบ state `draft → waiting_approval → confirmed → in_transit → delivered / cancelled`; `od19.transport.route` เก็บต้นทาง/ปลายทาง/ระยะทาง; ผูกกับ `stock.picking`; tier validation เมื่อค่าขนส่ง ≥ 50,000 THB → Stock Manager

### 6.3 Logistics extensions
- Picking features: auto-resolve signature chain (salesperson + dept manager) และ additional print lines
- Delivery label FM-PU-12: แสดง CODE / Customer / Project / DEPT พร้อมเหตุผลการส่ง (ภาษาไทย)
- FIFO valuation: บริการคำนวณ FIFO (ไม่พึ่ง SVL), as-of wizard, BF revaluation wizard, รายงาน XLSX รายเดือนทางอีเมล + cron

### 6.4 Stock Valuation Adjustment
`od19.stock.valuation.adjustment` + `.line` (audit trail) ครบ state; เฉพาะ inventory manager อนุมัติ; สร้าง journal entry สำหรับ valuation category แบบ real-time

### 6.5 Landed Cost
เปิดใช้ core `stock_landed_costs` สำหรับปันส่วนค่าขนส่ง/นำเข้าเข้าต้นทุนสินค้า (ไม่มี custom development) — เป็น **configuration/enablement task**:
- ติดตั้งโมดูล core `stock_landed_costs` บน `odoo19_pdev`
- ตั้งค่า product ประเภท `service` + `landed_cost_ok = True` สำหรับค่าขนส่ง/ศุลกากรที่ต้องการปันส่วน
- กำหนด valuation adjustment (by quantity / by current cost / by weight / by volume / equal) ตามนโยบายฝ่ายบัญชี
- ผูกใบรับสินค้า (`stock.picking` incoming) กับ landed cost แล้ว post เพื่อกระทบ `stock.valuation.layer` และ GL ผ่าน `stock_account`
- จัดทำคู่มือใช้งาน (ฝ่ายคลัง + ฝ่ายบัญชี) — อยู่ในขอบเขต training ไม่ใช่ development

## 7. Boundary กับโดเมนอื่น

- กับ Inventory (Wave 1): Wave 4 ต่อยอด ไม่รื้อ; การนับ/adjust สต็อกพื้นฐานอยู่ Wave 1
- กับ After-Sales (Wave 3): service returns อยู่ Wave 3; Wave 4 รับ picking ที่เกี่ยวกับโลจิสติกส์
- กับ Accounting (Wave 2): valuation adjustment และ landed cost กระทบ GL ผ่าน standard posting
- กับ Fleet (Wave 5): Transportation ใช้ `fleet` เป็นข้อมูลยานพาหนะ ไม่สร้างซ้ำ

## 8. Reporting และ KPI Needs

- Transportation: จำนวนงานขนส่ง, ค่าขนส่งตามช่วง, on-time delivery
- Stock Requests: backlog ของคำขอเบิก/อนุมัติ, lead time
- Valuation adjustment: จำนวน/มูลค่าการปรับ และเหตุผล
- FIFO report รายเดือน (XLSX) + valuation by lot
- Landed cost allocation summary
- รายงานที่พิมพ์ออกมา (delivery label ฯลฯ) ต้องมี Dual Report Format ตาม Wave 2

## 9. Security และ Control Model

- การปรับมูลค่าสต็อก (valuation adjustment) จำกัดเฉพาะ inventory manager (segregation of duties)
- Transportation tier validation (≥ 50,000 THB) ใช้ OCA `base_tier_validation`
- Stock Request approval ใช้ security groups ของ OCA `stock_request` (`group_stock_request_user` / `group_stock_request_manager` / `group_stock_request_order`); สามารถเสริม tier validation ได้หากต้องการอนุมัติตามวงเงิน
- Backdating การเคลื่อนไหวสต็อกจำกัดเฉพาะ inventory manager (ตาม Wave 1 control)
- Landing cost valuation posting อ้างอิง `stock_account` standard

## 10. Migration Assumptions

- Master data สินค้า/คลัง/ยานพาหนะ อ้างอิงจาก Wave 1 และ `fleet` (Wave 5)
- ยอดสต็อกและมูลค่าคงเหลือจากระบบเดิมยกมาเป็นยอดตั้งต้นตามข้อตกลงฝ่ายคลัง/บัญชี
- Legacy `Goods Issue` ตัดสินใจแล้ว (2026-10-21): ไม่ migrate โมเดล legacy ตรง ๆ แต่ Implement เป็นชั้นเอกสาร/UX (`od19_goods_issue`) ทับบน OCA `stock_request`; non-standard warehouse flows อื่น ๆ ยังต้องประเมินเป็นรายกรณี
- Legacy source transport/warehouse addon ไม่ได้อยู่บนดิสก์ — ใช้เอกสาร governance และการสัมภาษณ์

## 11. Training Impact

- ฝ่ายคลัง: การใช้ stock request, valuation adjustment และ delivery label
- ฝ่ายขนส่ง: การสร้าง/อนุมัติ transport order และ route
- ฝ่ายคลัง/บัญชี: การปันส่วน landed cost และการอ่าน FIFO report
- ผู้จัดการ: tier validation และการอนุมัติ

## 12. Test Strategy

- Unit/Integration tests (post-install): Transportation lifecycle + tier validation, Valuation adjustment workflow + JE, FIFO computation + wizards, Delivery label rendering + dept code, Picking signature chain
- Report tests: delivery label QWeb แสดงไทยถูกต้อง; FIFO XLSX generation
- Security tests: valuation adjustment เฉพาะ inventory manager; tier validation triggers; stock request group access (OCA own test suite)
- Stock Request: ใช้ชุดทดสอบของ OCA `stock_request` เอง + smoke test บน `odoo19_pdev`
- Landed Cost: smoke test การปันส่วนค่าขนส่งเข้าต้นทุนสินค้า (core)
- การรัน Unit Test ต้องรันโดยผู้ใช้ผ่าน Terminal บนเครื่องโดยตรง

## 13. Known Unknowns

- ~~แนวทาง Internal Stock Request: เพิ่ม OCA `stock_request` หรือสร้าง custom module~~ → **ปิดแล้ว (2026-10-21): ใช้ OCA `stock_request`** (submodule `third_party/oca/stock-logistics-request` 19.0)
- ~~การตัดสินใจ legacy `Goods Issue`~~ → **ปิดแล้ว (2026-10-21): Keep เป็นชั้นเอกสาร/UX (`od19_goods_issue`) บน OCA `stock_request`**; non-standard warehouse flows อื่น ๆ ยังเปิดอยู่
- ขอบเขตการปันส่วน landed cost (สินค้า/ใบรับใด) และผังบัญชีที่ใช้
- ระดับความต้องการ WMS จริง
- จะเสริม tier validation บน OCA `stock_request` ตามวงเงินหรือไม่ (optional)

## 14. Definition of Done ระดับสเปก

- โมดูล Wave 4 ทั้งหมดติดตั้งได้บน `odoo19_pdev` โดย log ไม่มี warning จากโมดูลเอง
- ปิดช่องว่าง: ✅ Internal Stock Request (ใช้ OCA `stock_request` — submodule พร้อมแล้ว รอติดตั้ง) และ ⏳ Landed Cost เปิดใช้ + ตั้งค่า + คู่มือ (purchase requisition ปิดแล้วด้วย `od19_purchase_request_extend`)
- Valuation adjustment และ Transportation ทดสอบผ่านรวมทั้ง security/tier validation
- ~~ตัดสินใจเรื่อง `Goods Issue` เป็นลายลักษณ์อักษร~~ → **✅ ปิดแล้ว (2026-10-21): Keep เป็นชั้นเอกสาร/UX (`od19_goods_issue`) บน OCA `stock_request`** (โมดูลพร้อมติดตั้ง)
- ไม่มีการแก้ไขไฟล์ core ของ Odoo

## 15. Gate Readiness Summary

- Spec-ready: ✅
- Plan-ready: ✅ (Internal Stock Request fixed = OCA `stock_request`; `Goods Issue` fixed = `od19_goods_issue` document layer on OCA `stock_request`)
- Build-ready: ⏳ (Stock Request wired, installation pending; Landed Cost enablement pending on `odoo19_pdev`)

## 16. คำตัดสินของ Child Spec นี้

ขยายงานโลจิสติกส์บนพื้นฐาน Inventory ที่เสถียร โดยใช้ core `stock_landed_costs` และ OCA `purchase_request*` + `stock_request` เป็นฐาน ผสานโมดูล in-house ที่มีอยู่ (`od19_stock_valuation_adjustment`, `od19_transportation`, `od19_stock_picking_features`, `od19_delivery_label`, `od19_stock_fifo`) ปิดช่องว่าง Internal Stock Request ด้วยการดึง OCA `stock_request` (submodule `third_party/oca/stock-logistics-request` branch 19.0) เปิดใช้ Landed Cost ผ่าน core โดยไม่พัฒนา custom ซ้ำ และปิดประเด็น legacy `Goods Issue` เป็นลายลักษณ์อักษรแล้วในรอบนี้ (2026-10-21) ด้วยการ Implement เป็นชั้นเอกสาร/UX (`od19_goods_issue`) ทับบน OCA `stock_request` แทนการก็อปโมเดล legacy หรือ Retire กระบวนการ — ยึดหลัก OCA-First, redesign มากกว่า migrate ตรง เหมาะกับบริบท Auto-Info ที่ต้องการ lean, stable, secure และดูแลรักษาง่าย
