# OCA Module Matching Report: Gaps → OCA Solutions

**วันที่:** 2026-10-14
**วัตถุประสงค์:** จับคู่ฟีเจอร์ที่ยังขาดจาก Gap Analysis กับ OCA modules ที่มีอยู่ใน `third_party/oca` หรือสามารถดึงมาใช้จาก OCA GitHub เพื่อหลีกเลี่ยงการพัฒนา custom module

**สัญลักษณ์:**
- ✅ มี OCA module ครอบคลุม (อยู่ใน third_party แล้ว)
- 🟡 มี OCA module ครอบคลุมบางส่วน (ต้องปรับแต่งเล็กน้อย)
- 🔵 มี OCA module ใน OCA GitHub (ยังไม่ได้ clone เข้ามา)
- ❌ ไม่มี OCA module (ต้องพัฒนาเอง)

---

## 1. Sales (การขาย)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| 7 master report models (price, delivery, payment product/engineering, validity, warranty, credit) | `base_comment_template` + `sale_order_note_template` | 🟡 | ใช้ comment template สำหรับ terms/conditions ที่เป็นข้อความ แต่ master report models ที่เป็น data-driven ต้อง custom |
| Wizard เปลี่ยนวันที่จัดส่งทั้งเอกสาร | `sale_order_line_date` + `sale_delivery_split_date` | ✅ | `sale_order_line_date` เพิ่ม commitment_date ต่อบรรทัด สามารถเขียน wizard เล็กๆ เพื่ออัปเดตทุกบรรทัดได้ หรือใช้ `sale_order_line_date` + mass edit ได้เลย |
| Wizard "Get Sale Order Lines" บน invoice | `sale_product_set` | 🟡 | `sale_product_set` อนุญาตให้เพิ่มชุดสินค้า แต่ไม่ใช่ดึงจาก SO อื่นๆ — ต้อง custom เล็กน้อยเพื่อเปลี่ยน source เป็น SO |
| Downpayment invoice linking (origin_second/po_origin) | `sale_advance_payment` + `purchase_advance_payment` | ✅ | `sale_advance_payment` รองรับ advance payment บน SO และเชื่อมกับ invoice |
| Cancel Reason บน SO | `sale_cancel_reason` | ✅ | มี wizard cancel พร้อมเหตุผล พร้อม mass cancel |
| Validity period auto-cancel | `sale_validity_auto_cancel` | ✅ | Cron อัตโนมัติยกเลิก SO ที่หมดอายุ |
| Sale Order Type (แยกประเภท) | `sale_order_type` | ✅ | มี model sale.order.type พร้อมกำหนดค่า default ต่างๆ |
| Sub-state บน SO | `sale_substate` + `base_substate` | ✅ | มี sub-state management พร้อม workflow |
| Tier Validation บน SO | `sale_tier_validation` | ✅ | รองรับหลายระดับอนุมัติ |
| Trade discount บน SO | `sale_order_general_discount` | ✅ | ส่วนลดทั้งเอกสาร |
| Triple discount บน SO line | `account_invoice_triple_discount` (dependency) | ✅ | ส่วนลด 3 ชั้นต่อบรรทัด |
| Last price info | `sale_last_price_info` | ✅ | แสดงราคาล่าสุดบน product |

---

