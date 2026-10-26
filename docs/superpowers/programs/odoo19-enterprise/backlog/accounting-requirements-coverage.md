# Accounting Requirements Coverage — ตารางเทียบข้อกำหนดฝ่ายบัญชี

## Document Control

| Field | Value |
| --- | --- |
| Artifact | Accounting department requirement coverage matrix |
| Program | Odoo 19 CE Program |
| สร้างเมื่อ | 2026-10-26 |
| ตรวจจาก | แผนจริง (`domain-wave-matrix.md`, `2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md`) + สภาพดิสก์จริง (`third_party/oca/`, `custom_addons/`, `odoo.conf`) |
| ผู้จัดทำ | ทีมเทคนิค |
| ผู้รับ | ฝ่ายบัญชี / Audit |

สัญลักษณ์: ✅ ครอบคลุมแล้ว · 🟡 ครอบคลุมบางส่วน หรือแนวทางต่างแต่ได้ผลเทียบเท่า · 🔵 มีพร้อมใช้แต่ยังไม่ถูกอ้างในแผน · 🔴 ยังไม่ครอบคลุม

## 1. สรุปผู้บริหาร

- ข้อกำหนดฝ่ายบัญชีทั้งหมด 14 รายการ → **ครอบคลุมแล้ว 8**, **ครอบคลุมบางส่วน/แนวทางต่าง 3**, **มีพร้อมใช้แต่ยังไม่เข้าแผน 0**, **ยังไม่ครอบคลุม 3** (นับหลังดำเนินการวันที่ 2026-10-26)
- ในวันที่ 2026-10-26 ทีมเทคนิคได้ **เพิ่ม OCA repo ที่ขาด 3 repo** (account-invoicing, account-financial-reporting, account-reconcile) เข้า `third_party/oca/` และต่อ `addons_path` ใน `odoo.conf` แล้ว
- **ยังเหลือช่องว่างจริง 1 รายการ**: `account_invoice_supplier_ref_unique` — ยังไม่มีบน OCA branch 19.0
- **ต้องตัดสินใจ 3 เรื่อง** กับฝ่ายบัญชี (ดูข้อ 4)

## 2. ตาราง Coverage Matrix

### 2.1 ข้อมูลพื้นฐานประเทศไทย

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| จังหวัด / อำเภอ / รหัสไปรษณีย์ | core Odoo + `od19_partner_thai_fields` | 🟡 | จังหวัดใช้ `state_id` มาตรฐาน, รหัสไปรษณีย์ใช้ `zip`; **อำเภอ/ตำบล แยกเป็นฟิลด์ยังไม่มี** (ถ้าต้องใช้แยก ขออนุมัติเพิ่ม) |
| เลขประจำตัวผู้เสียภาษี 13 หลัก | core `l10n_th` (ฟิลด์ `vat`) | ✅ | มาตรฐาน Odoo + validation |
| สาขา (สำนักงานใหญ่/สาขา) | core `l10n_th` + `od19_partner_thai_fields` (`branch_code` 5 หลัก) | ✅ | HQ = `00000` |

### 2.2 Localization ไทย

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `l10n_th_base` / `l10n_th_partner` / `l10n_th_account` | core `l10n_th` | 🟡 | Odoo 19 รวม 3 โมดูลเดิมเป็น core `l10n_th` เดียว (ชื่อเดิมไม่มีแล้ว) — ผังบัญชีไทย, ภาษีไทย, รายงานภาษีพื้นฐานครบ |
| `l10n_th_withholding_tax` (WHT 3% / 5% / 1% / 0.75%) | OCA `l10n_th_account_tax` | ✅ | 19.0 ใช้ชื่อ `l10n_th_account_tax`; คำนวณ WHT อัตโนมัติ, หักตอนจ่าย, ออกรายงาน; หนังสือรับรอง 50 ทวิ พิมพ์จาก `withholding.tax.cert` (custom `od19_thai_tax_reports`) |

### 2.3 ภาษีซื้อ-ภาษีขาย

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_move_name_sequence` | OCA `account-financial-tools` | 🔵 | มีบนดิสก์; โครงการมี custom `od19_document_sequence` / `od19_accounting_document_sequence` (เลขไทย INV/PO/SO/PV ตามปี) — **ต้องเลือกว่าใช้ตัวไหน** |
| `account_fiscal_year` | OCA `account-financial-tools` | ✅ | จัดการปีบัญชี (periods) ตามที่ขอ |
| `account_lock_date_update` | OCA `account-financial-tools` | 🟡 | มีบนดิสก์พร้อมติดตั้ง; แผนปัจจุบันเลือกใช้ core lock dates + `account.lock_exception` (manual no-code) |

### 2.4 ภาษีหัก ณ ที่จ่าย

ดูข้อ 2.2 (`l10n_th_account_tax`) — ครอบคลุม ✅

### 2.5 งานเจ้าหนี้ (AP)

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_payment_order` (Payment Batch / Proposal) | — | 🔴 | **ไม่ adopt โดยเจตนา** ตามแนวทาง "Prepare Payment วิธีที่ 3" (ใช้ `account.payment` + `account.payment.register` มาตรฐาน) — ต้องยืนยันว่ากรณี "จ่ายเจ้าหนี้หลายรายพร้อมกัน" ยอมรับได้ |
| `account_invoice_supplier_ref_unique` (กันเลข invoice ผู้ขายซ้ำ) | OCA `account-invoicing` | 🔴 | **ยังไม่มีบน OCA 19.0** → เลือก (ก) รอ OCA migrate หรือ (ข) ทำ custom ขนาดเล็กในนามโครงการ |

