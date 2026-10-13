# Gap Analysis: Odoo 15 (custom15_autoinfo) → Odoo 19 (od19_*)

**วันที่วิเคราะห์:** 2026-10-13 (อัปเดตใหม่: 2026-10-14)
**วิธีการ:** ตรวจสอบ source code ของทุกโมดูลใน `custom15_autoinfo` แล้วเทียบกับโมดูล `od19_*` ใน Odoo 19 (ตรวจลึกถึงระดับ model file ไม่ใช่แค่ manifest)

**คำอธิบายสัญลักษณ์:**
- ✅ ครบถ้วน (Full Coverage)
- 🟡 บางส่วน (Partial Coverage) — มีโครงสร้างพื้นฐานแต่ยังขาดฟีเจอร์บางอย่าง
- ❌ ยังไม่มี (Missing)

---

## 🔄 อัปเดตการประเมินใหม่ (2026-10-14)

### โมดูลใหม่ที่เพิ่มมาตั้งแต่ครั้งก่อน

| โมดูลใหม่ | คำอธิบาย | ครอบคลุม gap ที่เคยขาด |
|-----------|----------|------------------------|
| `od19_quotation_document_sequence` | Quotation sequence แยกตามแผนก + revision (R01/R02) | ✅ Sequence Quotation แยกตามแผนก |
| `od19_project_document_sequence` | Job No. auto-sequence by dept + project type (J/SV/PM/S) | ✅ Job No. auto-sequence, ✅ dept Many2one |
| `od19_purchase_document_sequence` | PR/PO sequence แยกตามแผนก | ✅ PR/PO sequence แยกตามแผนก |
| `od19_accounting_document_sequence` | Accounting sequences (voucher, billing, WHT, VAT, etc.) | 🟡 บางส่วน |
| `od19_partner_document_sequence` | Partner document sequences | - |
| `od19_partner_thai_fields` | Thai-specific partner fields (tax name, branch code, etc.) | - |
| `od19_accounting_payment_fee` | Payment fee (bank charges) on payments | ✅ Payment fee |
| `od19_service_warranty` | Warranty management and RMA/claims | 🟡 Warranty (แต่เป็น RMA ไม่ใช่ report master) |
| `od19_asset_loan` | Asset/tool loan management + calibration tracking | - |
| `od19_sales_confirm_stamp` | Red CONFIRMED stamp on printed quotations | - |
| `od19_thai_localization_base` | Sarabun font + Buddhist Era flag | - |
| `od19_iso_*` (8 โมดูล) | ISO 9001/14001 management modules | - |
| `od19_accounting_analytic_require` | Analytic account requirement | - |
| `od19_accounting_payment_voucher_reports` | Payment voucher reports | - |
| `od19_helpdesk_extension` | Helpdesk extension | - |
| `od19_product_return` | Product return management | - |
| `od19_service_card` | Service card management | - |
| `od19_user_guide_tours` | User guide tours | - |
| `od19_website` | Website module | - |

### OCA modules ที่มีอยู่แล้วใน third_party (สามารถใช้ได้)

| OCA Module | ครอบคลุม gap ที่เคยขาด |
|------------|------------------------|
| `l10n_th_amount_to_text` | ✅ convert_num_th (แปลงตัวเลขเป็นข้อความไทย) |
| `l10n_th_base_sequence` | 🟡 มี Buddhist Era year แต่ไม่ได้ skip date constraint |
| `auditlog` (server-tools) | ✅ Track deleted records |
| `report_xlsx` (reporting-engine) | ✅ OCA base XLSX report engine |
| `account_asset_management` | 🟡 Base asset management แต่ไม่มี disposal workflow |

### สรุปภาพรวมใหม่ (หลังอัปเดต)

| โดเมน | จำนวนโมดูล OD15 | ครบถ้วน | บางส่วน | ยังไม่มี | เปลี่ยนแปลง |
|--------|-----------------|---------|---------|----------|-------------|
| Sales | 5 | 1 | 2 | 2 | +1 ครบ (sequence) |
| Purchase | 3 | 1 | 1 | 1 | +1 ครบ (sequence) |
| Accounting | 8 | 3 | 2 | 3 | +2 ครบ (fee, convert_num) |
| Project | 5 | 1 | 1 | 3 | +1 ครบ (job no) |
| HR/Expense/Fleet | 4 | 0 | 1 | 3 | ไม่เปลี่ยน |
| Stock/Inventory | 4 | 1 | 2 | 1 | ไม่เปลี่ยน |
| Reports/Misc | 9 | 3 | 2 | 4 | +2 ครบ (auditlog, xlsx) |
| **รวม** | **38** | **10** | **11** | **17** | **+7 ครบ** |

### ฟีเจอร์ที่เคยขาด แต่ตอนนี้มีแล้ว (10 รายการ)

1. ✅ **Sequence Quotation แยกตามแผนก** → `od19_quotation_document_sequence`
2. ✅ **Job No. auto-sequence by dept/job_type** → `od19_project_document_sequence`
3. ✅ **PR/PO sequence แยกตามแผนก** → `od19_purchase_document_sequence`
4. ✅ **Payment fee** → `od19_accounting_payment_fee`
5. ✅ **convert_num_th (แปลงตัวเลขเป็นข้อความไทย)** → OCA `l10n_th_amount_to_text`
6. ✅ **Track deleted records** → OCA `auditlog`
7. ✅ **OCA base XLSX report engine** → OCA `report_xlsx`
8. ✅ **Money In Report** → `od19_accounting_money_in_report`
9. ✅ **Delivery reason flags** → `od19_delivery_label`
10. ✅ **Purchase Procurement Core** → `od19_purchase_procurement_core`

### ฟีเจอร์ที่ยังขาดสำคัญที่สุด (High Priority - ยังไม่มี)

#### Sales
- ❌ 7 master report models (price, delivery, payment product/engineering, validity, warranty, credit)
- ❌ Wizard เปลี่ยนวันที่จัดส่งทั้งเอกสาร
- ❌ Wizard "Get Sale Order Lines" บน invoice
- ❌ Downpayment invoice linking (origin_second/po_origin)

#### Purchase
- ❌ Trade Discount Wizard
- ❌ 5 master report models (warranty, delivery_to, term, shipment, weight)
- ❌ PR line pricing (price_unit, discount, taxes)
- ❌ Analytic จาก project บน PR/PO
- ❌ vendor_ref / your_ref บน PR

#### Accounting
- ❌ Asset Disposal Workflow (cancel draft moves, revert, linked docs, safe cron)
- ❌ WHT PDF Print (4 แบบ: ภงด.1, ภงด.3, ภงด.53, ภงด.53 ทริส)
- ❌ WHT base computed จาก selected invoices + wht.type model
- ❌ Cancel Reason Wizard บน invoice
- ❌ Payer/Payee บน prepayment
- ❌ Create vendor bill from PO wizard
- ❌ BOT URL config
- ❌ Prepayment actual due date (+30 days)

#### Project
- ❌ Project Risk Report (SQL view + risk score)
- ❌ Hierarchical Project Type model
- ❌ Task deadline email notification cron
- ❌ No backward stage change
- ❌ Job Assignment Document fields
- ❌ SO/PO linking จาก project