## 2. Purchase (การจัดซื้อ)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Trade Discount Wizard | `purchase_order_general_discount` + `purchase_triple_discount` | ✅ | ส่วนลดทั้งเอกสาร และ 3 ชั้นต่อบรรทัด |
| 5 master report models (warranty, delivery_to, term, shipment, weight) | `base_comment_template` + `purchase_default_terms_conditions` | 🟡 | Terms/conditions จาก template แต่ data-driven models ต้อง custom |
| PR line pricing (price_unit, discount, taxes) | `purchase_request` (core) | 🟡 | `purchase_request` มี PR line พร้อม price_unit/discount แต่ taxes อาจต้องปรับแต่ง |
| Analytic จาก project บน PR/PO | Odoo native `analytic_distribution` (Odoo 19) + `purchase_request` | ✅ | Odoo 19 มี analytic_distribution บน PO line โดยธรรมชาติ และสามารถดึงจาก project ได้ |
| vendor_ref / your_ref บน PR | `purchase_request` core | 🟡 | มี field partner_ref อยู่แล้ว บางเวอร์ชัน ถ้าไม่มีต้องเพิ่ม |
| Cancel Reason บน PO | `purchase_tier_validation` + `base_cancel_confirm` | 🟡 | ไม่มี cancel reason โดยตรง แต่สามารถใช้ `base_cancel_confirm` |
| Purchase Order Type | `purchase_order_type` | ✅ | มี model purchase.order.type |
| Purchase Request Type | `purchase_request_type` | ✅ | มี model purchase.request.type |
| Tier Validation บน PO | `purchase_tier_validation` | ✅ | รองรับหลายระดับอนุมัติ |
| Purchase deposit/advance payment | `purchase_deposit` + `purchase_advance_payment` | ✅ | สร้าง deposit/advance จาก PO |
| Last price info | `purchase_last_price_info` | ✅ | แสดงราคาซื้อล่าสุดบน product |
| Purchase stock price unit sync | `purchase_stock_price_unit_sync` | ✅ | อัปเดต cost price ใน stock moves ที่ทำแล้ว |

---

## 3. Accounting (การบัญชี)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Asset Disposal Workflow | `account_asset_disposal` (OCA/account-financial-tools) | 🔵 | มีใน OCA GitHub สำหรับเวอร์ชันเก่า ต้องตรวจสอบ Odoo 19 หรือ port มาใช้งาน |
| WHT PDF Print (4 แบบ: ภงด.1, ภงด.3, ภงด.53, ภงด.53 ทริส) | `l10n_th_account_tax` + `l10n_th_withholding_tax_cert_form` | ✅🔵 | `l10n_th_account_tax` **อยู่ใน third_party แล้ว มี WHT cert และ PND1/PND3/PND53 forms `l10n_th_withholding_tax_cert_form` อยู่ใน OCA GitHub |
| WHT base computed + wht.type model | `l10n_th_account_tax` | ✅ | มี model `withholding.tax.code.income`, `withholding.tax.cert`, WHT calculation บน payment |
| Cancel Reason Wizard บน invoice | `account_move_cancel_confirm` + `account_invoice_refund_reason` (OCA/account-invoicing) | 🔵 | `account_move_cancel_confirm` ยืนยันการ cancel `account_invoice_refund_reason` เหตุผลคืนเงิน |
| Payer/Payee บน prepayment | `account_payment_partner` (OCA/bank-payment) | 🔵 | เพิ่ม payment mode และ partner บน payment |
| Create vendor bill from PO wizard | Odoo native + `purchase` | ✅ | Odoo มี native "Create Bill" จาก PO อยู่แล้ว |
| BOT URL config | ต้อง custom | ❌ | ไม่มี OCA module เฉพาะ |
| Prepayment actual due date (+30 days) | `account_payment_partner` + custom cron | 🟡 | ใช้ custom field + cron สำหรับ +30 days |
| Account Move sequence จาก sequence | `account_move_name_sequence` | ✅ | มีอยู่ใน third_party |
| Invoice chronology constraint | `account_invoice_constraint_chronology` | ✅ | บังคับวันที่เรียงลำดับ |
| Tier Validation บน invoice | `account_move_tier_validation` | ✅ | มีอยู่แล้ว |
| Cancel confirm บน invoice | `base_cancel_confirm` | ✅ | มี wizard cancel confirm |

---

