# เอกสารออกแบบ: ฟอร์มรับชำระ / จ่ายชำระ ฉบับเทียบเท่า Odoo 15 (Payment Receipt & Voucher) — Odoo 19 CE

- **วันที่:** 2026-11-23 (rev1 — ฉบับแรก เสนอทิศทาง)
- **รหัสงาน:** OD19-PAYMENT-RECEIPT
- **โมดูลที่แตะ:** แก้ `od19_accounting_features`, `od19_accounting_payment_fee`, `od19_accounting_cheque`, `od19_accounting_payment_voucher_reports` (ไม่แตะ Odoo core และไม่แตะ `third_party/oca/`)
- **สถานะ:** ร่างเพื่อขออนุมัติทิศทาง — **ยังไม่เขียนโค้ด** (เฟสนี้ส่งมอบ "แบบ + ภาพจำลอง" ให้เลือกก่อน)
- **ขอบเขตเฟสนี้:** **ฝั่งรับชำระ (Customer / inbound) ก่อน** — ฝั่งจ่ายชำระ (Vendor / outbound) ทำในเฟสถัดไป
- **ผู้เกี่ยวข้อง:** เจ้าหน้าที่รับชำระ / ฝ่ายบัญชี / ผู้อนุมัติ / แอดมิน
- **ต้นทางอ้างอิง (Odoo 15):** `dtr_taxation`, `dtr_payment_fee`, `dtr_cheque`, `dtr_exchange_rate` (`c:\odoo-dev\Odoo15Backup\odoo\odoo15_mods_accounting\`)
- **ข้อตัดสินใจที่ต้องล็อก:** K1–K6 (ดู § 14 Open Questions)

---

## 1. บทสรุป (Summary)

ฟอร์มรับ/จ่ายชำระของ Odoo 19 ในระบบปัจจุบัน **"ย่อ" มาจาก Odoo 15 แบบไม่ครบ** เพราะของเดิมเป็น custom (`dtr_*`) ที่ผูกกับ `account.payment` ของ v15 โดยตรง พอย้ายมา v19 ซึ่งเปลี่ยนโครง `_prepare_move_line_default_vals` (ใช้ `balance` + `amount_currency` แทน `debit`/`credit`) และเลิกใช้ `exchange_rate` ที่ override ได้ จึง port มาได้แค่บางส่วน

ผลคือผู้ใช้เห็นฟอร์มที่ **ขาดทั้งแท็บข้อมูลภาษี/ค่าธรรมเนียม และขาดแถบผลรวมตัวเลข** อีกทั้งยังมีช่อง **ผู้จ่ายเงิน (Payer) / ผู้รับเงิน (Payee)** ที่ซ้ำซ้อนบนเมนูรับชำระ (เพราะ `partner_id` ก็คือผู้จ่ายอยู่แล้ว)

งานนี้จะ **จัดฟอร์มรับชำระ (inbound) ให้กลับมาเทียบเท่า v15** โดย:

1. ถอด **Payer/Payee** ออกจากฟอร์มรับชำระ (เหลือเฉพาะฝั่งจ่ายที่จำเป็นจริง)
2. คง **"เตรียมจ่าย / Prepare Payment" ไว้เฉพาะฝั่ง Vendor** — ฝั่ง Customer เอกสารต้นทางคือ **Invoice/Receipt**
3. เพิ่ม **ตัวเลือกประเภทการเปิดเอกสาร**: ใบกำกับภาษี (Tax Invoice) / ใบรับเงิน (Receipt)
4. เพิ่ม **Notebook 7 แท็บ** ตาม v15 + แท็บเช็ค: Fees/Charges · Collecting Cheques · Withholding Tax · VAT · Invoice · WHT Invoice · WHT Summary
5. เพิ่ม **แถบผลรวม (Totals strip)**: Amount · Total Collecting Cheques · Exchange Rate · Withholding Tax · Net Received
6. **แยกเลขที่เอกสารตามประเภทการเปิดเอกสาร** (ฝั่งรับชำระ): ใบรับเงิน `RE<yy><mm>-0001` · ใบกำกับภาษี `TI<yy><mm>-0001`

**เป้าหมายเชิงผลลัพธ์**

- ฟอร์มรับชำระมีข้อมูลครบเทียบเท่า v15 โดยไม่แตะ core Odoo
- ผู้ใช้เห็นยอดที่ต้องรู้ทันทีโดยไม่ต้องเปิดบัญชี journal entry
- โครงสร้างรองรับทั้งลูกค้าไทย (VAT + WHT + ใบรับเงิน) และการรับเช็คหลายใบ
- ฝั่ง Vendor ใช้โครงเดียวกันในเฟสถัดไป

---

## 2. สภาพปัจจุบันและช่องว่าง (Problem)

### 2.1 สิ่งที่มีอยู่จริงใน Odoo 19 (ยืนยันจากโค้ด)

| โมดูล | ให้อะไร | ไฟล์อ้างอิง |
|---|---|---|
| `od19_accounting_features` | `od19_payer_id` / `od19_payee_id`, `od19_wht_invoice_base_amount` / `od19_wht_rate` / `od19_wht_type_id` / `od19_wht_invoice_amount`, bill-first rule | [account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_features/models/account_payment.py) · [account_payment_views.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_features/views/account_payment_views.xml) |
| `od19_accounting_payment_fee` | `fee_amount` (ช่องเดียว) + `fee_account_id` + inject fee line ตอน post | [account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_fee/models/account_payment.py) |
| `od19_accounting_cheque` | `cheque_id` (ใบเดียว), `cheque_paid_id`, `pay_to`, คำนวณ outstanding/destination account สำหรับเช็ครับ | [account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_cheque/models/account_payment.py) |
| `od19_accounting_payment_voucher_reports` | prepare→approve→pay (`od19_prepare_state`), เลขที่ใบสำคัญ (`od19_voucher_no`), ยอดอ่านกลับจากเอกสารต้นทาง (`od19_bill_untaxed_amount` ฯลฯ), computed cheque info, rename เมนู "รายการรับชำระทั้งหมด / All Payments" | [account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_voucher_reports/models/account_payment.py) · [account_payment_views.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_voucher_reports/views/account_payment_views.xml) |
| `od19_accounting_prepayment` | smart button "Prepare Payment" — **vendor-only อยู่แล้ว** | ดู § 2.3 |

### 2.2 ตารางเทียบ Odoo 15 → Odoo 19 (ตอบคำถาม "ของพวกนี้หายไปไหน")

| # | ฟีเจอร์ (จาก Odoo 15) | ต้นทาง v15 | สถานะใน Odoo 19 ปัจจุบัน | สรุป |
|---|---|---|---|---|
| F1 | **ผู้จ่ายเงิน / ผู้รับเงิน** บนฟอร์ม | ไม่มี (v15 ใช้ `partner_id` เดียว) | มี `od19_payer_id` / `od19_payee_id` **ทุกทิศทาง** | ⚠️ **เกินมา** (ซ้ำซ้อนฝั่งรับชำระ) → ตัดออก |
| F2 | **Prepare Payment** | เฉพาะฝั่งจ่าย (vendor) | `od19_prepare_payment` `invisible` ฝั่ง inbound; pre-payment smart button vendor-only | ✅ **ตรงแล้ว** |
| F3 | **Free / Charges** (ค่าธรรมเนียมหลายบรรทัด) | `payment_fee_ids` One2many (`is_profit`, `name`, `account_id`, `analytic_account_id`, `percent`, `amount`) + `amount_fee`, `amount_with_fee` | `fee_amount` + `fee_account_id` (ช่องเดียว) ไม่มีตารางบรรทัด | ❌ **หาย** |
| F4 | **Withholding Tax** | inbound: `tax_id1/2/3` + `income_type1/2/3` + `pay_amount` / `wht_amount`; outbound: tree `wht_ids` (`dtr.wht`) | `od19_wht_*` ช่องเดียว + `invisible` ฝั่ง inbound | ❌ **หายฝั่งรับ** |
| F5 | **VAT** | `vat_ids` One2many (`dtr.vat`) + `amount_vat`, `amount_vat_base` | ไม่มีตาราง; มีแค่ `od19_bill_tax_amount` (computed) | ❌ **หาย** |
| F6 | **แท็บ Invoice** | แท็บเอกสารที่ตัดจ่าย | ไม่มีแท็บเฉพาะ (มี smart button ภายนอก) | ❌ **หาย** |
| F7 | **แท็บ WHT Invoice** | แท็บใบกำกับภาษีที่ผูก WHT | ไม่มี | ❌ **หาย** |
| F8 | **แท็บ WHT Summary** | สรุปยอดหัก ณ ที่จ่าย | ไม่มี | ❌ **หาย** |
| F9 | **Total Collecting Cheques** | `cheque_collect_ids` One2many (`dtr.cheque`) + `cheque_collect_amount` (Monetary) | `cheque_id` (ใบเดียว) ไม่มีตาราง/ผลรวม | ❌ **หาย** |
| F10 | **Exchange Rate** | `exchange_rate` (override ได้) | ไม่มี (v19 ใช้ `amount_currency` เป็น native; ไม่มี field อัตราแลกเปลี่ยนที่แก้ได้) | ❌ **หาย** |
| F11 | **Amount / Net Received** | `amount`, `amount_net` (`amount - amount_wht`), `amount_taxable` | มีแต่ `amount` | ❌ **หาย** |

**คำตอบตรง ๆ:** F3–F11 **หายจริง** — ไม่ได้ถูกย้ายไปที่อื่น แต่ "ไม่ถูก port" เพราะเป็น custom ของ v15 ที่ผูก core เก่า ส่วน F1 **เกินมา** และ F2 **ถูกต้องแล้ว**

### 2.3 ปัญหาที่ผู้ใช้รายงาน (ตรงกับตาราง)

- เมนู **"รายการรับชำระทั้งหมด"** มีช่อง **ผู้จ่ายเงิน/ผู้รับเงิน** ที่ไม่จำเป็น (F1)
- ฟอร์มขาด **ตัวเลือกประเภทเอกสาร** (ใบกำกับภาษี / ใบรับเงิน)
- ฟอร์มขาด **แท็บข้อมูลเพิ่มเติม** ตาม v15 (F3–F8)
- ฟอร์มขาด **แถบผลรวมตัวเลข** (F9–F11)

---

## 3. ความต้องการ (Requirements)

| รหัส | ความต้องการ | เกณฑ์ผ่าน |
|---|---|---|
| R1 | ฟอร์ม/เมนูรับชำระ **ไม่มี** ช่อง Payer/Payee | ฟอร์ม inbound ไม่ render `od19_payer_id`/`od19_payee_id` |
| R2 | "Prepare Payment" แสดง **เฉพาะฝั่ง Vendor**; ฝั่ง Customer = Invoice/Receipt | ปุ่มเตรียมจ่ายไม่โผล่ฝั่ง inbound; มีปุ่ม/แท็บ Invoice แทน |
| R3 | ฟอร์มมี **ตัวเลือกประเภทการเปิดเอกสาร**: ใบกำกับภาษี / ใบรับเงิน | field `od19_receipt_doc_type` (Selection) แสดงฝั่ง inbound |
| R4 | มี **Notebook แท็บ** ตาม v15: Fees/Charges · Collecting Cheques · WHT · VAT · Invoice · WHT Invoice · WHT Summary | เปิดฟอร์มรับชำระเห็นครบ 7 แท็บ |
| R5 | มี **แถบผลรวม**: Amount · Total Collecting Cheques · Exchange Rate · WHT Amount · Net Received | ค่าตรงกับเอกสารต้นทาง/บรรทัดที่บันทึก |
| R6 | รับเช็ค **หลายใบ** ได้ และรวมยอดอัตโนมัติ | เพิ่มบรรทัดเช็ค ≥2 ใบ → Total Collecting Cheques = ผลรวม |
| R7 | ลงค่าธรรมเนียม **หลายบรรทัด** ได้ | เพิ่มบรรทัด fee ≥2 → กระทบ liquidity ตามยอดรวม |
| R8 | ไม่แตะ Odoo core / `third_party/oca/` | diff เฉพาะ `custom_addons/` |
| R9 | แท็บ **Invoice** ดึง **เอกสารที่เกี่ยวข้องของคู่ค้า** (ใบแจ้งหนี้/ใบกำกับภาษี/ใบรับเงิน) มาให้ **เลือกเอง** — ประเภทเอกสารเป็นเพียงตัวกรองเริ่มต้น ไม่บังคับ | เลือก ใบกำกับภาษี → ตั้งกรองเริ่มต้นเป็นใบกำกับภาษี/ใบแจ้งหนี้; เลือก ใบรับเงิน → ตั้งกรองเป็นใบรับเงิน; แต่ยังเห็น/เลือกเอกสารอื่นที่เกี่ยวข้องได้ทั้งหมด |
| R10 | เลขที่เอกสารรับชำระ **แยกชุดตามประเภทการเปิดเอกสาร**: ใบรับเงิน `RE<yy><mm>-0001` · ใบกำกับภาษี `TI<yy><mm>-0001` | เลือก ใบรับเงิน → เลขขึ้นต้น `RE`; เลือก ใบกำกับภาษี → เลขขึ้นต้น `TI` |

---

## 4. ขอบเขต (Scope)

**In (เฟสนี้ — ฝั่งรับชำระ / inbound)**

- ถอด Payer/Payee ออกจากฟอร์มรับชำระ
- ตัวเลือกประเภทเอกสาร (ใบกำกับภาษี / ใบรับเงิน)
- Notebook 7 แท็บ + แถบผลรวม
- รับเช็คหลายใบ + Total Collecting Cheques
- ค่าธรรมเนียมหลายบรรทัด + ผลรวม
- WHT / VAT ของฝั่งรับ (แสดง + บันทึก)

**Out (เฟสนี้ไม่ทำ)**

- ฝั่งจ่ายชำระ (Vendor / outbound) — ทำเฟส 2 ด้วยโครงเดียวกัน (เว้นแต่ค่าที่ต่างกัน)
- e-Tax / ใบรับรองแทนใบเสร็จ (มีในโมดูล HR expense แล้ว — ไม่แตะ)
- เปลี่ยนโครง journal entry ของ core **นอกเหนือจาก** ที่จำเป็นต่อ fee/WHT/VAT/อัตราแลกเปลี่ยน (ดู K4/K5)
- รายงานพิมพ์ (มี QWeb อยู่แล้ว — ปรับเฉพาะเมื่อผลรวมใหม่ต้องโผล่ในรายงาน)

> **แก้ไข 2026-11-24 (มติผู้ใช้):** เดิม § 4 เคยกัน "อัตราแลกเปลี่ยนแบบแก้มือแล้วกระทบ journal" ออก แต่ **มติ K5 กลับให้ทำ** (แก้ได้ + กระทบ journal) จึงย้ายจาก Out → In (ดู § 8 และ § 14)

---

## 5. สถาปัตยกรรม + ที่ตั้งโมดูล (Design / Architecture)

**หลักการ:** เก็บของเดิมไว้ให้เสถียร แล้ว **ต่อยอดด้วยฟิลด์ `od19_*` ใหม่ + inherit view** ไม่เขียนทับของเดิม

| ชั้น | ที่อยู่ | หน้าที่ |
|---|---|---|
| ฟิลด์ยอดรวม + ประเภทเอกสาร | `od19_accounting_features` | `od19_receipt_doc_type`, `od19_amount_net`, `od19_exchange_rate` |
| ค่าธรรมเนียมหลายบรรทัด | `od19_accounting_payment_fee` | model ใหม่ `od19.payment.fee.line` + `od19_fee_ids` + ผลรวม |
| เช็คหลายใบ | `od19_accounting_cheque` | model ใหม่ `od19.payment.cheque.collect` + `od19_cheque_collect_ids` + `od19_cheque_collect_amount` |
| WHT / VAT lines | `od19_accounting_features` | model ใหม่ `od19.payment.wht.line`, `od19.payment.vat.line` |
| ประกอบฟอร์ม (Notebook 7 แท็บ + totals) | `od19_accounting_payment_voucher_reports` | view orchestration เดียว (จุดเดียวที่จัด layout) |
| แท็บ Invoice / WHT Invoice / WHT Summary | `od19_accounting_payment_voucher_reports` | ใช้ field ที่คำนวณจากเอกสารต้นทางเดิม (มีอยู่แล้ว: `od19_source_move_ids`, `od19_bill_*`) |

> **เหตุผลที่รวม layout ไว้โมดูลเดียว:** ปัจจุบันมี 4 โมดูลยิง `inherit_id` ใส่ `account.view_account_payment_form` พร้อมกัน เสี่ยง xpath ชนกัน/ลำดับไม่แน่นอน → ให้ `...voucher_reports` เป็นเจ้าของ layout หลัก แล้วโมดูลอื่น "ส่งมอบฟิลด์" เท่านั้น

---

## 6. โมเดลข้อมูล (Data Model)

### 6.1 ฟิลด์ใหม่บน `account.payment`

| ฟิลด์ | ชนิด | ทิศทาง | หมายเหตุ |
|---|---|---|---|
| `od19_receipt_doc_type` | Selection(`tax_invoice`=ใบกำกับภาษี, `receipt`=ใบรับเงิน) | inbound | R3 (มติ K8: drives ชุดเลข RE/TI) |
| `od19_amount_net` | Monetary (compute, store) | both | `amount - od19_wht_amount - od19_fee_amount` (ทิศทางกำหนดเครื่องหมาย) — R5 |
| `od19_exchange_rate` | Float (store, แก้ได้) | both | อัตราเทียบสกุลบริษัท ↔ สกุลเอกสาร · **แก้ได้ และใช้แปลง `balance` ของ move line ตอน post** (มติ K5) |
| `od19_wht_amount` | Monetary (compute, store) | both | ผลรวมจาก `od19_wht_line_ids` |
| `od19_fee_ids` | One2many(`od19.payment.fee.line`) | both | F3, R7 |
| `od19_fee_amount` | Monetary (compute, store) | both | ผลรวม fee |
| `od19_cheque_collect_ids` | One2many(`od19.payment.cheque.collect`) | inbound | F9, R6 |
| `od19_cheque_collect_amount` | Monetary (compute, store) | inbound | "Total Collecting Cheques" |
| `od19_wht_line_ids` | One2many(`od19.payment.wht.line`) | both | F4 |
| `od19_vat_line_ids` | One2many(`od19.payment.vat.line`) | both | F5 |
| `od19_vat_amount` | Monetary (compute, store) | both | ผลรวมจาก `od19_vat_line_ids` (มติ K4: ลงบัญชีจริง) |

> **หมายเหตุ:** ยังคงมี `od19_wht_invoice_base_amount` / `od19_wht_rate` / `od19_wht_invoice_amount` เดิมอยู่ — งานนี้จะ **ไม่ลบ** แต่ย้ายไปทำหน้าที่เป็น "ค่าเริ่มต้น" ให้ `od19_wht_line_ids` (จะประสานใน K2)

### 6.2 โมเดลย่อย (บรรทัด)

| โมเดล | ฟิลด์หลัก | อ้างอิง v15 |
|---|---|---|
| `od19.payment.fee.line` | `is_profit`, `name`, `account_id`, `analytic_distribution`, `percent`, `amount` | `dtr.payment.fee` |
| `od19.payment.cheque.collect` | `name` (เลขที่เช็ค), `bank_id`, `bank_branch`, `cheque_date`, `amount`, `journal_id` | `dtr.cheque` |
| `od19.payment.wht.line` | `tax_id` (`account.withholding.tax`), `income_type`, `pay_amount`, `wht_amount` | `dtr.wht` + `tax_id1/2/3` |
| `od19.payment.vat.line` | `tax_id`, `base_amount`, `vat_amount`, `invoice_id` | `dtr.vat` |

### 6.3 เลขที่เอกสาร (Sequence) — แยกชุดตามประเภท (K8)

ปัจจุบันเลขใบรับ/ใบสำคัญ **อ้างตามทิศทางอย่างเดียว ไม่ได้อ้างประเภทเอกสาร**: ฟิลด์ `od19_voucher_no` รันจาก `VOUCHER_SEQUENCE_BY_PAYMENT_TYPE` → inbound = `account.voucher.customer.payment` (`RV…`) · outbound = `account.voucher.vendor.payment` (`PV…`) ทำให้ **ใบรับเงินและใบกำกับภาษีใช้ `RV` ร่วมกัน** ([account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_voucher_reports/models/account_payment.py#L308-L323))

ตามมติ K8 จะ **เพิ่ม `ir.sequence` ใหม่ 2 ตัว** (ฝั่งรับชำระ) และปรับ `_od19_voucher_sequence_code` ให้เลือกตาม `od19_receipt_doc_type`:

| ประเภทเอกสาร | code (`ir.sequence`) | prefix | ตัวอย่าง |
|---|---|---|---|
| ใบรับเงิน | `account.voucher.receipt` | `RE%(range_y)s%(range_month)s-` | `RE2611-0001` |
| ใบกำกับภาษี | `account.voucher.tax.invoice` | `TI%(range_y)s%(range_month)s-` | `TI2611-0001` |

- เพิ่มนิยามใน [ir_sequence_data.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_document_sequence/data/ir_sequence_data.xml) แบบ `noupdate="1"` + `company_id=False` + `padding 4` (เหมือนตัวอื่น)
- ฝั่ง outbound คง `PV` เดิมไม่แตะ
- ถ้าเป็น inbound แต่ยังไม่เลือกประเภทเอกสาร → fallback เป็น `RV` เดิม (ไม่ให้เลขเว้นว่าง)

---

## 7. สถานะ / เส้นทางเอกสาร (State / Flow)

**ฝั่งรับชำระ (inbound) — ไม่มี Prepare/Approve gate (ตาม R2)**

```
Invoice (Customer)  --Register Payment-->  account.payment (draft)
        │                                       │
        │                                       ├─ เลือกประเภทเอกสาร (ใบกำกับภาษี/ใบรับเงิน)
        │                                       ├─ กรอก WHT / Fees / เช็คหลายใบ
        │                                       └─ Confirm (Post)  →  state = in_process → paid
```

**ฝั่งจ่ายชำระ (outbound) — คง Prepare→Approve→Pay เดิมไว้ไม่แตะ**

```
Vendor Bill --Register Payment (Prepare Payment)--> draft
   → action_od19_prepare → action_od19_approve → Post
```

> การแสดงผลต่างกันตาม `payment_type`: ฟอร์ม inbound **ไม่มี** ปุ่ม Prepare/Approve; ฟอร์ม outbound **มี**

---

## 8. บัญชีและภาษี (Accounting / Tax)

- **Net Received / Net Paid** = `amount − WHT − Fees` (ทิศทางรับ: เงินเข้าจริงเป็นบวก) → ใช้เป็นยอดของ liquidity line ตามรูปแบบ v15 (`get_payment_amount_net`)
- **Total Collecting Cheques** = ผลรวม `od19_cheque_collect_ids.amount` → เช็คที่รับจะ park บนบัญชี cheque-received แล้วค่อยนำฝาก (ใช้โครงเดิมของ `od19_accounting_cheque` ที่คำนวณ outstanding account ให้แล้ว)
- **WHT** → สร้าง move line ต่อบรรทัด (`_prepare_wht_aml` เทียบ v15): ฝั่งรับใช้ `property_wht_receivable_id` ของคู่ค้า; ฝั่งจ่ายใช้ `property_wht_payable_id`
- **VAT** → **มติ K4 (2026-11-24): สร้าง move line ต่อบรรทัดจาก `od19_vat_line_ids` และลงบัญชีจริง** (แก้ได้ในสถานะร่าง; readonly เมื่อ post) — ฝั่งรับใช้บัญชี VAT ของคู่ค้า/บริษัทตามผังบัญชี ไม่ซ้ำกับ VAT ที่รับรู้แล้วในใบกำกับภาษี เพราะรับรู้ ณ วันชำระ
- **Exchange Rate** → **มติ K5 (2026-11-24): แก้ได้ และใช้แปลง `balance` ของ move line ตอน post** (`od19_exchange_rate` override การแปลง core เฉพาะรายการจ่ายนี้) — มีค่าเริ่มต้นจากอัตราของบริษัท ณ วันชำระ; หากปล่อยว่างใช้พฤติกรรม core ตามเดิม

---

## 9. UX / หน้าจอ (ผูกกับ Mockup)

ดูภาพจำลอง 2 แบบที่ [2026-11-23-od19-payment-receipt-form-mockup.html](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-11-23-od19-payment-receipt-form-mockup.html)

- **แบบ A — กระชับ (แนะนำ):** Header → แถบผลรวม (Totals strip) ใต้ชื่อคู่ค้า → Notebook 7 แท็บ → แท็บแรกคือ Fees/Charges ต่อด้วย Collecting Cheques
- **แบบ B — ตาม v15 เป๊ะ:** วาง WHT/Fees ไว้ในที่เดิมของ v15 ก่อน notebook อื่น, ไม่มี totals strip รวม (ตัวเลขกระจายตามแท็บ)

**รายละเอียดที่ทั้งสองแบบต้องมี**

- ไม่มีช่อง Payer/Payee (R1)
- มีช่อง **ประเภทการเปิดเอกสาร** (R3)
- Totals strip: Amount · Total Collecting Cheques · Exchange Rate · WHT · Net Received (R5)
- Notebook 7 แท็บ: Fees/Charges · Collecting Cheques · WHT · VAT · Invoice · WHT Invoice · WHT Summary (R4)
- แท็บ **Invoice** = ตัวเลือกเอกสารที่เกี่ยวข้องของคู่ค้า — เลือกตัดจ่ายได้หลายใบ และ **ไม่กรองตายตัว** ตามประเภทเอกสาร (R9)
- Cheque รับหลายใบ (grid) + Fees หลายบรรทัด (grid) (R6, R7)

---

## 10. สิทธิ์ / ความปลอดภัย (Security)

- ไม่เพิ่มกลุ่มใหม่ — ใช้ `account.group_account_invoice` / `group_account_readonly` และกลุ่ม approver เดิม
- ฟิลด์ใหม่ทุกตัว inherit สิทธิ์จาก `account.payment` (ไม่ตั้ง `groups` ยกเว้นปุ่มอนุมัติเดิม)
- WHT/VAT/Fee lines: แก้ได้เฉพาะ `state == 'draft'` (readonly เมื่อ post) — ตาม v15

---

## 11. การย้ายข้อมูล (Migration)

- เรนาม/ไม่ลบฟิลด์เดิม; ฟิลด์ใหม่ nullable
- ข้อมูลเก่าที่มี `od19_payer_id`/`od19_payee_id` ยังคงอยู่ใน DB (ไม่แสดงบนฟอร์มรับชำระ) — ถ้าอนุมัติ K1 ให้ "ไม่ลบ" จะไม่ต้อง migration
- `fee_amount` เดิม (ช่องเดียว) → ถ้าอนุมัติ K3 ให้ map เป็น 1 บรรทัดใน `od19_fee_ids` ตอน migrate (optional; เก็บของเดิมไว้เป็น fallback)
- `ir.sequence` ใหม่ 2 ตัว (RE/TI) ติดตั้งผ่าน `noupdate="1"` — ข้อมูลเดิมที่มี `od19_voucher_no` เป็น `RV…` **ไม่แก้ย้อนหลัง** (ของเก่าคงไว้; ของใหม่แยกชุดตาม K8)

---

## 12. เฟสการส่งมอบ (Phases)

| เฟส | เนื้อหา | เกณฑ์ปิด |
|---|---|---|
| **P0 (ตอนนี้)** | Spec + Mockup 2 แบบ | ผู้ใช้อนุมัติแบบ + ล็อก K1–K6 |
| P1 | ถอด Payer/Payee ฝั่งรับ + ช่องประเภทเอกสาร + Totals strip | R1, R3, R5 (บางส่วน) |
| P2 | Notebook แท็บ (โชว์ข้อมูลจากเอกสารต้นทางก่อน) | R4 |
| P3 | Cheque หลายใบ + Total Collecting Cheques | R6, R5 |
| P4 | Fees หลายบรรทัด + WHT/VAT lines + บันทึกลง journal | R7, R8 |
| P5 | ฝั่ง Vendor (outbound) ใช้โครงเดียวกัน | parity เต็ม |

**ทุกเฟส:** ทำตาม AGENTS.md r8 → เทสต์ผ่าน → `-u odoo19_pdev` → deploy release → restart `8070` → commit

---

## 13. แผนเทสต์ (TDD)

| เทสต์ | ตรวจ |
|---|---|
| T1 | ฟอร์ม inbound ไม่มี `od19_payer_id`/`od19_payee_id` |
| T2 | ปุ่ม Prepare ไม่โผล่ฝั่ง inbound; โผล่ฝั่ง outbound |
| T3 | เลือก `od19_receipt_doc_type` = ใบกำกับภาษี / ใบรับเงิน บันทึกได้ |
| T4 | `od19_amount_net` = `amount − WHT − Fees` ถูกต้องทั้งเครื่องหมาย inbound/outbound |
| T5 | ใส่เช็ค 2 ใบ (100, 250) → `od19_cheque_collect_amount` = 350 |
| T6 | ใส่ fee 2 บรรทัด → liquidity line ลดลงตามผลรวม; journal balanced |
| T7 | WHT line → เกิด move line ที่บัญชี WHT ถูกต้อง และ net ตรง |
| T8 | เปิด 7 แท็บครบ ไม่มี xpath error ตอน `-u` |
| T9 | แท็บ Invoice ดึงเอกสารที่เกี่ยวข้องของคู่ค้าได้ และเลือกตัดจ่ายหลายใบพร้อมกัน |
| T10 | เลือก ใบรับเงิน → เลขขึ้นต้น `RE<yy><mm>-`; เลือก ใบกำกับภาษี → เลขขึ้นต้น `TI<yy><mm>-` |

---

## 14. คำถามที่ต้องตัดสินใจ (Open Questions)

| รหัส | คำถาม | ข้อเสนอแนะนำ |
|---|---|---|
| **K1** | Payer/Payee: **ลบ field** หรือ **ซ่อนบนฟอร์มรับชำระ** | ✅ **มติผู้ใช้ 2026-11-24: ซ่อนบนฟอร์ม inbound** (คง field ไว้ไม่ให้ข้อมูลเก่าพัง) |
| **K2** | WHT ฝั่งรับ: ใช้ **One2many หลายบรรทัด** หรือ **3 ช่องคงที่** เหมือน v15 | ✅ **มติผู้ใช้ 2026-11-24: One2many หลายบรรทัด** |
| **K3** | `fee_amount` เดิม: **ทับด้วยตารางใหม่** หรือ **อยู่คู่กัน** | ✅ **มติผู้ใช้ 2026-11-24: ตารางใหม่ `od19_fee_ids`** เป็นหลัก; `fee_amount` เดิมคงไว้เป็น fallback |
| **K4** | VAT: **สร้าง line ใหม่** หรือ **อ่านจากใบกำกับภาษี (read-only)** | ✅ **มติผู้ใช้ 2026-11-24: "แก้ได้และกระทบ journal"** — สร้าง line ใหม่ที่แก้ได้ และลงบัญชีจริง (เบี่ยงจากข้อเสนอเดิม read-only) |
| **K5** | Exchange Rate: **แก้ได้แล้วกระทบ journal** หรือ **แสดงเป็นข้อมูลอ้างอิง** | ✅ **มติผู้ใช้ 2026-11-24: "แก้ได้และกระทบ journal"** — override การแปลงสกุลเฉพาะรายการจ่ายนี้ (เบี่ยงจากข้อเสนอเดิม) |
| **K6** | เลือก **แบบ A (กระชับ)** หรือ **แบบ B (ตาม v15 เป๊ะ)** | ✅ **มติผู้ใช้ 2026-11-24: แบบ A (กระชับ)** |
| **K7** | แท็บ Invoice: **กรองตามประเภทเอกสาร** หรือ **แสดงเอกสารที่เกี่ยวข้องทั้งหมดให้เลือกเอง** | **แสดงเอกสารที่เกี่ยวข้องทั้งหมดของคู่ค้าให้เลือกเอง** — ประเภทเอกสารเป็นแค่ตัวกรองเริ่มต้น (มติผู้ใช้ 2026-11-23) |
| **K8** | เลขที่รับชำระ: ใช้ RV ร่วมทั้งสองประเภท หรือ **แยกชุดตามประเภทเอกสาร** | **แยกชุด + สร้าง `ir.sequence` ใหม่** — ใบรับเงิน `RE<yy><mm>-<4>` · ใบกำกับภาษี `TI<yy><mm>-<4>` (มติผู้ใช้ 2026-11-23; เพิ่มเดือน 2 หลัก 2026-11-24) |
| **K9** | ยอดของใบรับชำระ: **แก้ไขยอดได้** หรือ **ล็อกยอดไม่แก้** | ✅ **มติผู้ใช้ 2026-11-24: "ยอดไม่แก้ แต่ถ้า undue vat ขอแก้ไขวันที่พอ"** — ยอด net คงเดิมไม่ให้แก้; เฉพาะบรรทัด **VAT (undue)** เปิดช่อง **วันที่เอกสาร** ให้แก้ได้ |

---

## 15. เกณฑ์ยอมรับ (Acceptance Criteria)

- [ ] R1–R10 ผ่านทั้งหมด (§ 3)
- [ ] เทสต์ T1–T10 ผ่าน (`-u odoo19_pdev`)
- [ ] ไม่มี xpath/view error ตอนอัปเดตโมดูล
- [ ] ฟอร์มรับชำระเปิดได้ แสดง 7 แท็บ + totals strip ครบ
- [ ] แท็บ Invoice แสดงเอกสารที่เกี่ยวข้องของคู่ค้าให้เลือกได้ (R9)
- [ ] เลือก ใบรับเงิน → เลขขึ้นต้น `RE<yy><mm>-`; เลือก ใบกำกับภาษี → เลขขึ้นต้น `TI<yy><mm>-` (R10)
- [ ] ฝั่ง Vendor ยังทำงานเดิม (Prepare→Approve→Pay) ไม่พัง
- [ ] ไม่แตะ core / `third_party/oca/`
- [ ] deploy release + restart `8070` + verify online

---

## 16. ภาคผนวก — จุดอ้างอิงโค้ด

**Odoo 19 (ปัจจุบัน)**

- [account_payment.py (features)](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_features/models/account_payment.py)
- [account_payment_views.xml (features)](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_features/views/account_payment_views.xml)
- [account_payment.py (fee)](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_fee/models/account_payment.py)
- [account_payment.py (cheque)](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_cheque/models/account_payment.py)
- [account_payment.py (voucher reports)](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_voucher_reports/models/account_payment.py)
- [account_payment_views.xml (voucher reports)](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_payment_voucher_reports/views/account_payment_views.xml)

**Odoo 15 (ต้นทางอ้างอิง)**

- `dtr_taxation/models/account_payment.py` — WHT/VAT/net, `_prepare_wht_aml`, `get_payment_amount_net`
- `dtr_taxation/view/account_payment_invoice_view.xml` — แท็บ Withholding Tax
- `dtr_payment_fee/view/account_payment_view.xml` — แท็บ Fees/Charges (`payment_fee_ids`)
- `dtr_cheque/models/account_payment.py` — `cheque_collect_ids` + `cheque_collect_amount`