#### HR/Expense/Fleet
- ❌ Department head as auto approver
- ❌ Cash tracking state (expense) + return/reset wizards
- ❌ XLSX expense reports
- ❌ Delegate approvals
- ❌ WHT for expense payment
- ❌ Insurance/Act expire date + email notification cron
- ❌ Service done notification

#### Stock/Inventory
- ❌ FIFO valuation service + monthly stock report email cron
- ❌ FIFO as-of wizard
- ❌ BF revaluation
- ❌ stock.picking.additional.line model
- ❌ Signature chain auto-resolve (sale user → dept manager)

#### Misc
- ❌ Document Signing (sign)
- ❌ logo_iso field
- ❌ Skip date/sequence constraint (l10n_th_base_sequence มีแค่ BE year)
- ❌ Runtime guard tool
- ❌ Abstract service preserve sale_line_ids/purchase_line_id

---

## สรุปภาพรวม (เวอร์ชันเดิม 2026-10-13)

| โดเมน | จำนวนโมดูล OD15 | ครบถ้วน | บางส่วน | ยังไม่มี |
|--------|-----------------|---------|---------|----------|
| Sales | 5 | 0 | 2 | 3 |
| Purchase | 3 | 0 | 1 | 2 |
| Accounting | 8 | 1 | 3 | 4 |
| Project | 5 | 0 | 1 | 4 |
| HR/Expense/Fleet | 4 | 0 | 1 | 3 |
| Stock/Inventory | 4 | 1 | 2 | 1 |
| Reports/Misc | 9 | 1 | 2 | 6 |
| **รวม** | **38** | **3** | **12** | **23** |

---

## 1. Sales (การขาย)

### 1.1 autoinfo_sale

**Workflow:** การสร้างใบเสนอราคา (Quotation) → ระบุแผนก → ระบบสร้างเลขที่เอกสารตามแผนก → คำนวณ scheduled_date → อนุญาตให้แก้ไข client_order_ref ระหว่างการยืนยัน → ตรวจสอบสินค้าต้องเป็นของแผนกตนเอง → ดึง analytic account จาก project ของลูกค้า

**Workfunctional:**
- Sequence ใบเสนอราคาแยกตามแผนก/ผู้ใช้
- คำนวณ scheduled_date อัตโนมัติ
- Wizard เปลี่ยนวันที่จัดส่ง
- client_order_ref แก้ไขได้ระหว่าง validation
- กฎสินค้าต้องเป็นของแผนกตนเอง
- Analytic account จาก customer project

**Workcondition:** ใช้งานได้เฉพาะเมื่อกำหนดแผนกให้ผู้ใช้แล้ว และต้องมี project ที่ผูกกับลูกค้า

**OD19 Coverage:**
- `od19_sales_contract_core` — มี Master Contract (limit_amount, consumed_amount, over_limit_policy) ✅
- `od19_sales_project_context` — มี sale_mode (one_time/contract), project_id, project_owner_id 🟡
- `od19_sales_customer_risk_gate` — มี blacklist + credit gate ✅
- `od19_document_sequence` — มีรองรับ sequence แต่ต้องตรวจสอบว่ารองรับแยกตามแผนกหรือไม่ 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Sequence Quotation แยกตามแผนก | 🟡 | ตรวจสอบ od19_document_sequence ว่ารองรับแยกตาม hr.department หรือไม่ ถ้าไม่ ต้องเพิ่ม logic ในการ override `_create_sequence` หรือใช้ `sequence.mixin` กับ domain ตามแผนก |
| scheduled_date compute อัตโนมัติ | ❌ | เพิ่ม compute field ที่คำนวณจาก commitment_date หรือจากรายการสินค้าที่มี delivery_lead_time |
| Wizard เปลี่ยนวันที่จัดส่งทั้งเอกสาร | ❌ | สร้าง wizard `od19.sale.change.delivery.date` ที่อัปเดต `scheduled_date` ของทุก sale.order.line |
| client_order_ref แก้ไขได้ระหว่าง validation | ❌ | Override `action_confirm` หรือใส่ readonly condition ที่ขึ้นกับ state โดยอนุญาตให้แก้ไขได้จนกว่าจะ confirm |
| กฎสินค้าต้องเป็นของแผนกตนเอง | ❌ | เพิ่ม constrains ที่ตรวจสอบ product.department_id กับ user's department ในการ create/write sale.order.line |
| Analytic จาก customer project | 🟡 | `od19_sales_project_context` มี project_id แล้ว แต่ต้องเพิ่ม onchange ให้ดึง analytic account จาก project มาใส่ sale.order.line อัตโนมัติ |

---

### 1.2 autoinfo_sale_form

**Workflow:** การพิมพ์ใบเสนอราคา → ระบบดึงข้อมูลจาก 7 master report models (ราคาการขาย, เงื่อนไขการจัดส่ง, เงื่อนไขการชำระเงินสินค้า/วิศวกรรม, ระยะเวลาความถูกต้องของใบเสนอราคา, การรับประกัน, เครดิต) → รวมเข้ากับข้อมูลใบเสนอราคา → พิมพ์ผ่าน Jasper

**Workfunctional:**
- 7 master report models สำหรับเก็บเงื่อนไขมาตรฐาน
- Jasper quotation form
- แบ่งเงื่อนไขการชำระเงินระหว่างสินค้าและวิศวกรรม

**Workcondition:** ต้องกำหนดเงื่อนไขมาตรฐานใน master models ก่อน การพิมพ์จะดึงข้อมูลตาม partner หรือตามค่า default

**OD19 Coverage:**
- `od19_reporting_jasper` — มี foundation สำหรับ Jasper report 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| 7 master report models (price, delivery, payment product/engineering, validity, warranty, credit) | ❌ | สร้าง model ใหม่ `od19.sale.term.template` ที่รวมเงื่อนไขทั้งหมดใน model เดียว (หรือแยกตามประเภท) พร้อม Many2one จาก sale.order ให้เลือก template แล้ว auto-fill เงื่อนไข |
| Jasper quotation form | 🟡 | ใช้ `od19_reporting_jasper` เป็น base แล้วสร้าง template ใหม่ สำหรับใบเสนอราคา (แยกจาก Odoo standard report) |
| แยกเงื่อนไขชำระเงิน สินค้า vs วิศวกรรม | ❌ | เพิ่ม field `payment_term_product_id` และ `payment_term_engineering_id` บน sale.order หรือใช้ ฺฺbpayment_term_id ธรรมดาแต่แยกใน report template |

---

### 1.3 account_invoice_get_sale

**Workflow:** บนหน้า Customer Invoice → กดปุ่ม "Get Sale Order Lines" → เปิด wizard ให้เลือก SO → ระบบดึง sale.order.line มาใส่เป็น invoice.line อัตโนมัติ

**Workfunctional:** Wizard สร้าง invoice.line จาก sale.order.line

**Workcondition:** ใช้ได้กับ invoice ที่ยังอยู่สถานะ draft และต้องมี SO ที่ผูกกับ partner เดียวกัน

**OD19 Coverage:** ❌ ไม่มีโมดูลใดครอบคลุม

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Wizard "Get Sale Order Lines" บน invoice | ❌ | สร้าง wizard `od19.account.invoice.get.sale.lines` ที่ให้เลือก sale.order แล้วสร้าง account.move.line จาก sale.order.line โดยคงไว้ซึ่ง sale_line_ids เพื่อให้สามารถติดต่อ追踪ได้ |