## 4. Project (โครงการ)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Project Risk Report (SQL view + risk score) | `bi_sql_editor` | 🟡 | ใช้สร้าง SQL view สำหรับ risk report แต่ risk score logic ต้องเขียน SQL เอง |
| Hierarchical Project Type model | `project` native (Odoo) | 🟡 | Odoo มี project type แต่ hierarchical อาจต้อง custom |
| Task deadline email notification cron | `project` native + `base_automation` (Odoo native) | ✅ | ใช้ Automated Actions ธรรมชาติ |
| No backward stage change | `project_task_stage_force` หรือ custom constraint | 🟡 | ไม่มี OCA โดยตรง ต้อง custom หรือใช้ server action |
| Job Assignment Document fields | `project` native + custom fields | 🟡 | ต้อง custom fields |
| SO/PO linking จาก project | `sale_purchase_stock_auto_confirm` หรือ native | 🟡 | Odoo มี project linking กับ SO/PO แต่อาจต้อง custom |
| Project milestones | `project_milestone` (OCA/project) | 🔵 | มีใน OCA GitHub |
| Project budget | `project_budget` (OCA/project) | 🔵 | มีใน OCA GitHub |

---

## 5. HR/Expense/Fleet

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Department head as auto approver | `hr_expense_tier_validation` + `base_tier_validation_formula` | 🟡 | ใช้ tier validation formula เพื่อกำหนด approver จาก dept head อัตโนมัติ |
| Cash tracking state (expense) + return/reset wizards | ต้อง custom | ❌ | ไม่มี OCA module เฉพาะ |
| XLSX expense reports | `report_xlsx` + custom report | 🟡 | ใช้ `report_xlsx` เป็น base แล้วเขียน report เอง |
| Delegate approvals | `base_tier_validation_forward` | ✅ | มี forward tier validation |
| WHT for expense payment | `l10n_th_account_tax` | ✅ | WHT บน payment รองรับ expense ได้ |
| Insurance/Act expire date + email notification cron | `fleet` native + `base_automation` | 🟡 | Odoo fleet มี contract/insurance ใช้ Automated Actions สำหรับ email |
| Service done notification | `fleet` native + `base_automation` | 🟡 | ใช้ Automated Actions |
| Expense Tier Validation | `hr_expense_tier_validation` | ✅ | มีอยู่ใน third_party |

---

## 6. Stock/Inventory (สต็อก)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| FIFO valuation service + monthly stock report email cron | `stock_account` native + `stock_account_valuation_report` (OCA/stock-logistics-reporting) | 🔵 | Odoo มี FIFO native แต่ as-of report ต้องใช้ OCA module |
| FIFO as-of wizard | `stock_inventory_valuation_report` (OCA/stock-logistics-reporting) | 🔵 | มีใน OCA GitHub |
| BF revaluation | `stock landeds_costs` (Odoo native) | 🟡 | Odoo มี landed costs แต่ BF revaluation อาจต้อง custom |
| stock.picking.additional.line model | `purchase_landed_cost` (OCA) หรือ custom | 🟡 | ไม่มีโดยตรง แต่สามารถใช้ landed cost หรือ custom |
| Signature chain auto-resolve | `signature` (Odoo native) | 🟡 | Odoo มี sign app แต่ auto-resolve chain ต้อง custom |

---

## 7. Reports/Misc

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Document Signing (sign) | `sign` (Odoo native - Enterprise) | 🟡 | Odoo Sign เป็น Enterprise feature สำหรับ CE อาจต้องใช้ OCA หรือ custom |
| logo_iso field | custom field | ❌ | ไม่มี OCA module เฉพาะ |
| Skip date/sequence constraint | `l10n_th_base_sequence` + custom | 🟡 | `l10n_th_base_sequence` มี BE year แต่ skip constraint ต้อง custom |
| Runtime guard tool | `auditlog` + custom | 🟡 | ใช้ auditlog สำหรับ tracking แต่ runtime guard ต้อง custom |
| Abstract service preserve sale_line_ids/purchase_line_id | custom abstract model | ❌ | ไม่มี OCA module เฉพาะ ต้องสร้าง abstract |
| Sequence reset period | `sequence_reset_period` (server-ux) | ✅ | มีอยู่ใน third_party |
| Audit log (deleted/changed records) | `auditlog` (server-tools) | ✅ | มีอยู่ใน third_party |
| XLSX report engine | `report_xlsx` (reporting-engine) | ✅ | มีอยู่ใน third_party |
| PDF report parameters | `report_qweb_parameter` (reporting-engine) | ✅ | มีอยู่ใน third_party |