### 2.6 สินทรัพย์ถาวร

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_asset_management` | OCA `account-financial-tools` | ✅ | Asset Group / Depreciation / Disposal / Partial Disposal / Revalue; เสริมด้วย custom `od19_asset_disposal` และ `od19_asset_loan` |

### 2.7 รายงานภาษี

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_tax_balance` (VAT ซื้อ/ขาย, Tax Reconciliation) | OCA `account-financial-reporting` | ✅ | clone repo + ต่อ addons_path แล้ว 2026-10-26 |
| `account_financial_report` (TB / GL / BS / P&L / Cash Flow) | OCA `account-financial-reporting` | ✅ | clone repo + ต่อ addons_path แล้ว 2026-10-26; ควบคู่กับ custom `od19_accounting_reporting` (QWeb) |

### 2.8 Audit Trail

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `auditlog` (ใครแก้อะไร เมื่อไร ค่าเดิม/ใหม่) | OCA `server-tools` | ✅ | มีบนดิสก์อยู่แล้ว; **adopt เข้าแผน 2026-10-26** (รองรับ ISO 9001 / Internal / External Audit) |

### 2.9 เอกสารภาษีไทย (Excel export)

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `report_xlsx` (ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 / ทะเบียนภาษีซื้อ-ขาย) | OCA `reporting-engine` | ✅ | มีบนดิสก์อยู่แล้ว; **adopt เข้าแผน 2026-10-26** เพื่อ export Excel |

### 2.10 กระทบยอดบัญชี (Bank Reconciliation)

| รายการที่ขอ | โมดูลที่เกี่ยวข้อง | สถานะ | หมายเหตุ |
| --- | --- | --- | --- |
| `account_reconcile_model_oca` | OCA `account-reconcile` | ✅ | clone repo + ต่อ addons_path แล้ว 2026-10-26; ชื่อโมดูลจริงบน 19.0 คือ **`account_reconcile_oca`** |

## 3. สิ่งที่ดำเนินการแล้ว (2026-10-26)

1. เพิ่ม git submodule 3 repo (branch 19.0) เข้า `third_party/oca/`:
   - `account-invoicing` (สำหรับ `account_invoice_supplier_ref_unique` — โมดูลยังไม่ถูก migrate)
   - `account-financial-reporting` (`account_tax_balance`, `account_financial_report`)
   - `account-reconcile` (`account_reconcile_oca`)
2. ต่อ `addons_path` ใน `odoo.conf` ให้ครบทั้ง 3 repo
3. อัปเดตเอกสารแผน: `domain-wave-matrix.md` (เพิ่มภาคผนวก Accounting Requirements Coverage) และ `2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md` (ปรับรายการ OCA availability + Keep)

## 4. เรื่องที่ต้องตัดสินใจร่วมกับฝ่ายบัญชี

| # | เรื่อง | ทางเลือก |
| --- | --- | --- |
| 1 | `account_payment_order` | รับ Prepare Payment (1 เอกสารต่อ 1 คู่สัญญา) แทน หรือต้องรองรับจ่ายหลาย partner ในครั้งเดียวจริง |
| 2 | Sequence / Lock Date | ใช้ OCA (`account_move_name_sequence`, `account_lock_date_update`) แทน หรือเสริมของ custom ที่มีอยู่ |
| 3 | `account_invoice_supplier_ref_unique` | รอ OCA migrate 19.0 หรือให้โครงการทำ custom ขนาดเล็ก |
| 4 | ฟิลด์อำเภอ/ตำบล | ต้องการแยกฟิลด์อำเภอ/ตำบลจริงหรือไม่ (ปัจจุบันมีแค่จังหวัด + รหัสไปรษณีย์) |

## 5. ภาคผนวก — ชื่อโมดูล OCA จริงบน branch 19.0

| ชื่อที่ฝ่ายบัญชีเขียน | ชื่อโมดูลจริงบน 19.0 | Repo |
| --- | --- | --- |
| `l10n_th_withholding_tax` | `l10n_th_account_tax` | OCA `l10n-thailand` |
| `account_reconcile_model_oca` | `account_reconcile_oca` | OCA `account-reconcile` |
| `l10n_th_base` / `l10n_th_partner` / `l10n_th_account` | core `l10n_th` (รวมเป็นโมดูลเดียว) | Odoo core `addons/` |