---

### 1.4 sale_purchase_downpayment_invoice

**Workflow:** สร้าง downpayment invoice จาก SO/PO → ระบบเก็บข้อมูลอ้างอิงผ่าน `origin_second` (สำหรับ SO) และ `po_origin` (สำหรับ PO) → เพื่อให้สามารถ trace ย้อนกลับได้ว่า invoice นี้มาจาก SO/PO ใด

**Workfunctional:**
- field `origin_second` บน invoice (อ้างอิง SO)
- field `po_origin` บน invoice (อ้างอิง PO)

**Workcondition:** ใช้ได้เมื่อสร้าง downpayment invoice จาก SO/PO

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| origin_second / po_origin บน invoice | ❌ | Odoo 19 มี `invoice_origin` field ธรรมดาแล้ว แต่ถ้าต้องการ trace แยกชัดเจน สามารถเพิ่ม field `od19_downpayment_origin` (Char) ที่เก็บ SO/PO name หรือใช้ `od19_source_document` Many2one ที่รองรับทั้ง SO และ PO |

---

### 1.5 autoinfo_repeat_customer_dashboard

**Workflow:** ระบบคำนวณ Repeat Customer จากประวัติการซื้อ → แสดงผลใน dashboard รูปแบบ KPI → กรองได้ตามช่วงเวลา 30/90 วัน → แยกดูทั้งระดับ Contractor และ Project Owner

**Workfunctional:**
- SQL view `autoinfo.repeat.customer.event.report`
- actual_partner_id mapping (แมป partner จริงจาก SO)
- ตัวกรอง 30/90 วัน
- KPI dashboard

**Workcondition:** ต้องมีประวัติ SO ที่ผูกกับ project และมีการซื้อซ้ำเกิดขึ้น

**OD19 Coverage:**
- `od19_sales_reporting` — มี `od19.sales.repeat.business.report` SQL view ที่แสดง commercial_customer, project_owner, project_count, sale_order_count 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| actual_partner_id mapping | ❌ | เพิ่ม logic ใน SQL view ให้แมป partner ที่แท้จริง (กรณี SO มี partner_shipping_id ต่างจาก partner_id) |
| ตัวกรอง 30/90 วัน | ❌ | เพิ่ม field `last_order_date` ใน SQL view แล้วสร้าง filter ที่คำนวณจากวันที่ปัจจุบันลบ 30/90 วัน |
| KPI Dashboard | 🟡 | `od19_sales_reporting` มี report แล้ว แต่ต้องเพิ่ม dashboard view (graph/pivot) และ KPI card ที่แสดงจำนวน repeat customer ย้อนหลัง 30/90 วัน |

---

## 2. Purchase (การจัดซื้อ)

### 2.1 autoinfo_purchase

**Workflow:** สร้าง Purchase Request (PR) → ระบุแผนก → ระบบสร้างเลขที่ PR ตามแผนก → ระบุ vendor/your_ref → เพิ่มรายการสินค้าพร้อมราคา/ส่วนลด/ภาษี → ใช้ Trade Discount Wizard เพื่อคำนวณส่วนลดรวม → ดึง analytic จาก project → แปลงเป็น PO

**Workfunctional:**
- PR/PO sequence แยกตามแผนก
- vendor_ref / your_ref บน PR
- Trade Discount Wizard
- PR line มี price_unit, discount, taxes
- Analytic จาก project

**Workcondition:** ต้องกำหนดแผนก และต้องมี project ที่จะผูก analytic

**OD19 Coverage:**
- `od19_purchase_procurement_core` — มี entry_mode (requisition/direct), approval_state, budget_warning, material edit protection ✅
- `od19_purchase_request_extend` — มี request_reason, priority, requested_department, budget_year, notifications ✅
- `od19_purchase_document_sequence` — มีรองรับ sequence สำหรับ PR/PO 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| PR/PO sequence แยกตามแผนก | 🟡 | ตรวจสอบ od19_purchase_document_sequence ถ้ายังไม่รองรับแผนก ให้เพิ่ม logic override `_create_sequence` โดยใช้ `department_id.code` เป็น prefix |
| vendor_ref บน PR | ❌ | เพิ่ม field `od19_vendor_ref` (Char) บน purchase.request และ propagate ไปที่ PO |
| your_ref บน PR | ❌ | เพิ่ม field `od19_your_ref` (Char) บน purchase.request |
| Trade Discount Wizard | ❌ | สร้าง wizard `od19.purchase.trade.discount` ที่คำนวณส่วนลดรวมจาก multiple discount levels แล้วอัปเดตทุก purchase.request.line |
| PR line มี price_unit, discount, taxes | ❌ | เพิ่ม field `price_unit`, `discount`, `taxes_id` บน purchase.request.line (ถ้ายังไม่มี) และ propagate ไปที่ PO line |
| Analytic จาก project บน PR/PO | ❌ | เพิ่ม field `od19_project_id` บน purchase.request และ onchange ให้ดึง analytic account จาก project มาใส่ PR line อัตโนมัติ |

---

### 2.2 autoinfo_purchase_form

**Workflow:** การพิมพ์ PO/PR → ระบบดึงข้อมูลจาก 5 master report models (warranty, delivery_to, term, shipment, weight) → auto-fill list price จาก vendor → พิมพ์ผ่าน Jasper (FM-PU-01/02/03/04)

**Workfunctional:**
- 5 master report models (warranty, delivery_to, term, shipment, weight)
- List price auto-fill จาก vendor
- Jasper PO/PR templates (FM-PU-01/02/03/04)

**Workcondition:** ต้องกำหนดเงื่อนไขมาตรฐานใน master models และต้องมี list price ใน vendor

**OD19 Coverage:**
- `od19_reporting_jasper` — foundation 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| 5 master report models | ❌ | สร้าง model รวม `od19.purchase.term.template` ที่เก็บ warranty, delivery_to, payment_term, shipment_term, weight_terms แล้วให้ PO เลือก template เพื่อ auto-fill |
| List price auto-fill จาก vendor | ❌ | เพิ่ม onchange `partner_id` บน purchase.order ที่ดึง list price จาก vendor's product_supplier_info มาใส่ PO line |
| Jasper PO/PR templates | 🟡 | ใช้ `od19_reporting_jasper` สร้าง template ใหม่ สำหรับ PO (FM-PU-01) และ PR (FM-PU-02) |

---

### 2.3 od15_autoinfo_account_cash_with_purchase

**Workflow:** เมื่อจ่ายเงินสดสำหรับ Vendor Bill → ระบบนับจำนวนเงินสดที่จ่ายแล้วเข้าไปใน `qty_invoiced` ของ PO เพื่อให้ PO แสดงสถานะถูกต้อง

**Workfunctional:** นับ cash payment เข้า qty_invoiced ของ PO

**Workcondition:** ใช้ได้กับ vendor bill ที่มีการจ่ายเงินสด

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| นับ cash payment เข้า qty_invoiced ของ PO | ❌ | Override `_compute_qty_invoiced` บน purchase.order.line ให้รวม cash payment ที่จ่ายแล้ว หรือสร้าง logic ใน account.payment ที่อัปเดต qty_invoiced เมื่อจ่ายเงินสด |