---

## 📊 สรุปภาพรวม

### OCA modules ที่มีอยู่แล้วใน third_party (สามารถใช้ได้ทันที)

| OCA Module | ครอบคลุมฟีเจอร์ |
|------------|-------------------|
| `l10n_th_account_tax` | WHT types, WHT cert, WHT calculation, PND forms, PIT |
| `l10n_th_amount_to_text` | แปลงตัวเลขเป็นข้อความไทย |
| `l10n_th_base_sequence` | Buddhist Era year ใน sequence |
| `auditlog` | Track deleted/changed records |
| `report_xlsx` | XLSX report engine |
| `account_asset_management` | Base asset management |
| `sale_cancel_reason` | Cancel reason บน SO |
| `sale_order_general_discount` | ส่วนลดทั้งเอกสารบน SO |
| `sale_order_line_date` | commitment date ต่อบรรทัด SO |
| `sale_delivery_split_date` | แยก delivery ตามวันที่ |
| `sale_order_type` | SO type |
| `sale_substate` | Sub-state บน SO |
| `sale_tier_validation` | Tier validation บน SO |
| `sale_validity_auto_cancel` | Auto-cancel SO หมดอายุ |
| `sale_advance_payment` | Advance payment บน SO |
| `sale_last_price_info` | ราคาขายล่าสุด |
| `purchase_order_general_discount` | ส่วนลดทั้งเอกสารบน PO |
| `purchase_triple_discount` | ส่วนลด 3 ชั้นบน PO |
| `purchase_order_type` | PO type |
| `purchase_request_type` | PR type |
| `purchase_tier_validation` | Tier validation บน PO |
| `purchase_deposit` | Deposit จาก PO |
| `purchase_advance_payment` | Advance payment บน PO |
| `purchase_last_price_info` | ราคาซื้อล่าสุด |
| `purchase_stock_price_unit_sync` | Sync ราคา cost ใน stock |
| `base_cancel_confirm` | Cancel confirm wizard |
| `account_move_name_sequence` | Sequence จาก journal entry |
| `account_invoice_constraint_chronology` | Chronology constraint |
| `account_move_tier_validation` | Tier validation บน invoice |
| `hr_expense_tier_validation` | Tier validation บน expense |
| `base_tier_validation_forward` | Forward/delegate approvals |
| `base_substate` | Base sub-state |
| `sequence_reset_period` | Reset sequence ตามช่วงเวลา |
| `bi_sql_editor` | สร้าง SQL view สำหรับ BI |
| `base_comment_template` | Comment/terms templates |
| `sale_order_note_template` | SO terms template |
| `purchase_default_terms_conditions` | PO default terms |
| `sale_product_set` | Product set บน SO |
| `report_qweb_parameter` | Report parameters |
| `purchase_request` | Purchase request (PR) |

### OCA modules ที่ต้อง clone เพิ่มจาก OCA GitHub

| OCA Module | Repository | ครอบคลุมฟีเจอร์ |
|------------|------------|-------------------|
| `account_asset_disposal` | OCA/account-financial-tools | Asset disposal workflow |
| `l10n_th_withholding_tax_cert_form` | OCA/l10n-thailand | WHT cert PDF form (Thai standard) |
| `account_move_cancel_confirm` | OCA/account-invoicing | Cancel confirm บน invoice |
| `account_invoice_refund_reason` | OCA/account-invoicing | Refund reason |
| `account_payment_partner` | OCA/bank-payment | Payer/Payee บน payment |
| `stock_account_valuation_report` | OCA/stock-logistics-reporting | Stock valuation report |
| `stock_inventory_valuation_report` | OCA/stock-logistics-reporting | Inventory valuation as-of |
| `project_milestone` | OCA/project | Project milestones |
| `project_budget` | OCA/project | Project budget |
| `purchase_landed_cost` | OCA/purchase-workflow | Landed cost (อาจช่วย additional line) |

