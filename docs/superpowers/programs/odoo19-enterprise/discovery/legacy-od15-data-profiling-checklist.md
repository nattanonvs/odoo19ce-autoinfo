# Legacy Odoo 15 → Odoo 19 Data Profiling Checklist

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 Enterprise (Greenfield + ETL) |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/discovery/legacy-od15-data-profiling-checklist.md` |
| Artifact owner | Migration / Data engineering lead |
| Artifact status | Template (ยังไม่กรอกผล — รอการรัน Profiling) |
| Source system | Odoo 15 CE (legacy) |
| Target system | Odoo 19 (fresh database) |
| SQL ที่ใช้คู่กัน | `migration/extract/01_profiling_queries.sql` |
| Last updated | 2026-10-22 |

## บริบทและขอบเขต (Context)

กลยุทธ์การย้ายข้อมูลคือ **Greenfield + ETL**: ฐานข้อมูล Odoo 19 ใหม่จะรับเฉพาะ
**ข้อมูลหลัก (master data)** และ **ยอดยกมา (opening balances)** เท่านั้น
ไม่ยกประวัติธุรกรรมทั้งก้อน ดังนั้นการ Profiling จึงโฟกัส 3 เรื่อง:

1. **ปริมาณข้อมูล (data volume)** — เพื่อประเมินเวลาและขอบเขตของ ETL
2. **ช่องว่างคุณภาพข้อมูล (data quality gaps)** — สิ่งที่จะทำให้การ import ล้มเหลว
3. **ตัวเลข opening balance ที่ต้อง tie หลัง import (reconciliation baseline)**

> **ข้อบังคับสำคัญ:** การ Profiling ต้องรันบน **สำเนาที่ restore แล้ว** (ชื่อฐานข้อมูล `od15_stage`)
> **ห้ามรันบนฐานข้อมูล production ของระบบเดิมเด็ดขาด** และต้องตั้งการเชื่อมต่อเป็น **read-only**

ไฟล์ SQL ที่ใช้คู่กับเอกสารนี้: `c:\odoo-dev\odoo19\migration\extract\01_profiling_queries.sql`
วิธีรัน:
```
psql -h <host> -U <user> -d od15_stage -f 01_profiling_queries.sql > profiling_result.txt
```

---

## Section 0 : ขั้นตอนเตรียมการ

| # | ขั้นตอน | รายละเอียด | Query | ผลลัพธ์ที่คาดหวัง | สถานะ |
| --- | --- | --- | --- | --- | --- |
| 0.1 | Restore dump เป็นสำเนา | Restore backup ของ Odoo 15 เป็นฐานข้อมูลใหม่ชื่อ `od15_stage` (ห้ามใช้ DB production) | — | ได้ DB `od15_stage` ที่เปิดใช้งานได้ | ☐ |
| 0.2 | ตั้ง read-only | ใช้ role ที่มีสิทธิ์อ่านเท่านั้น หรือรันใน transaction เดียวแล้ว ROLLBACK; ตรวจด้วย query ยืนยัน | `[0.3]` | `transaction_read_only = on` | ☐ |
| 0.3 | ตรวจเวอร์ชัน Odoo 15 | อ่านค่า `base_version` จาก `ir_config_parameter` | `[0.1]` | ค่าขึ้นต้นด้วย `15.` | ☐ |
| 0.4 | ตรวจเวอร์ชันโมดูลหลัก | อ่าน `latest_version` ของ `base`, `account`, `stock`, `sale`, `purchase`, `hr`, `project` จาก `ir_module_module` | `[0.2]` | `base` = `15.0.x.x.x` | ☐ |
| 0.5 | ยืนยันชื่อฐานข้อมูล | ยืนยันว่ากำลังต่อกับ `od15_stage` | `[0.3]` | `database_name = od15_stage` | ☐ |
| 0.6 | เตรียมที่เก็บหลักฐาน | redirect ผลลัพธ์ทุก query เป็นไฟล์ `profiling_result.txt` และแนบเก็บ | — | มีไฟล์หลักฐานครบ | ☐ |

ผลการตรวจเวอร์ชัน (บันทึก):

| รายการ | ค่าที่อ่านได้ |
| --- | --- |
| `base_version` | |
| `ir.module.module` base `latest_version` | |
| database name ที่เชื่อมต่อ | |
| transaction_read_only | |

---

## Section 1 : ทะเบียนโมดูลที่ติดตั้งจริง (Installed Module Inventory)

แหล่งข้อมูล: `ir_module_module` ที่ `state = 'installed'` (query `[1.2]`, `[1.3]`, `[1.5]`)

### 1.1 สรุปจำนวนโมดูล

| หมวด | จำนวน (จาก query `[1.4]`) | หมายเหตุ |
| --- | --- | --- |
| core/other | | |
| OCA | | |
| custom (`autoinfo_*` / `dtr_*` / `account_invoice_get_sale`) | | |
| **รวมทั้งหมด (installed)** | | เทียบกับ `[1.1]` |

> หมายเหตุ: การแยก core / OCA / custom ใน SQL อ้างอิงจาก prefix ของชื่อโมดูลและคอลัมน์
> `author`/`maintainer` (ตรวจสอบกับ source Odoo 15 CE แล้วว่าคอลัมน์เหล่านี้มีจริงที่
> `odoo/addons/base/models/ir_module.py`) ให้ทบทวนผลลัพธ์จริงอีกรอบ

### 1.2 รายชื่อโมดูล custom ที่พบในระบบเดิม (จากโครงสร้างโฟลเดอร์จริง)

โฟลเดอร์ `c:\odoo-dev\Odoo15Backup\odoo\custom15_autoinfo` (prefix `autoinfo_*` และ 1 โมดูลชื่ออื่น):

| # | โมดูลเดิม (Odoo 15) | ติดตั้งจริง? (ยืนยันจาก `[1.5]`) | mapping ไปยังโมดูล od19_* ปลายทาง | สถานะ mapping |
| --- | --- | --- | --- | --- |
| 1 | `account_invoice_get_sale` | | | ☐ |
| 2 | `autoinfo_account` | | | ☐ |
| 3 | `autoinfo_account_move_link_payment_number` | | | ☐ |
| 4 | `autoinfo_accounting_form` | | | ☐ |
| 5 | `autoinfo_accounting_form_wht_fix` | | | ☐ |
| 6 | `autoinfo_asset_sale_fix` | | | ☐ |
| 7 | `autoinfo_currency_rate_bot` | | `od19_currency_rate_bot` | ☐ |
| 8 | `autoinfo_data_link_base` | | | ☐ |
| 9 | `autoinfo_data_link_project` | | | ☐ |
| 10 | `autoinfo_employees` | | | ☐ |
| 11 | `autoinfo_fixes_accounting_runtime_guard` | | | ☐ |
| 12 | `autoinfo_fleet` | | | ☐ |
| 13 | `autoinfo_hr_expense` | | `od19_hr_expense_enhanced` / `od19_hr_expense_thai` | ☐ |
| 14 | `autoinfo_hr_expense_cash_tracking` | | | ☐ |
| 15 | `autoinfo_logo` | | | ☐ |
| 16 | `autoinfo_money_in_report` | | `od19_accounting_money_in_report` | ☐ |
| 17 | `autoinfo_payment_wht` | | `od19_thai_tax_reports` | ☐ |
| 18 | `autoinfo_project` | | `od19_project_enhanced` | ☐ |
| 19 | `autoinfo_project_form` | | | ☐ |
| 20 | `autoinfo_project_risk_report` | | | ☐ |
| 21 | `autoinfo_purchase` | | `od19_purchase_procurement_core` | ☐ |
| 22 | `autoinfo_purchase_form` | | `od19_purchase_terms` | ☐ |
| 23 | `autoinfo_repeat_customer_dashboard` | | | ☐ |
| 24 | `autoinfo_sale` | | `od19_sale_terms` / `od19_sales_contract_core` | ☐ |
| 25 | `autoinfo_sale_form` | | `od19_sale_terms` | ☐ |
| 26 | `autoinfo_sale_order_invoice_amount` | | `od19_sales_currency_amount` | ☐ |
| 27 | `autoinfo_sign_oca` | | `od19_document_sign` | ☐ |
| 28 | `autoinfo_skip_check_sequence` | | `od19_document_sequence` | ☐ |
| 29 | `autoinfo_stock_monthly_report` | | `od19_stock_fifo` / `od19_inventory_reporting` | ☐ |

โฟลเดอร์ `c:\odoo-dev\Odoo15Backup\odoo\odoo15_mods` (prefix `dtr_*`):

| # | โมดูลเดิม (Odoo 15) | ติดตั้งจริง? | mapping ไปยังโมดูล od19_* ปลายทาง | สถานะ mapping |
| --- | --- | --- | --- | --- |
| 1 | `dtr_access_right_base` | | | ☐ |
| 2 | `dtr_access_right_base_partner_rules` | | | ☐ |
| 3 | `dtr_account_control_level` | | | ☐ |
| 4 | `dtr_coa` | | `od19_thai_localization_base` | ☐ |
| 5 | `dtr_common` | | | ☐ |
| 6 | `dtr_company` | | | ☐ |
| 7 | `dtr_customer_invoices` | | | ☐ |
| 8 | `dtr_database_cleanup` | | | ☐ |
| 9 | `dtr_document_sequence_group` | | `od19_document_sequence` | ☐ |
| 10 | `dtr_employee_master` | | | ☐ |
| 11 | `dtr_erp_package_core` | | | ☐ |
| 12 | `dtr_exchange_rate` | | `od19_currency_rate_bot` | ☐ |
| 13 | `dtr_goods_issue` | | `od19_goods_issue` | ☐ |
| 14 | `dtr_goods_issue_project` | | | ☐ |
| 15 | `dtr_goods_issue_tier_validation` | | | ☐ |
| 16 | `dtr_inventory_department` | | | ☐ |
| 17 | `dtr_inventory_filter` | | | ☐ |
| 18 | `dtr_inventory_overview` | | | ☐ |
| 19 | `dtr_inventory_project` | | | ☐ |
| 20 | `dtr_invoicing_discount` | | | ☐ |
| 21 | `dtr_invoicing_report` | | `od19_sales_reporting` | ☐ |
| 22 | `dtr_jasper` | | `od19_reporting_jasper` | ☐ |
| 23 | `dtr_jasper_auto_active` | | | ☐ |
| 24 | `dtr_landed_cost` | | `od19_stock_valuation_adjustment` | ☐ |
| 25 | `dtr_m2o_no_create` | | | ☐ |
| 26 | `dtr_partner_master` | | `od19_partner_thai_fields` | ☐ |
| 27 | `dtr_product_access_rules` | | | ☐ |
| 28 | `dtr_product_category` | | | ☐ |
| 29 | `dtr_product_master` | | | ☐ |
| 30 | `dtr_product_part_history` | | | ☐ |
| 31 | `dtr_project` | | `od19_project_enhanced` | ☐ |
| 32 | `dtr_report_base` | | `od19_reporting_jasper` | ☐ |
| 33 | `dtr_settings` | | | ☐ |
| 34 | `dtr_sql_command` | | | ☐ |
| 35 | `dtr_stock` | | `od19_stock_picking_features` | ☐ |
| 36 | `dtr_stock_adjustment` | | `od19_stock_valuation_adjustment` | ☐ |
| 37 | `dtr_stock_backdating` | | | ☐ |
| 38 | `dtr_stock_fifo` | | `od19_stock_fifo` | ☐ |
| 39 | `dtr_stock_form` | | | ☐ |

โฟลเดอร์ `c:\odoo-dev\Odoo15Backup\odoo\odoo15_mods_sales` (prefix `dtr_*`):

| # | โมดูลเดิม (Odoo 15) | ติดตั้งจริง? | mapping ไปยังโมดูล od19_* ปลายทาง | สถานะ mapping |
| --- | --- | --- | --- | --- |
| 1 | `dtr_access_right_sales` | | | ☐ |
| 2 | `dtr_crm_filter` | | | ☐ |
| 3 | `dtr_delivery_status` | | `od19_delivery_label` | ☐ |
| 4 | `dtr_document_sequence_group_sales` | | `od19_document_sequence` | ☐ |
| 5 | `dtr_erp_package_sales` | | | ☐ |
| 6 | `dtr_pricelists` | | | ☐ |
| 7 | `dtr_product_premium` | | | ☐ |
| 8 | `dtr_project_analysis` | | `od19_project_analytic` | ☐ |
| 9 | `dtr_project_analysis_tier_validation` | | | ☐ |
| 10 | `dtr_sale_tier_validation` | | | ☐ |
| 11 | `dtr_sales` | | `od19_sale_wizards` / `od19_sales_project_context` | ☐ |
| 12 | `dtr_sales_department` | | | ☐ |
| 13 | `dtr_sales_discount` | | | ☐ |
| 14 | `dtr_sales_exchange_rate` | | `od19_sales_currency_amount` | ☐ |
| 15 | `dtr_sales_exchange_rate_specific` | | | ☐ |
| 16 | `dtr_sales_filter` | | | ☐ |
| 17 | `dtr_sales_form` | | `od19_sale_terms` | ☐ |
| 18 | `dtr_sales_report` | | `od19_sales_reporting` | ☐ |
| 19 | `dtr_sales_revision` | | `od19_purchase_revision` (แนวทางเดียวกัน) | ☐ |
| 20 | `dtr_sales_warranty` | | `od19_service_warranty` | ☐ |

> หมายเหตุ: ไม่พบโมดูลที่ใช้ prefix `od15_autoinfo_*` ในระบบไฟล์จริง (โฟลเดอร์จริงใช้
> `autoinfo_*` และ `dtr_*`) — SQL จึงยังเผื่อ pattern `od15_autoinfo%` ไว้ด้วยเพื่อความครบถ้วน

### 1.3 รายชื่อโมดูลปลายทาง Odoo 19 (อ้างอิงสำหรับ mapping)

โมดูลเป้าหมายภายใต้ `c:\odoo-dev\odoo19\custom_addons` (เรียงตามชื่อ):

`od19_accounting_advance`, `od19_accounting_analytic_require`, `od19_accounting_cheque`,
`od19_accounting_dncn`, `od19_accounting_document_sequence`, `od19_accounting_features`,
`od19_accounting_money_in_report`, `od19_accounting_operational_closure`,
`od19_accounting_payment_fee`, `od19_accounting_petty_cash`, `od19_accounting_reporting`,
`od19_after_sales_reporting`, `od19_announcement`, `od19_apps_filter`, `od19_asset_disposal`,
`od19_asset_loan`, `od19_contacts_partner_roles`, `od19_currency_rate_bot`, `od19_dashboard`,
`od19_delivery_label`, `od19_document_sequence`, `od19_document_sign`, `od19_fleet_accounting`,
`od19_fleet_notification`, `od19_goods_issue`, `od19_helpdesk_extension`,
`od19_hr_attendance_zkteco`, `od19_hr_expense_enhanced`, `od19_hr_expense_thai`,
`od19_internal_issue`, `od19_inventory_audit_count`, `od19_inventory_execution_control`,
`od19_inventory_reporting`, `od19_iso_calibration`, `od19_iso_customer_satisfaction`,
`od19_iso_document_control`, `od19_iso_internal_audit`, `od19_iso_management_review`,
`od19_iso_nonconformity`, `od19_iso_risk`, `od19_iso_supplier_quality`, `od19_iso_training`,
`od19_knowledge_enhanced`, `od19_meeting_room_booking`, `od19_misc_features`,
`od19_notification_multi_channel`, `od19_partner_document_sequence`, `od19_partner_thai_fields`,
`od19_product_return`, `od19_project_analytic`, `od19_project_document_sequence`,
`od19_project_enhanced`, `od19_purchase_document_sequence`, `od19_purchase_procurement_core`,
`od19_purchase_request_extend`, `od19_purchase_revision`, `od19_purchase_terms`,
`od19_purchase_wizards`, `od19_quality_control`, `od19_quotation_document_sequence`,
`od19_reporting_jasper`, `od19_sale_terms`, `od19_sale_wizards`, `od19_sales_billing_evidence`,
`od19_sales_confirm_stamp`, `od19_sales_contract_core`, `od19_sales_currency_amount`,
`od19_sales_customer_risk_gate`, `od19_sales_oca_bridge_workflow`, `od19_sales_project_context`,
`od19_sales_reporting`, `od19_service_card`, `od19_service_warranty`, `od19_stock_fifo`,
`od19_stock_picking_features`, `od19_stock_valuation_adjustment`, `od19_thai_font_support`,
`od19_thai_localization_base`, `od19_thai_tax_reports`, `od19_transportation`,
`od19_user_guide_tours`, `od19_website`

> เกณฑ์ผ่าน Section 1: โมดูล custom ที่ติดตั้งจริงทั้งหมด (`[1.5]`) ต้องมี mapping ปลายทาง
> หรือมีบันทึกเหตุผลว่า "ไม่ยก" ครบทุกโมดูล

---

## Section 2 : ปริมาณข้อมูล (Row Counts)

รัน query `[2.1]`–`[2.6]` แล้วบันทึกผล (ค่าเป็นจริงที่อ่านได้ ไม่ใช่ตัวเลขคาดเดา)

### 2.1 Master data

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `res_company` | | |
| `res_users` | | |
| `res_partner` | | |
| `hr_department` | | |
| `hr_employee` | | |
| `product_category` | | |
| `product_template` | | |
| `product_product` | | |
| `product_supplierinfo` | | |
| `uom_uom` | | |
| `product_pricelist` | | |
| `product_pricelist_item` | | |

### 2.2 Accounting

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `account_account` | | |
| `account_journal` | | |
| `account_tax` | | |
| `account_payment_term` | | |
| `account_analytic_account` | | |
| `account_move` | | |
| `account_move_line` | | |

### 2.3 ขาย / ซื้อ

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `sale_order` | | |
| `sale_order_line` | | |
| `purchase_order` | | |
| `purchase_order_line` | | |

### 2.4 account_move แยกตาม move_type และ state (query `[2.4]`)

| move_type | draft | posted | cancel | รวม |
| --- | --- | --- | --- | --- |
| `entry` | | | | |
| `out_invoice` | | | | |
| `out_refund` | | | | |
| `in_invoice` | | | | |
| `in_refund` | | | | |
| `out_receipt` | | | | |
| `in_receipt` | | | | |

### 2.5 สต็อก / มูลค่าสต็อก

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `stock_quant` | | |
| `stock_move` | | |
| `stock_valuation_layer` | | |

### 2.6 โปรเจกต์ / ไฟล์แนบ

| ตาราง | จำนวนแถว | หมายเหตุ |
| --- | --- | --- |
| `project_project` | | |
| `ir_attachment` | | |

> เกณฑ์ผ่าน Section 2: ได้ตัวเลข baseline ครบทุกตารางที่ระบุ และบันทึกวันที่รัน/ผู้รัน

---

## Section 3 : คุณภาพข้อมูล (Data Quality) — ต้องแก้ก่อน import

รัน query `[3.1a]`–`[3.11b]` แล้วบันทึกจำนวนที่พบ + รายการที่ต้องแก้

| # | ประเด็นที่ตรวจ | Query | เกณฑ์ผ่าน (good) | จำนวนที่พบ | ต้องแก้ไข |
| --- | --- | --- | --- | --- | --- |
| 3.1 | partner นิติบุคคลที่ VAT ว่าง | `[3.1a]` | ใกล้ 0 หรือมีรายการยกเว้น | | ☐ |
| 3.2 | partner ที่ VAT ไม่ใช่ 13 หลัก | `[3.1b]` | 0 ก่อน import | | ☐ |
| 3.3 | partner ที่มีชื่อซ้ำ | `[3.2]` | 0 กลุ่ม หรือมี justification | | ☐ |
| 3.4 | partner `active=FALSE` ที่มียอดค้าง | `[3.3]` | 0 รายการค้างผูกกับ partner ปิดใช้งาน | | ☐ |
| 3.5 | product ที่ไม่มี `default_code` | `[3.4]` | 0 (เฉพาะ active) | | ☐ |
| 3.6 | product ที่มี UoM แปลก/ไม่มาตรฐาน | `[3.5]` | ทุก UoM เป็นหน่วยที่ตกลง | | ☐ |
| 3.7 | product ที่ราคาต้นทุนเป็น 0 (แต่มีสต็อก) | `[3.6]` | 0 สำหรับสินค้าที่มีสต็อก | | ☐ |
| 3.8 | สินค้าที่มีสต็อกติดลบ | `[3.7]` | 0 ก่อนทำ opening stock | | ☐ |
| 3.9 | บัญชีที่ `code` ซ้ำในบริษัทเดียว | `[3.8]` | 0 (unique ต่อ company) | | ☐ |
| 3.10 | ภาษีที่ rate ผิด | `[3.9]` | ไม่มี percent นอกเหนือ 0/7 ที่ไม่ได้รับอนุมัติ | | ☐ |
| 3.11 | เอกสารค้างเก่าเกิน 1 ปี (draft) | `[3.10a]` | ยกเลิก/ปิด หรือมีเอกสารอนุมัติ | | ☐ |
| 3.12 | เอกสาร posted ยังไม่ชำระ เกิน 1 ปี | `[3.10b]` | นับรวมในยอด AR/AP opening ครบ | | ☐ |
| 3.13 | attachment ที่ระเบียนไม่สมบูรณ์ | `[3.11b]` | 0 ระเบียนว่าง | | ☐ |
| 3.14 | attachment ที่ไฟล์หายจาก filestore | `[3.11a]` + ตรวจ filesystem | ไม่มีไฟล์หาย (ต้องตรวจที่ filesystem) | | ☐ |

> หมายเหตุ 3.14: SQL ตรวจได้เฉพาะ metadata (`store_fname`, `db_datas`, `file_size`)
> การยืนยันว่าไฟล์จริงหายจาก filestore ต้องตรวจที่ระดับ filesystem/`ir_attachment` store path

---

## Section 4 : ตัวเลข baseline ที่ต้อง tie หลัง import (Reconciliation Baseline)

> แก้ `DATE '2025-12-31'` ในไฟล์ SQL เป็นวันตัดยอดจริงก่อนรันทุก query ในส่วนนี้

| # | ตัวเลข baseline | Query ที่ใช้ | ค่าที่ได้ (baseline) | ค่าหลัง import | ผลต่าง | หมายเหตุ |
| --- | --- | --- | --- | --- | --- | --- |
| 4.1 | Trial Balance ณ วันตัดยอด (รายบัญชี) | `[4.1a]` | | | | |
| 4.2 | Trial Balance ยอดรวม (debit = credit) | `[4.1b]` | | | | debit ต้อง = credit |
| 4.3 | AR คงเหลือ แยกตาม partner | `[4.2]` | | | | |
| 4.4 | AR aging (not_due / 0–90 / >90) | `[4.2b]` | | | | |
| 4.5 | AP คงเหลือ แยกตาม partner | `[4.3]` | | | | |
| 4.6 | AP aging (not_due / 0–90 / >90) | `[4.3b]` | | | | |
| 4.7 | มูลค่าสต็อก + ปริมาณ แยกสินค้า | `[4.4a]` | | | | จาก valuation layer |
| 4.8 | ปริมาณคงเหลือจาก stock_quant | `[4.4b]` | | | | ต้องสอดคล้องกับ 4.7 |
| 4.9 | มูลค่าสต็อกรวมทั้งบริษัท | `[4.4c]` | | | | |
| 4.10 | ทะเบียนสินทรัพย์ + ค่าเสื่อมสะสม | `[5.1]` (optional) | | | | ต้องยืนยันโมดูล asset ก่อน |
| 4.11 | ยอด WHT ค้าง | `[5.2]` (optional) | | | | ตาราง custom — ยืนยันชื่อก่อน |
| 4.12 | เงินทดรองค้าง | `[5.3]` (optional) | | | | ตาราง custom — ยืนยันชื่อก่อน |
| 4.13 | เช็คค้างรับ/ค้างจ่าย | `[5.4]` (optional) | | | | ตาราง custom — ยืนยันชื่อก่อน |
| 4.14 | จำนวนเอกสารค้างทั้งหมด | `[4.9]` | | | | draft/posted-unpaid/SO/PO/project |

> ข้อควรระวัง: ตัวเลขในส่วน 4.10–4.13 อ้างถึงตารางที่ต้องยืนยันก่อนว่ามีอยู่ในฐานข้อมูลจริง
> (ดูส่วน Optional ในไฟล์ SQL และ `[5.0]`) ห้ามกรอกตัวเลขก่อนยืนยันว่าตารางมีอยู่จริง

---

## Section 5 : เกณฑ์ผ่าน/ไม่ผ่าน (Acceptance Gate) ของการ Profiling

การ Profiling ถือว่า "ผ่าน" เมื่อครบทุกข้อ:

- [ ] **G1 — ข้อมูลครบ:** รัน query ครบทุกข้อในส่วนที่ 0–4 และบันทึกผลในเอกสารนี้แล้ว
- [ ] **G2 — ตรวจเวอร์ชัน:** ยืนยันได้ว่าเป็น Odoo 15 (`base_version` ขึ้นต้น `15.`)
      และรันบนสำเนา `od15_stage` แบบ read-only เท่านั้น
- [ ] **G3 — Module inventory ครบ:** โมดูล custom ที่ติดตั้งจริงทุกตัวมี mapping ไปยัง `od19_*`
      หรือมีบันทึกเหตุผลว่า "ไม่ยก"
- [ ] **G4 — ไม่มี blocking data-quality issue:** ประเด็นใน Section 3 ที่เป็น blocking
      ถูกแก้แล้ว หรือมีแผนแก้ที่อนุมัติ ก่อนเริ่มขั้นตอน ETL / import
- [ ] **G5 — Baseline ถูกบันทึกและ sign-off:** ตัวเลข baseline ใน Section 4 ถูกบันทึกครบ
      และ **ลงนามรับรอง (sign-off) โดยฝ่ายบัญชี**
- [ ] **G6 — หลักฐานครบ:** มีไฟล์ `profiling_result.txt` และเอกสารนี้ที่กรอกผลครบแล้ว

| รายการ sign-off | ชื่อ | ตำแหน่ง | วันที่ | ลายเซ็น |
| --- | --- | --- | --- | --- |
| ผู้รัน Profiling | | | | |
| หัวหน้าฝ่ายบัญชี (baseline) | | | | |
| Migration lead | | | | |

---

## Section 6 : ตารางบันทึกผล (Result Log)

| วันที่รัน | ผู้รัน | Query / ส่วน | ผลลัพธ์ | ความผิดปกติที่พบ | การแก้ไข | สถานะ |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | ☐ |
| | | | | | | ☐ |
| | | | | | | ☐ |
| | | | | | | ☐ |
| | | | | | | ☐ |

---

## ภาคผนวก: ตาราง/คอลัมน์ที่ยืนยันกับ source Odoo 15 CE แล้ว

อ้างอิงจาก source ที่ `c:\odoo-dev\Odoo15Backup\odoo\odoo15`

| ตาราง/คอลัมน์ | ไฟล์:บรรทัด (evidence) | สถานะ |
| --- | --- | --- |
| `ir_module_module` (`name`, `latest_version`, `state`, `author`, `maintainer`) | `odoo/addons/base/models/ir_module.py:154,257,259,263,264,273,286` | ✅ ยืนยัน |
| `ir_config_parameter` (`key`, `value`) | `odoo/addons/base/models/ir_config_parameter.py:30,35,36` | ✅ ยืนยัน |
| `res_partner` (`vat`, `active`, `is_company`, `company_type`) | `odoo/addons/base/models/res_partner.py:134,172,181,209,213` | ✅ ยืนยัน |
| `ir_attachment` (`store_fname`, `db_datas`, `file_size`, `res_model`, `res_id`) | `odoo/addons/base/models/ir_attachment.py:39,384,385,387,403,404,405` | ✅ ยืนยัน |
| `account_account` (`code`, `internal_type`, `internal_group`, `user_type_id`) | `addons/account/models/account_account.py:36,61,64,66,67` | ✅ ยืนยัน |
| `account_account_type.type` ค่าคือ `other/receivable/payable/liquidity` | `addons/account/models/account_account.py:13-18` | ✅ ยืนยัน (Odoo 15 ใช้ค่าเหล่านี้ ไม่ใช่ `asset_receivable`/`liability_payable`) |
| `account_move` (`move_type`, `state`, `date`, `payment_state`, `amount_residual`) | `addons/account/models/account_move.py:160-176,185,239,256` | ✅ ยืนยัน |
| `account_move_line` (`move_id`, `date`, `parent_state`, `account_id`, `balance`, `amount_residual`, `full_reconcile_id`, `date_maturity`, `partner_id`) | `addons/account/models/account_move.py:3525-3646` | ✅ ยืนยัน (ไม่มีคอลัมน์ stored `account_type`/`internal_type` — ต้อง JOIN `account_account`) |
| `account_journal` (`code`, `type`, `company_id`) | `addons/account/models/account_journal.py:27,56,58,98` | ✅ ยืนยัน |
| `account_tax` (`amount`, `amount_type`, `type_tax_use`, `active`) | `addons/account/models/account_tax.py:62,72,75,87,95` | ✅ ยืนยัน |
| `account_payment_term` | `addons/account/models/account_payment_term.py:10` | ✅ ยืนยัน |
| `account_analytic_account` (`code`, `name`, `active`, `partner_id`) | `addons/analytic/models/analytic_account.py:58,126,127,128,137` | ✅ ยืนยัน |
| `product_template` (`type`, `detailed_type`, `categ_id`, `standard_price`, `uom_id`, `active`, `default_code`) | `addons/product/models/product_template.py:16,47,53,62,83,105,122,140` ; `type` ได้ `product` จาก `addons/stock/models/product.py:643` | ✅ ยืนยัน |
| `product_product` (`default_code`, `standard_price`, `product_tmpl_id`) | `addons/product/models/product.py:76,97,104,116` | ✅ ยืนยัน |
| `product_supplierinfo` (`min_qty`, `price`, `product_tmpl_id`) | `addons/product/models/product.py:800,820,823,838` | ✅ ยืนยัน |
| `product_category` | `addons/product/models/product.py:19` | ✅ ยืนยัน |
| `product_pricelist` / `product_pricelist_item` | `addons/product/models/product_pricelist.py:13,354` | ✅ ยืนยัน |
| `hr_department` (`name`, `active`, `company_id`) | `addons/hr/models/hr_department.py:9,15,17,18` | ✅ ยืนยัน |
| `hr_employee` (`active`, `company_id`) | `addons/hr/models/hr_employee.py:28,39,40` | ✅ ยืนยัน |
| `stock_quant` (`product_id`, `location_id`, `quantity`, `company_id`) | `addons/stock/models/stock_quant.py:17,53,63,64,79` | ✅ ยืนยัน |
| `stock_move` (`product_qty`, `location_id`, `state`) | `addons/stock/models/stock_move.py:21,51,73,96` | ✅ ยืนยัน |
| `stock_valuation_layer` (`product_id`, `quantity`, `value`, `remaining_qty`, `remaining_value`) | `addons/stock_account/models/stock_valuation_layer.py:10,17,20,24,25,26` | ✅ ยืนยัน |
| `sale_order.state` = `draft/sent/sale/done/cancel` | `addons/sale/models/sale_order.py:168-174` | ✅ ยืนยัน |
| `purchase_order` (`state` = `draft/sent/to approve/purchase/done/cancel`) | `addons/purchase/models/purchase.py:22,99-106` | ✅ ยืนยัน |
| `project_project` (`name`, `active`, `company_id`, `analytic_account_id`) | `addons/project/models/project.py:177,269,271,282,284` | ✅ ยืนยัน |
| `account_asset` / ตาราง asset | ไม่พบใน source Odoo 15 CE (`addons`, `odoo/addons`) | ⚠️ ต้องยืนยัน (enterprise/OCA) |
| `dtr_wht`, `dtr_account_prepayment`, cheque ฯลฯ | เป็นโมดูล custom — ไม่มีใน core | ⚠️ ต้องยืนยันจาก `ir_module_module` + `information_schema` (`[5.0]`) |