---

## 3. Accounting (การบัญชี)

### 3.1 autoinfo_account

**Workflow:** 
- Cancel invoice → เปิด wizard ให้ระบุเหตุผลการยกเลิก → บันทึกเหตุผล
- ตั้งค่า BOT URL สำหรับตรวจสอบใบกำกับภาษีออนไลน์
- พิมพ์ WHT PDF (4 แบบ: ภงด.1, ภงด.3, ภงด.53, ภงด.53 ทริส)
- Prepayment: คำนวณ due date จริง = วันที่ + 30 วัน
- Payment Register: รองรับ WHT และ fee

**Workfunctional:**
- Cancel reason wizard
- BOT URL config
- WHT PDF print (4 variants)
- Prepayment actual due date (+30 days)
- Payment register WHT/fee

**Workcondition:** 
- Cancel reason: ใช้ได้เมื่อกดยกเลิก invoice
- BOT URL: ต้องตั้งค่าใน settings
- WHT PDF: ต้องมี WHT บน payment
- Prepayment: ใช้ได้กับ prepayment invoice

**OD19 Coverage:**
- `od19_accounting_wht` — มี wht.type และ WHT บน payment 🟡
- `od19_accounting_advance` — มี advance payment (แต่เป็น model แยก ไม่ใช่ standard prepayment) 🟡
- `od19_accounting_dncn` — มี DN/CN พร้อม reason 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Cancel reason wizard บน account.move | ❌ | สร้าง wizard `od19.account.move.cancel.reason` ที่ให้ระบุเหตุผลก่อนยกเลิก แล้วเก็บใน field `od19_cancel_reason` บน account.move |
| BOT URL config | ❌ | เพิ่ม field `od19_bot_url` ใน res.config.settings และสร้าง link ใน invoice form ที่เปิด BOT website พร้อมเลขที่ใบกำกับ |
| WHT PDF print (4 variants) | ❌ | สร้าง report template สำหรับภงด.1, ภงด.3, ภงด.53, ภงด.53 ทริส โดยใช้ข้อมูลจาก od19_accounting_wht |
| Prepayment actual due date (+30 days) | 🟡 | `od19_accounting_advance` ใช้ model แยก ถ้าต้องการใช้ standard prepayment ให้เพิ่ม compute field `od19_actual_due_date` ที่คำนวณ = invoice_date + 30 days |
| Payment register fee | ❌ | เพิ่ม field `od19_fee_amount` บน account.payment และสร้าง journal entry สำหรับ fee ตอน post payment |
| Payment register WHT | 🟡 | `od19_accounting_wht` มี WHT บน payment แล้ว แต่เป็น manual wht_base_amount (ดู 3.3) |

---

### 3.2 autoinfo_accounting_form

**Workflow:** การพิมพ์เอกสารบัญชี (invoice, receipt, tax receipt, billing, DN, CN, prepayment) → ใช้ Jasper template → ฟังก์ชัน `convert_num_th` แปลงตัวเลขเป็นข้อความภาษาไทย

**Workfunctional:**
- Jasper forms สำหรับเอกสารบัญชี 7 ชนิด
- SQL function `convert_num_th` (แปลงตัวเลขเป็นข้อความไทย)

**Workcondition:** ต้องติดตั้ง Jasper report engine และต้องมี function `convert_num_th` ในฐานข้อมูล

**OD19 Coverage:**
- `od19_reporting_jasper` — foundation 🟡
- `od19_thai_font_support` — มีฟอนต์ Sarabun ✅

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Jasper forms สำหรับ invoice/receipt/tax receipt/billing/DN/CN/prepayment | 🟡 | ใช้ `od19_reporting_jasper` สร้าง template แต่ละชนิด หรือใช้ Odoo standard report + QWeb ที่มีฟอนต์ไทยจาก od19_thai_font_support |
| SQL function convert_num_th | ❌ | สร้าง SQL function `od19_convert_num_th` ในฐานข้อมูล หรือใช้ Python method ใน model ที่แปลงตัวเลขเป็นข้อความไทย (แนะนำ Python method เพราะง่ายต่อการ maintain) |

---

### 3.3 autoinfo_payment_wht

**Workflow:** สร้าง Payment → เลือก invoices ที่จะชำระ → ระบบคำนวณ WHT base จากยอดรวมของ invoices ที่เลือก → เลือก wht.type → ระบบคำนวณ WHT amount

**Workfunctional:**
- WHT base computed จาก selected invoices
- `wht.type` model
- `invoice_line_ids` table บน payment

**Workcondition:** ต้องเลือก invoices ก่อนคำนวณ WHT

**OD19 Coverage:**
- `od19_accounting_wht` — มี wht.type model และ WHT fields บน payment แต่ wht_base_amount เป็น manual 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| WHT base computed จาก selected invoices | ❌ | เพิ่ม compute `wht_base_amount` ที่คำนวณจาก `reconciled_invoice_ids` หรือ `invoice_line_ids` ของ payment โดยรวม amount_untaxed ของ invoices ที่เลือก |
| invoice_line_ids table บน payment | ❌ | เพิ่ม One2many `od19_payment_invoice_line_ids` ที่เชื่อมกับ invoices ที่เลือกสำหรับคำนวณ WHT |

---

### 3.4 autoinfo_asset_sale_fix

**Workflow:** 
- กำจัดสินทรัพย์ → ระบบยกเลิก depreciation moves ที่ยังเป็น draft ก่อน → ทำการจำหน่าย
- Revert การจำหน่าย → กลับไปสถานะเดิม
- ผูกเอกสารที่เกี่ยวข้อง (additional_bills, supporting_moves)
- Safe depreciation cron (รันอย่างปลอดภัย ไม่กระทบ transaction อื่น)

**Workfunctional:**
- Disposal workflow (cancel draft depreciation moves first)
- Disposal revert
- Linked documents (additional_bills, supporting_moves)
- Safe depreciation cron

**Workcondition:** 
- Disposal: ใช้ได้กับสินทรัพย์ที่อยู่สถานะ open
- Revert: ใช้ได้กับสินทรัพย์ที่จำหน่ายแล้วและยังไม่มี transaction ถัดไป

**OD19 Coverage:**
- `od19_accounting_fixed_assets` — มี asset module แบบ custom (draft/open/close, depreciation schedule) แต่ไม่มี disposal workflow 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Asset disposal workflow (cancel draft moves first) | ❌ | เพิ่ม state `disposed` และ action `action_dispose` ที่: (1) ค้นหา depreciation moves ที่ยัง draft → button_cancel, (2) สร้าง journal entry สำหรับจำหน่าย, (3) เปลี่ยน state เป็น disposed |
| Disposal revert | ❌ | เพิ่ม action `action_revert_disposal` ที่ย้อนกลับ journal entry และคืนสถานะเป็น open |
| Linked documents (additional_bills, supporting_moves) | ❌ | เพิ่ม Many2many `od19_additional_bill_ids` และ `od19_supporting_move_ids` บน account.asset |
| Safe depreciation cron | ❌ | สร้าง cron ที่รัน depreciation ด้วย isolated transaction (ใช้ `with_context` หรือ `env.cr.savepoint`) และจัดการ error อย่างปลอดภัย |