### ฟีเจอร์ที่ไม่มี OCA module (ต้องพัฒนา custom)

| ฟีเจอร์ | เหตุผล |
|---------|---------|
| BOT URL config | เฉพาะธุรกิจไทย ไม่มี OCA |
| Cash tracking state (expense) | ไม่มี OCA module เฉพาะ |
| logo_iso field | เฉพาะบริษัท ไม่มี OCA |
| Skip date/sequence constraint (skip logic) | ต้อง custom logic |
| Runtime guard tool | เฉพาะ internal tool ไม่มี OCA |
| Abstract service preserve sale_line_ids/purchase_line_id | เฉพาะ business logic ไม่มี OCA |
| No backward stage change (project) | ไม่มี OCA โดยตรง |
| stock.picking.additional.line model | ไม่มี OCA โดยตรง (สามารถใช้ landed cost แทนได้บางส่วน) |

---

## 🎯 ข้อเสนอแนะ

### ลำดับความสำคัญในการนำ OCA module

**ระดับ 1 (ใช้ได้ทันที - อยู่ใน third_party แล้ว):**
1. `l10n_th_account_tax` — ครอบคลุม WHT ทั้งหมด (สำคัญที่สุด)
2. `sale_cancel_reason`, `purchase_order_general_discount`, `purchase_triple_discount`
3. `sale_order_line_date`, `sale_delivery_split_date` — delivery date
4. `sale_tier_validation`, `purchase_tier_validation`, `hr_expense_tier_validation` — approvals
5. `sale_advance_payment`, `purchase_advance_payment`, `purchase_deposit` — downpayment
6. `sale_order_type`, `purchase_order_type`, `purchase_request_type` — document types
7. `base_comment_template`, `sale_order_note_template`, `purchase_default_terms_conditions` — terms templates
8. `bi_sql_editor` — SQL views สำหรับ reports
9. `base_tier_validation_forward` — delegate approvals
10. `sale_validity_auto_cancel` — auto-cancel expired SO

**ระดับ 2 (ต้อง clone จาก OCA GitHub):**
1. `account_asset_disposal` — asset disposal
2. `l10n_th_withholding_tax_cert_form` — WHT PDF forms
3. `account_move_cancel_confirm`, `account_invoice_refund_reason` — cancel/refund reasons
4. `account_payment_partner` — payer/payee
5. `stock_account_valuation_report` — stock valuation

**ระดับ 3 (ต้องพัฒนา custom เท่านั้น):**
1. BOT URL config
2. Cash tracking state
3. Skip date/sequence constraint logic
4. Runtime guard tool
5. Abstract service for line preservation

---

## 💡 ข้อสังเกตสำคัญ

1. **WHT** — `l10n_th_account_tax` ที่มีอยู่แล้วใน third_party ครอบคลุม WHT ได้เกือบทั้งหมด รวมถึง wht.type model, WHT cert, PND1/PND3/PND53 เพียงแค่ต้องเพิ่ม `l10n_th_withholding_tax_cert_form` สำหรับ PDF form มาตรฐานไทย

2. **Approvals** — ใช้ `tier-validation` modules ทั้งหมด ที่มีอยู่แล้วใน third_party ได้เลย สำหรับ dept head auto-approver ใช้ `base_tier_validation_formula` เพื่อกำหนด formula

3. **Discount** — ใช้ `purchase_order_general_discount` และ `purchase_triple_discount` สำหรับ trade discount บน PO และ `sale_order_general_discount` สำหรับ SO

4. **Delivery date** — ใช้ `sale_order_line_date` + `sale_delivery_split_date` ได้เลย

5. **Downpayment** — ใช้ `sale_advance_payment` และ `purchase_advance_payment` / `purchase_deposit`

6. **Analytic** — Odoo 19 มี `analytic_distribution` โดยธรรมชาติบน PO/SO line สามารถดึงจาก project ได้

7. **Reports** — ใช้ `bi_sql_editor` สำหรับ SQL views และ `report_xlsx` สำหรับ XLSX reports