---

### 3.5 od15_autoinfo_account_prepayment

**Workflow:** 
- สร้าง Prepayment → ระบุ Payer (ผู้จ่าย) และ Payee (ผู้รับเงิน) จากรายชื่อ partner ทั้งหมด
- จาก PO → กด "Create Vendor Bill" → ระบบสร้าง vendor bill จาก PO

**Workfunctional:**
- Payer/Payee fields บน prepayment (เลือกจาก partner ทั้งหมด ไม่กรอง)
- Create vendor bill from PO wizard

**Workcondition:** 
- Payer/Payee: ใช้ได้กับทุก prepayment
- Create bill from PO: ใช้ได้กับ PO ที่ confirmed แล้ว

**OD19 Coverage:**
- `od19_accounting_advance` — มี advance payment แต่ไม่มี Payer/Payee 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Payer/Payee fields บน prepayment | ❌ | เพิ่ม field `od19_payer_id` และ `od19_payee_id` (Many2one res.partner) บน account.advance โดยไม่ใส่ domain (ให้เลือกได้ทุก partner) |
| Create vendor bill from PO wizard | ❌ | สร้าง wizard `od19.purchase.create.vendor.bill` ที่สร้าง account.move (vendor bill) จาก purchase.order โดยดึง PO line มาเป็น invoice line |

---

### 3.6 autoinfo_account_move_link_payment_number

**Workflow:** เมื่อมีการจ่ายเงินสำหรับ vendor bill → ระบบคำนวณและแสดง `payment_number` บน vendor bill เพื่อให้เห็นเลขที่การชำระเงิน

**Workfunctional:** `payment_number` computed field บน vendor bill

**Workcondition:** ใช้ได้กับ vendor bill ที่มีการจ่ายเงินแล้ว

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| payment_number computed field บน vendor bill | ❌ | เพิ่ม compute field `od19_payment_number` บน account.move ที่ดึง name ของ account.payment ที่ผูกกับ invoice ผ่าน reconciliation |

---

### 3.7 autoinfo_fixes_accounting_runtime_guard

**Workflow:** Admin เข้าใช้งาน tool → ตรวจสอบ runtime environment (Python version, Odoo version, installed modules, database size) → แสดงผลรายงาน

**Workfunctional:** Runtime environment check tool (admin only, cron disabled)

**Workcondition:** ใช้ได้เฉพาะ admin และไม่รันอัตโนมัติ

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Runtime guard tool | ❌ | สร้าง model `od19.runtime.guard` ที่เก็บผลการตรวจสอบ และ wizard ที่รวบรวมข้อมูล runtime (Python, Odoo, modules, DB size) แล้วแสดงผล จำกัดสิทธิ์แค่ admin |

---

### 3.8 autoinfo_accounting_form_wht_fix

**Workflow:** แก้ไข bug ที่ tax receipt form crash เมื่อมี WHT module ติดตั้ง

**Workfunctional:** Fix compatibility ระหว่าง tax receipt form กับ WHT module

**Workcondition:** เกิดขึ้นเมื่อทั้งสองโมดูลทำงานร่วมกัน

**OD19 Coverage:** ❌ ไม่มี (แต่ OD19 อาจไม่มีปัญหาเดียวกันเพราะโครงสร้างต่างกัน)

**Gaps:** ไม่จำเป็นต้องนำไปใช้ใน OD19 ถ้าไม่มีปัญหาเดียวกัน

---

## 4. Project (โครงการ)

### 4.1 autoinfo_project

**Workflow:** สร้าง Project → ระบบสร้าง Job No. อัตโนมัติตามแผนก/ประเภทงาน → ระบุแผนก (required) → ผูก SO/PO → เมื่อ task มี deadline ใกล้ถึง → cron ส่ง email แจ้งเตือน → ห้ามเปลี่ยน stage ย้อนหลัง

**Workfunctional:**
- Job No. auto-sequence by dept/job_type
- project_department_id required
- SO/PO linking
- Task deadline email notification cron
- No backward stage change

**Workcondition:** 
- Job No.: ต้องมี sequence ที่กำหนดตามแผนก
- Email notification: ต้องตั้งค่า outgoing mail server
- No backward stage: ใช้ได้กับ task ทุก task

**OD19 Coverage:**
- `od19_project_analytic` — มี job_no (Char, ไม่ auto-sequence), job_type (selection), department (Char), project_owner_id, contractor_ids, auto analytic account 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Job No. auto-sequence by dept/job_type | ❌ | เปลี่ยน job_no เป็น computed field ที่สร้างจาก `ir.sequence` โดยใช้ prefix = department.code + job_type หรือ override `create` เพื่อสร้าง job_no อัตโนมัติ |
| project_department_id เป็น Many2one (required) | 🟡 | เปลี่ยน `department` จาก Char เป็น `od19_department_id` (Many2one hr.department, required=True) |
| SO/PO linking จาก project | ❌ | เพิ่ม One2many `od19_sale_order_ids` และ `od19_purchase_order_ids` บน project.project โดยอ้างอิงผ่าน sale.order.od19_project_id และ purchase.order.od19_project_id |
| Task deadline email notification cron | ❌ | สร้าง cron `od19_project_task_deadline_notification` ที่ค้นหา task ที่ deadline ใกล้ถึง (เช่น ภายใน 3 วัน) แล้วส่ง email ถึง responsible user |
| No backward stage change | ❌ | เพิ่ม constrains ใน project.task ที่ตรวจสอบ sequence ของ stage ห้ามให้ sequence ปัจจุบัน < sequence เดิม |

---

### 4.2 autoinfo_project_form

**Workflow:** การพิมพ์ Job Assignment Document → ระบบดึงข้อมูลผู้รับผิดชอบ, ผู้ประสานงาน, ขอบเขตงาน, เอกสารที่ต้องการ → พิมพ์ผ่าน Jasper

**Workfunctional:**
- Job assignment document fields (responsible persons, coordinators, scope_of_work, document requirements)
- Jasper report

**Workcondition:** ต้องกรอกข้อมูลใน project form ก่อนพิมพ์

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Job assignment document fields | ❌ | เพิ่ม fields บน project.project: `od19_responsible_person_ids` (Many2many hr.employee), `od19_coordinator_ids` (Many2many hr.employee), `od19_scope_of_work` (Text), `od19_document_requirements` (Text) |
| Jasper job assignment report | ❌ | สร้าง report template สำหรับ Job Assignment Document โดยใช้ `od19_reporting_jasper` หรือ QWeb report |

---

### 4.3 autoinfo_project_risk_report

**Workflow:** ระบบคำนวณค่าความเสี่ยงของแต่ละโครงการจาก SQL view → พิจารณาตัวแปร: สัญญา, ยอดที่วิเคราะห์แล้ว, ต้นทุนจริง, ต้นทุนคอมมิต, AR ค้างชำระ → คำนวณ risk score (margin<15% +40, overdue +30, due<today +30) → แสดงรายงาน

**Workfunctional:**
- SQL view `autoinfo_project_risk_report`
- Risk score calculation (margin<15 +40, overdue +30, due<today +30)

**Workcondition:** ต้องมีข้อมูล SO, invoice, expense ที่ผูกกับ project

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Project Risk Report (SQL view + risk score) | ❌ | สร้าง SQL view `od19_project_risk_report` ที่คำนวณ contract_amount, invoiced_amount, actual_cost, committed_cost, overdue_ar, risk_score โดยใช้สูตรเดียวกัน (margin<15 +40, overdue +30, due<today +30) แล้วสร้าง report view ใน Odoo |

---

### 4.4 autoinfo_data_link_project

**Workflow:** เมื่อสร้าง invoice จาก SO → ระบบดึง project มาจาก SO ไปใส่ invoice อัตโนมัติ เพื่อให้สามารถวิเคราะห์รายได้ตามโครงการได้

**Workfunctional:** Link invoice to customer project from sale order

**Workcondition:** ใช้ได้เมื่อ SO มี project_id กำหนดไว้

**OD19 Coverage:**
- `od19_sales_project_context` — มี od19_project_id บน sale.order 🟡
- `od19_project_analytic` — มี analytic account auto-create 🟡

**Gaps:**
| ฟีเคอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Link invoice to customer project from SO | 🟡 | เพิ่ม onchange/override ใน `_prepare_invoice` ของ sale.order ให้ส่ง `od19_project_id` ไปที่ account.move ตอนสร้าง invoice |

---

### 4.5 project_type

**Workflow:** สร้าง Project Type แบบลำดับชั้น (parent/child) → กำหนดว่า type ไหนใช้สำหรับ project หรือ task → ระบบสร้าง complete_name แบบ `Parent / Child`

**Workfunctional:**
- Hierarchical project type (parent_id, child_ids)
- project_ok / task_ok flags
- complete_name

**Workcondition:** ใช้ได้ทั้ง project และ task

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Hierarchical project type model | ❌ | สร้าง model `od19.project.type` ที่มี parent_id, child_ids, project_ok, task_ok, complete_name (computed จาก parent chain) แล้วเพิ่ม field `od19_project_type_id` บน project.project และ project.task |

---

## 5. HR/Expense/Fleet (ทรัพยากรบุคคล/ค่าใช้จ่าย/ยานพาหนะ)

### 5.1 autoinfo_employees

**Workflow:** เพิ่ม field `dtr_department_short` บน hr.department สำหรับเก็บรหัสย่อของแผนก ใช้ในรายงาน

**Workfunctional:** `dtr_department_short` field บน hr.department

**Workcondition:** ใช้ได้กับทุกแผนก

**OD19 Coverage:** ❌ ไม่มี (แต่ od19_delivery_label ใช้ department.code แล้ว)

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| dtr_department_short field | ❌ | Odoo มี `code` field บน hr.department อยู่แล้ว แนะนำให้ใช้ `code` แทน ถ้าต้องการ field แยก สามารถเพิ่ม `od19_department_short` ได้ แต่ควรพิจารณาใช้ code standard |

---

### 5.2 autoinfo_hr_expense

**Workflow:** เมื่อทำการชำระเงินค่าใช้จ่าย (expense) → ระบบรองรับการหัก WHT ในการจ่าย

**Workfunctional:** WHT in payment register for expenses

**Workcondition:** ใช้ได้กับ expense payment

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| WHT in payment register for expenses | ❌ | ขยาย `od19_accounting_wht` ให้รองรับ expense payment ด้วย โดยเพิ่ม WHT fields ใน payment ที่มาจาก hr.expense |

---

### 5.3 autoinfo_hr_expense_cash_tracking

**Workflow:** 
- สร้าง Expense → เลือก expense category → ระบบกำหนด approver เป็นหัวหน้าแผนกอัตโนมัติ (override tier validation)
- ติดตามสถานะ cash (รับเงินแล้ว/ใช้แล้ว/คืนเงิน)
- มี wizard สำหรับคืนเงินและ reset
- สร้างรายงาน XLSX
- สามารถมอบหมายการอนุมัติ (delegate)

**Workfunctional:**
- Expense category model
- Department head as approver (auto)
- Cash tracking state
- Return/reset wizards
- XLSX reports
- Delegate approvals

**Workcondition:** 
- Approver: ต้องมีหัวหน้าแผนกตั้งไว้
- Cash tracking: ใช้ได้กับ expense ที่จ่ายด้วยเงินสด

**OD19 Coverage:**
- `od19_hr_expense_thai` — มี payment_method, first/second approver (manual), thai_expense_type (selection), two-level approval 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Expense category model | 🟡 | `od19_hr_expense_thai` มี thai_expense_type เป็น selection แต่ถ้าต้องการ flexibility เพิ่ม สร้าง model `od19.expense.category` แล้วเปลี่ยนเป็น Many2one |
| Department head as approver (auto) | ❌ | เพิ่ม onchange/create ที่กำหนด `first_approver_id` = employee's department.manager_id อัตโนมัติ |
| Cash tracking state | ❌ | เพิ่ม field `od19_cash_state` (selection: not_received/received/used/returned) บน hr.expense และ wizard สำหรับเปลี่ยน state |
| Return/reset wizards | ❌ | สร้าง wizard `od19.expense.return.cash` และ `od19.expense.reset` |
| XLSX reports | ❌ | สร้าง report XLSX สำหรับ expense โดยใช้ openpyxl (แบบเดียวกับ money_in_report) |
| Delegate approvals | ❌ | เพิ่ม field `od19_delegate_approver_id` บน hr.expense และ action ที่โอนสิทธิ์การอนุมัติ |

---

### 5.4 autoinfo_fleet

**Workflow:** 
- บันทึกวันที่หมดอายุประกันและภาษี (Act) ของยานพาหนะ
- Cron ตรวจสอบวันที่หมดอายุใกล้ถึง → ส่ง email แจ้งเตือน
- เมื่อมีการเข้ากระบวนการ service แล้วเสร็จ → ส่งการแจ้งเตือน

**Workfunctional:**
- Insurance/Act expire date fields
- Email notification cron for expiry
- Service done notification

**Workcondition:** 
- Expiry notification: ต้องตั้งค่า email และต้องมีวันที่หมดอายุกำหนดไว้
- Service notification: ใช้ได้เมื่อ service log ถูกทำเครื่องหมาย done

**OD19 Coverage:**
- `od19_fleet_accounting` — มี department_id, analytic_account_id, expense_category_id, total_expense 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Insurance expire date | ❌ | เพิ่ม field `od19_insurance_expire_date` (Date) บน fleet.vehicle |
| Act expire date | ❌ | เพิ่ม field `od19_act_expire_date` (Date) บน fleet.vehicle |
| Email notification cron for expiry | ❌ | สร้าง cron `od19_fleet_expiry_notification` ที่ค้นหายานพาหนะที่ประกัน/Act หมดอายุภายใน X วัน แล้วส่ง email ถึงผู้รับผิดชอบ |
| Service done notification | ❌ | เพิ่ม action/override ใน `fleet.vehicle.log.services` ที่ส่ง notification เมื่อ state เปลี่ยนเป็น done (ใช้ od19_notification_multi_channel) |

---

## 6. Stock/Inventory (สต็อก/สินค้าคงคลัง)

### 6.1 autoinfo_stock_monthly_report

**Workflow:** 
- ระบบคำนวณมูลค่าสินค้าคงคลังแบบ FIFO ผ่าน FIFO valuation service
- Cron รายเดือนสร้างรายงานสินค้าคงคลังแล้วส่ง email
- FIFO as-of wizard: คำนวณมูลค่าสินค้าคงคลัง ณ วันที่กำหนด
- BF revaluation: ปรับมูลค่าสินค้าเปิดยกมา

**Workfunctional:**
- FIFO valuation service
- Monthly stock report cron with email
- FIFO as-of wizard
- BF revaluation

**Workcondition:** 
- FIFO: ต้องใช้การ valuation แบบ FIFO
- Monthly report: ต้องตั้งค่า cron และ email
- BF revaluation: ใช้ได้กับสินค้าที่มียอดยกมา

**OD19 Coverage:**
- `od19_inventory_reporting` — มี inventory movement backlog และ accuracy 🟡
- `od19_stock_valuation_adjustment` — มี stock valuation adjustment 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| FIFO valuation service | ❌ | ถ้า Odoo 19 ใช้ inventory valuation แบบ manual/fifo อยู่แล้ว อาจไม่จำเป็น แต่ถ้าต้องการรายงาน FIFO ที่ละเอียด สร้าง service ที่คำนวณจาก stock.move โดยเรียงตามวันที่ |
| Monthly stock report cron with email | ❌ | สร้าง cron `od19_monthly_stock_report` ที่คำนวณยอดสินค้าคงคลังสิ้นเดือนแล้วส่งรายงานทาง email (ใช้ od19_notification_multi_channel) |
| FIFO as-of wizard | ❌ | สร้าง wizard `od19.stock.fifo.asof` ที่ให้ระบุวันที่แล้วคำนวณมูลค่าสินค้าคงคลัง ณ วันที่นั้น |
| BF revaluation | 🟡 | `od19_stock_valuation_adjustment` อาจครอบคลุมบางส่วน แต่ต้องตรวจสอบว่ารองรับ BF revaluation หรือไม่ ถ้าไม่ เพิ่ม wizard สำหรับปรับมูลค่าเปิดยกมา |

---

### 6.2 autoinfo_stock_report

**Workflow:** รายงานสต็อกที่ขยายความสามารถให้กรองตามแผนกได้

**Workfunctional:** Extended stock reports with department filter

**Workcondition:** ใช้ได้กับรายงานสต็อกทั้งหมด

**OD19 Coverage:**
- `od19_inventory_reporting` — มีรายงาน movement backlog และ accuracy 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Extended stock reports with department filter | 🟡 | เพิ่ม `od19_department_code` ในรายงานสต็อกที่มีอยู่ และเพิ่ม filter ตามแผนก |

---

### 6.3 autoinfo_stock_picking_additional_print_lines

**Workflow:** เมื่อพิมพ์ใบส่งมอบ → สามารถเพิ่มบรรทัดพิเศษ (additional lines) สำหรับพิมพ์เพิ่มเติมได้ เช่น หมายเหตุพิเศษ, รายการที่ไม่อยู่ในระบบ

**Workfunctional:** `stock.picking.additional.line` model

**Workcondition:** ใช้ได้กับ picking ทุกรายการ

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| stock.picking.additional.line model | ❌ | สร้าง model `od19.stock.picking.additional.line` ที่มี picking_id (Many2one), name (Char), quantity, product_uom แล้วเพิ่ม One2many บน stock.picking และแสดงใน delivery label report |

---

### 6.4 autoinfo_stock_picking_sale_person_tier

**Workflow:** 
- กรอกเหตุผลการส่ง (claim/return/damaged/warranty/delivery/document)
- ระบบ auto-resolve signature chain จาก sale user → dept manager
- contact name/phone auto-fill จาก SO
- backorder สืบทอด contact จาก SO เดิม

**Workfunctional:**
- Delivery reason flags
- Signature chain auto-resolve (sale user → dept manager)
- Contact name/phone defaults from sale
- Backorder contact inheritance

**Workcondition:** 
- Signature chain: ต้องมี sale user และ dept manager
- Contact auto-fill: ต้องมี SO ผูกกับ picking

**OD19 Coverage:**
- `od19_delivery_label` — มี delivery reason flags ✅, department code ✅, project from sale ✅, contact auto-fill ✅, backorder contact (partially) 🟡

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Delivery reason flags | ✅ | ครบถ้วนแล้ว |
| Signature chain auto-resolve | ❌ | เพิ่ม fields `od19_sale_user_id` และ `od19_dept_manager_id` บน stock.picking และ onchange จาก sale_id ให้ auto-fill sale user แล้วดึง dept manager จาก sale user's department |
| Contact name/phone defaults | ✅ | ครบถ้วนแล้ว |
| Backorder contact inheritance | 🟡 | ตรวจสอบว่า backorder สืบทอด contact จาก SO เดิมหรือไม่ ถ้าไม่ เพิ่ม logic ใน `_apply_delivery_contact_defaults` ให้ดึงจาก backorder_id |

---

## 7. Reports/Misc (รายงาน/อื่นๆ)

### 7.1 autoinfo_money_in_report

**Workflow:** 
- Phase 1: วิเคราะห์รายได้จาก invoice
- Phase 2A: วิเคราะห์รายได้จาก cash + invoice
- ระบบสร้าง snapshot ของข้อมูล → สร้างรายงาน XLSX

**Workfunctional:** Snapshot-based money in analysis (Phase 1 + Phase 2A)

**Workcondition:** ต้องมีข้อมูล invoice และ payment

**OD19 Coverage:**
- `od19_accounting_money_in_report` — มี run, line, builder models, Phase 1 + Phase 2A, XLSX export, snapshot locking ✅

**Gaps:** ✅ ครบถ้วน

---

### 7.2 report_xlsx (OCA)

**Workflow:** OCA base XLSX report engine ที่ให้โมดูลอื่นๆ สืบทอดเพื่อสร้างรายงาน Excel

**Workfunctional:** Base XLSX report engine

**Workcondition:** ใช้เป็น dependency ของโมดูลรายงานอื่นๆ

**OD19 Coverage:** ❌ ไม่มี (od19 ใช้ openpyxl ตรงๆ)

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| OCA base XLSX report engine | ❌ | แนะนำให้ติดตั้ง OCA `report_xlsx` หรือสร้าง base abstract model `od19.report.xlsx.abstract` ที่มี methods สำหรับสร้าง XLSX ด้วย openpyxl เพื่อให้โมดูลอื่นๆ สืบทอดใช้งาน |

---

### 7.3 sign_oca + autoinfo_sign_oca

**Workflow:** 
- สร้างเอกสารสำหรับลงนาม → กำหนดผู้ลงนามและตำแหน่งลายเซ็น → ส่งให้ลงนามทาง portal → รับเอกสารที่ลงนามแล้ว
- อนุญาตให้จัดการผู้ลงนามแม้เอกสารจะอยู่สถานะ sent
- แจ้งเตือนผ่าน bus notification

**Workfunctional:**
- Document signing (templates, roles, fields, requests, portal signing)
- Allow signer management in sent state
- Bus notifications
- Systray fix

**Workcondition:** ต้องตั้งค่า portal และ email

**OD19 Coverage:** ❌ ไม่มี (ไม่มี sign module ใน Odoo 19)

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Document signing | ❌ | แนะนำให้ติดตั้ง OCA `sign` หรือ Odoo Enterprise `sign` module ถ้าต้องการฟีเจอร์นี้ หรือสร้างโมดูล `od19_document_sign` ที่ใช้ OCA sign เป็น base |
| Signer management in sent state | ❌ | ขึ้นอยู่กับว่าใช้ sign module ไหน ถ้าใช้ OCA ให้ override state machine เพื่ออนุญาตแก้ไข signer ในสถานะ sent |
| Bus notifications | ❌ | ใช้ `od19_notification_multi_channel` ที่มีอยู่แล้วสำหรับแจ้งเตือน |

---

### 7.4 autoinfo_data_link_base

**Workflow:** Abstract service ที่ช่วย preserve sale_line_ids และ purchase_line_id จาก parent invoice line เมื่อมีการสร้าง invoice line ใหม่ (เช่น จาก downpayment)

**Workfunctional:** Abstract service to preserve sale_line_ids/purchase_line_id

**Workcondition:** ใช้เมื่อมีการสร้าง invoice line ที่ต้องเชื่อมโยงกับ SO/PO line

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Abstract service preserve sale_line_ids/purchase_line_id | ❌ | สร้าง abstract model `od19.data.link.mixin` ที่มี methods สำหรับ copy/preserve sale_line_ids และ purchase_line_id จาก parent line แล้วให้โมดูลที่ต้องการ inherit ใช้ |

---

### 7.5 autoinfo_logo

**Workflow:** เพิ่ม field `logo_iso` (binary) บน res.company สำหรับเก็บ logo แบบ ISO ที่แยกจาก logo ปกติ

**Workfunctional:** `logo_iso` binary field on res.company

**Workcondition:** ใช้ได้ทุก company

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| logo_iso field on res.company | ❌ | เพิ่ม field `od19_logo_iso` (Binary) บน res.company และแสดงใน settings form |

---

### 7.6 autoinfo_skip_check_sequence

**Workflow:** Override `_constrains_date_sequence` ของ `sequence.mixin` เพื่อข้ามการตรวจสอบวันที่/ลำดับเลขที่เอกสาร (เพราะระบบไทยใช้ปี พ.ศ. และอาจมีการแก้ไขวันที่ย้อนหลัง)

**Workfunctional:** Override _constrains_date_sequence to skip date/sequence constraint

**Workcondition:** ใช้กับเอกสารทุกประเภทที่ใช้ sequence.mixin

**OD19 Coverage:** ❌ ไม่มี (แต่ Odoo 19 อาจมี l10n_th_base_sequence จาก OCA)

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Skip date/sequence constraint | ❌ | ตรวจสอบว่า Odoo 19 มี `l10n_th_base_sequence` หรือไม่ ถ้ามีให้ใช้ ถ้าไม่ สร้างโมดูล `od19_sequence_thai` ที่ override `_constrains_date_sequence` เพื่อข้ามการตรวจสอบ หรือปรับเปลี่ยนให้รองรับปี พ.ศ. |

---

### 7.7 deleted_records_info

**Workflow:** เมื่อมีการลบ record ใดๆ ในระบบ → ระบบบันทึกข้อมูลการลบ (model, record id, user, time, reason) เพื่อใช้ตรวจสอบย้อนหลัง

**Workfunctional:** Track deleted records across all models

**Workcondition:** ใช้กับทุก model ที่มีการลบ record

**OD19 Coverage:** ❌ ไม่มี

**Gaps:**
| ฟีเจอร์ | สถานะ | ข้อเสนอใน OD19 |
|---------|--------|----------------|
| Track deleted records | ❌ | สร้าง model `od19.deleted.record` ที่เก็บ model_name, record_id, deleted_by, deleted_at, reason แล้ว override `unlink` ของ BaseModel เพื่อบันทึกข้อมูลก่อนลบ (หรือใช้ OCA `auditlog` ที่มีอยู่แล้วใน third_party/oca/server-tools/auditlog) |

---

### 7.8 autoinfo_account_move_link_payment_number (ซ้ำ)

ดูที่ 3.6

---

## สรุป: โมดูลที่ต้องสร้างใหม่ใน Odoo 19

### ความสำคัญสูง (High Priority)
1. **od19_sale_terms** — 7 master report models + Jasper quotation form
2. **od19_project_enhanced** — Job No. auto-sequence, dept Many2one, SO/PO link, task deadline cron, no backward stage, job assignment fields
3. **od19_project_risk_report** — SQL view risk report
4. **od19_project_type** — Hierarchical project type
5. **od19_asset_disposal** — Disposal workflow, revert, linked docs, safe cron
6. **od19_accounting_thai_forms** — WHT PDF, convert_num_th, Jasper accounting forms
7. **od19_fleet_notification** — Insurance/Act expire date + email cron
8. **od19_expense_enhanced** — Auto dept head approver, cash tracking, XLSX, delegate
9. **od19_stock_fifo** — FIFO valuation service, monthly report email, as-of wizard

### ความสำคัญกลาง (Medium Priority)
10. **od19_purchase_terms** — 5 master report models + list price auto-fill
11. **od19_accounting_cancel_reason** — Cancel reason wizard
12. **od19_purchase_trade_discount** — Trade discount wizard
13. **od19_invoice_get_sale_lines** — Get SO lines wizard
14. **od19_payment_wht_auto** — WHT base from selected invoices
15. **od19_stock_picking_additional_lines** — Additional print lines
16. **od19_hr_expense_wht** — WHT for expense payment

### ความสำคัญต่ำ (Low Priority)
17. **od19_res_company_logo_iso** — logo_iso field
18. **od19_sequence_thai** — Skip date/sequence constraint
19. **od19_deleted_records** — Track deleted records
20. **od19_report_xlsx_base** — Base XLSX report engine
21. **od19_runtime_guard** — Runtime check tool

---

## ข้อเสนอแนะเพิ่มเติม

1. **ลดความซับซ้อน:** หลายฟีเจอร์ใน OD15 ที่แยกเป็นโมดูลย่อย สามารถรวมเข้ากับโมดูลหลักใน OD19 ได้ เช่น cancel_reason รวมเข้ากับ od19_accounting_dncn, logo_iso รวมเข้ากับ od19_thai_localization_base

2. **ใช้ OCA ให้มากที่สุด:** สำหรับฟีเจอร์ที่มี OCA module อยู่แล้ว (เช่น auditlog, report_xlsx, sign) ควรติดตั้ง OCA แทนที่จะสร้างเอง เพื่อลดภาระในการ maintain

3. **FIFO Valuation:** ตรวจสอบว่า Odoo 19 standard inventory valuation รองรับ FIFO หรือไม่ ถ้าใช่ อาจไม่จำเป็นต้องสร้าง FIFO service เอง

4. **Document Signing:** ถ้าต้องการฟีเจอร์ลงนามเอกสาร ควรประเมินว่าจะใช้ OCA sign หรือ Odoo Enterprise sign เพราะการสร้างเองมีความซับซ้อนสูง

5. **Thai Localization:** ควรรวมฟีเจอร์เกี่ยวกับภาษาไทย (convert_num_th, WHT PDF, sequence พ.ศ.) เข้ากับ od19_thai_localization_base เพื่อความเป็นระบบ
