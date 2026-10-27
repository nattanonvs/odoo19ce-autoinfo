# Thai Accounting Compliance Gap — ตารางเทียบข้อบังคับบัญชี/ภาษีไทย

## Document Control

| Field | Value |
| --- | --- |
| Artifact | Thai accounting & tax regulatory compliance gap analysis |
| Program | Odoo 19 CE Program |
| สร้างเมื่อ | 2026-10-27 |
| ปรับปรุงล่าสุด | 2026-10-27 (Wave 2A ติดตั้งสำเร็จ · Wave 2B ปิดช่อง VAT สำเร็จ) |
| ตรวจจาก | สภาพจริงบนดิสก์ (`custom_addons/`, `third_party/oca/`, core `addons/l10n_th`), สถานะโมดูลใน DB `odoo19_pdev`, `odoo.conf`, และงานวิจัยกฎหมายไทย (ยืนยันซ้ำด้วยการค้นเว็บ) |
| มุมมอง | **ข้อบังคับ/กฎหมาย** (ต่างจาก `accounting-requirements-coverage.md` ที่เป็นมุม "requirement checklist ของฝ่ายบัญชี") |
| ผู้จัดทำ | ทีมเทคนิค |
| ผู้รับ | ฝ่ายบัญชี / Audit / เจ้าของธุรกิจ |

สัญลักษณ์: ✅ ครอบคลุมแล้ว · 🟡 ครอบคลุมบางส่วน หรือแนวทางต่างแต่ได้ผลเทียบเท่า · 🔴 ยังไม่ครอบคลุม

## 1. สรุปผู้บริหาร

- ระบบบัญชี Odoo 19 ปัจจุบันมี **ฐาน Thai localization ที่แข็งแรง**: core `l10n_th` มีรายงาน ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 ในตัว และ OCA `l10n_th_account_tax` จัดการ VAT + WHT + หนังสือรับรอง 50 ทวิ
- เมื่อเทียบกับ **ข้อบังคับ/กฎหมายไทย** พบช่องว่างที่ยังไม่มี (🔴) เหลือ 4 กลุ่ม หลังปิดหมวด VAT ครบใน Wave 2B แล้ว:
  1. **ภาษีเงินได้นิติบุคคล ภ.ง.ด.50 / ภ.ง.ด.51**
  2. **ภาษีเงินได้รอตัดบัญชี TAS 12**
  3. **การยื่นงบการเงิน DBD (ส.บช.3) / retention 5 ปี**
  4. **ภาษีอื่น: ภ.ธ.40 (SBT) และอากรแสตมป์ / e-Stamp**
- พร้อมกันนั้น **Wave 2A ติดตั้งสำเร็จแล้ว (2026-10-27)** — OCA 12 โมดูล state = `installed` บน `odoo19_pdev` แล้ว ซึ่งปิดช่องว่างด้านรายงานการเงิน/การควบคุมภายในได้ทันที — ได้แก่ `account_financial_report`, `account_tax_balance`, `partner_statement`, `account_reconcile_oca` (+`account_statement_base`), `auditlog`, `account_move_tier_validation` (+`base_tier_validation_formula`), `account_check_deposit`, `account_billing`, `account_journal_lock_date`, `date_range`
- **Wave 2B ปิดช่อง VAT ครบแล้ว (2026-10-27)** — custom module `od19_thai_tax_reports` v19.0.1.5.0 ครอบคลุม ม.82/5 ภาษีซื้อต้องห้าม, ม.83/6 Reverse charge ภ.พ.36, ม.86/4 validate 8 รายการ, ม.86/6 ใบกำกับภาษีอย่างย่อ และ ม.86/9-10 ใบเพิ่มหนี้/ใบลดหนี้ (unit tests ของโมดูลผ่าน 39 รายการ, 0 failed)
- **ข้อเสนอ**: Wave 2A ✅ และ Wave 2B ✅ ปิดแล้ว; ขั้นถัดไปคือ Wave 2C (ภ.ง.ด.54 + e-Tax Invoice ให้สมบูรณ์)

## 2. สิ่งที่ระบบมีวันนี้ (As-Is)

### 2.1 โมดูลบัญชีที่ติดตั้งใช้งานจริงใน `odoo19_pdev`

| กลุ่ม | โมดูล | บทบาท |
| --- | --- | --- |
| Core Odoo 19 | `account`, `account_payment`, `account_asset_management`, `account_fiscal_year` | บัญชีแกนหลัก + สินทรัพย์ถาวร + ปีบัญชี |
| Core Thai | `l10n_th` | ผังบัญชีไทย + ภาษีไทย + **รายงาน ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53** (account.report engine) |
| OCA Thai | `l10n_th_account_tax` | VAT + WHT บนบรรทัดใบแจ้งหนี้ + `withholding.tax.cert` (50 ทวิ) + `account.move.tax.invoice` (`tax_invoice_number`/`tax_invoice_date`) |
| OCA Finance Tools | `account_lock_date_update`, `account_move_name_sequence` | ล็อกงวดบัญชี + รันเลขที่เอกสารไม่มีช่องว่าง |
| OCA (Wave 2A, 2026-10-27) | `account_financial_report`(+`date_range`), `account_tax_balance`, `partner_statement`, `account_reconcile_oca`(+`account_statement_base`), `auditlog`, `account_move_tier_validation`(+`base_tier_validation_formula`), `account_check_deposit`, `account_billing`, `account_journal_lock_date` | รายงานการเงิน + กระทบยอด VAT/ธนาคาร + AR/AP statement + Audit Trail + อนุมัติหลายชั้น + เช็ครับ + จัดกลุ่มใบแจ้งหนี้ + ล็อกงวดสมุดรายวัน |
| OCA | `base_tier_validation`, `currency_rate_update`, `report_xlsx` | อนุมัติหลายชั้น + เรต + Excel export |
| Custom od19 | `od19_thai_localization_base`, `od19_partner_thai_fields`, `od19_thai_font_support` | ฐานไทย + ที่อยู่ไทย (อำเภอ/ตำบล/รหัสไปรษณีย์) + ฟอนต์ |
| Custom od19 | `od19_accounting_features`, `od19_thai_tax_reports`, `od19_etax_invoice` | ฟีเจอร์บัญชี + ทะเบียน VAT/WHT + e-Tax Invoice |
| Custom od19 | `od19_asset_disposal`, `od19_asset_loan` | จำหน่าย/ให้ยืมสินทรัพย์ |

### 2.2 จุดแข็งที่ยืนยันจากโค้ด

- **ใบกำกับภาษีขาย**: core `l10n_th` override หัวเอกสารเป็น "Tax Invoice" + แสดง `l10n_th_branch_name` (สาขา)
- **รายงาน ภ.พ.30**: มีโครงครบ (ภาษีขายข้อ 1-5, ภาษีซื้อข้อ 6-7, VAT ข้อ 8-12 + ยกยอด) เป็น `account.report`
- **WHT**: มี `withholding.tax.cert` + `account.move.tax.invoice` + PIT rate data
- **ล็อกงวด + รันเลขที่**: ติดตั้งแล้วทั้งคู่

## 3. Gap Analysis — ข้อบังคับไทย vs ความครอบคลุม

### หมวด A: กฎหมายแม่บท / DBD / การเก็บรักษาเอกสาร

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| พ.ร.บ.การบัญชี 2543 ม.14 | เก็บรักษาสมุดบัญชี/เอกสาร **5 ปี** | 🟡 | มี DB เก็บถาวร แต่ไม่มีกลไก retention policy / ห้ามลบชัดเจน |
| พ.ร.บ.การบัญชี 2543 ม.11 | งบการเงินรายปี + ยื่น DBD **150 วัน** | 🔴 | ไม่มีงบการเงินตามแบบ ส.บช.3 และไม่มีชุดยื่น DBD |
| พ.ร.บ.การบัญชี 2543 ม.17 | งบการเงินต้องมีผู้สอบบัญชีรับรอง (บางประเภท) | 🔴 | ไม่รองรับสายงานผู้สอบบัญชี |

### หมวด B: ภาษีมูลค่าเพิ่ม (VAT)

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ม.86/4 | ใบกำกับภาษีเต็มรูป **8 รายการ** | ✅ | validation 8 รายการก่อน post เมื่อผู้ซื้อมีเลขภาษี (บังคับ/ปิดได้ผ่าน `res.company.od19_enforce_86_4_validation`) + ฟิลด์ `od19_tax_invoice_doc_type` |
| ม.86/6 | ใบกำกับอย่างย่อ | ✅ | รายงาน `od19_thai_tax_reports.abbreviated_tax_invoice_document` สำหรับขายปลีก (ผู้ซื้อไม่มีเลขภาษี) |
| ม.86/9-10 | ใบเพิ่มหนี้ / ใบลดหนี้ | ✅ | ผูกประเภทเอกสาร (ใบเพิ่มหนี้/ใบลดหนี้) + อ้างอิงเลขที่/วันที่ใบกำกับภาษีเดิม + เหตุผล บนรายงานใบกำกับภาษี |
| ภ.พ.30 | ยื่น VAT รายเดือน (15 ของเดือนถัดไป) | ✅ | core `l10n_th` tax_report + od19 register |
| ม.82/5 | **ภาษีซื้อต้องห้าม** (หักไม่ได้) | ✅ | ฟิลด์ `od19_vat_deductible` บน `account.move.line` + ภาษีซื้อต้องห้าม + แยกยอดในทะเบียนภาษีซื้อ |
| ม.83/6 | **Reverse charge ภ.พ.36** (ซื้อบริการต่างประเทศ) | ✅ | ภาษี reverse charge (self-assess ขาย+ซื้อ) + รายงาน ภ.พ.36 |
| ม.83/5 | ขายยกเว้น VAT | ✅ | core จัดการ exempt |

### หมวด C: ภาษีหัก ณ ที่จ่าย (WHT)

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ภ.ง.ด.1 / 2 / 3 | หักจากเงินเดือน/บุคคล/นิติบุคคล | ✅ | OCA personal_income_tax + core `tax_report_pnd3` |
| ภ.ง.ด.53 | ยื่น **7 วัน** (e-Filing +8 = 15 วัน) | ✅ | core `tax_report_pnd53` |
| ภ.ง.ด.54 | นำส่งภาษีให้ราชการ/องค์กร | 🟡 | ไม่มี report เฉพาะ |
| ม.50 ทวิ | หนังสือรับรองการหักภาษี **2 ฉบับ** (ม.40(1)(2) ภายใน 15 ก.พ. ปีถัดไป) | ✅ | OCA `withholding.tax.cert` |
| e-Withholding Tax | นำส่งอิเล็กทรอนิกส์ผ่านธนาคาร | 🔴 | ไม่มี integration |

### หมวด D: ภาษีเงินได้นิติบุคคล

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ภ.ง.ด.50 | ยื่นประจำปีภายใน 150 วัน | 🔴 | ไม่มี |
| ภ.ง.ด.51 | ยื่นครึ่งปี (ประมาณการ) ภายใน 2 เดือน | 🔴 | ไม่มี |
| TAS 12 | ภาษีเงินได้รอตัดบัญชี (deferred tax) | 🔴 | ไม่มีทั้งการคำนวณและรายงาน |

### หมวด E: e-Tax Invoice

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ระเบียบกรมสรรพากร พ.ศ. 2560 | e-Tax Invoice / e-Receipt | 🟡 | `od19_etax_invoice` มีโครง XML + sign (lxml/signxml/cryptography) แต่ต้องยืนยัน XAdES + ลงนาม PDF/A-3 |
| ขมธอ.3-2560 (ETDA) | มาตรฐาน XML + ลายมือชื่อดิจิทัล | 🟡 | มี mapping บางส่วน ต้องตรวจ schema ฉบับเต็ม |
| การนำส่งให้สรรพากร | Upload ผ่านระบบ RD | 🔴 | ไม่มี integration ยื่นสรรพากร |

### หมวด F: ภาษีอื่น

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| ภ.ธ.40 | ภาษีธุรกิจเฉพาะ (SBT) | 🔴 | ไม่มี |
| อากรแสตมป์ / e-Stamp | อากรแสตมป์ + นำส่งอิเล็กทรอนิกส์ | 🔴 | ไม่มี |

### หมวด G: รายงานการเงิน / การปิดงบ

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| TFRS for NPAEs | งบการเงินตามมาตรฐาน | 🟡 | มี GL แต่ไม่มี template งบตามแบบ NPAE |
| งบทดลอง / กำไรขาดทุน / งบดุล / กระแสเงินสด | รายงานมาตรฐาน | ✅ | `account_financial_report` (OCA) **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| กระทบยอดธนาคาร | Monthly recon | ✅ | `account_reconcile_oca` + `account_statement_base` **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| ปิดงวดบัญชี | ล็อกงวด | ✅ | `account_lock_date_update` ติดตั้งแล้ว + `account_journal_lock_date` **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |

### หมวด H: การควบคุมภายใน / Audit Trail

| ข้อบังคับ | สิ่งที่กฎหมายกำหนด | สถานะ | ช่องว่าง |
| --- | --- | --- | --- |
| Audit Trail | ISO 9001 + การตรวจสอบย้อนกลับ | ✅ | `auditlog` (OCA) **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| อนุมัติหลายชั้นบัญชี | Separation of Duties | ✅ | `base_tier_validation` + `account_move_tier_validation` (+`base_tier_validation_formula`) **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |
| เช็ค | ระบบเช็ครับ/จ่าย | ✅ | `account_check_deposit` **ติดตั้งแล้ว 2026-10-27** (Wave 2A) |

## 4. แผนพัฒนา (ปิดช่องว่างตาม Wave)

### Wave 2A — Quick Win: เปิดใช้ OCA ที่มีอยู่แล้ว ✅ (ปิดแล้ว 2026-10-27)
**เป้าหมาย**: ได้รายงานการเงิน + การควบคุมภายใน + เครื่องมือเช็ค/จัดกลุ่ม โดยไม่ต้องเขียนโค้ดใหม่ (ความเสี่ยงต่ำ)

**ผลการติดตั้ง**: 12 โมดูล state = `installed` บน `odoo19_pdev` (ตรวจด้วย psql 2026-10-27) และ Odoo โหลดผ่านทุกโมดูลใน log (`Loading module account_billing (265/274)` → `account_check_deposit (266/274)` → `account_reconcile_oca (274/274)`)

| # | โมดูล | Repo | ปิดช่องว่าง | สถานะ |
| --- | --- | --- | --- | --- |
| 1 | `account_financial_report` | account-financial-reporting | หมวด G — TB / GL / BS / P&L | ✅ installed |
| 2 | `account_tax_balance` | account-financial-reporting | หมวด B — กระทบยอด VAT | ✅ installed |
| 3 | `partner_statement` | account-financial-reporting | AR/AP statement | ✅ installed |
| 4 | `account_reconcile_oca` (+`account_statement_base`) | account-reconcile | หมวด G — bank reconciliation | ✅ installed |
| 5 | `auditlog` | server-tools | หมวด H — Audit Trail (ISO 9001) | ✅ installed |
| 6 | `account_move_tier_validation` (+`base_tier_validation_formula`) | tier-validation | หมวด H — อนุมัติหลายชั้น | ✅ installed |
| 7 | `account_check_deposit` | account-financial-tools | หมวด H — เช็ครับ | ✅ installed |
| 8 | `account_billing` | account-invoicing | จัดกลุ่มใบแจ้งหนี้ก่อนจ่าย | ✅ installed |
| 9 | `account_journal_lock_date` | account-financial-tools | ล็อกงวดระดับสมุดรายวัน | ✅ installed |
| — | `date_range` | server-ux | dependency ของ `account_financial_report` | ✅ installed |

### Wave 2B — ปิดช่อง VAT (สรรพากรบังคับ) ✅ (ปิดแล้ว 2026-10-27)
**เป้าหมาย**: ปิดช่องว่างภาษีมูลค่าเพิ่มที่สรรพากรบังคับ ภายในโมดูล custom `od19_thai_tax_reports` v19.0.1.5.0

**ผลการดำเนินการ**: unit tests ของโมดูลผ่าน **39 รายการ (0 failed, 0 error)** บน `odoo19_pdev`

| รายการ | สิ่งที่ทำ | ไฟล์/กลไก |
| --- | --- | --- |
| ม.82/5 ภาษีซื้อต้องห้าม | ฟิลด์ `od19_vat_deductible` บน `account.move.line` + ภาษี "ภาษีซื้อต้องห้าม" + แยกยอดในทะเบียนภาษีซื้อ | `models/account_move_line.py`, `data/od19_vat_non_deductible_data.xml`, `report/vat_purchase_register.*` |
| ม.83/6 Reverse charge ภ.พ.36 | ภาษี reverse charge (repartition factor < 0 = self-assess ภาษีขาย + ภาษีซื้อ) + รายงาน ภ.พ.36 | `models/account_tax.py`, `data/od19_reverse_charge_data.xml`, `report/pp36_register.*` |
| ม.86/4 validate 8 รายการ | ตรวจความครบถ้วน 8 รายการก่อน post (เฉพาะเมื่อผู้ซื้อมีเลขภาษี) — เปิด/ปิดผ่าน `res.company.od19_enforce_86_4_validation` | `models/account_move.py`, `models/res_company.py`, `models/res_config_settings.py` |
| ม.86/6 ใบกำกับอย่างย่อ | รายงาน Abbreviated Tax Invoice สำหรับขายปลีก | `report/tax_invoice_forms.xml` |
| ม.86/9-10 ใบเพิ่มหนี้/ใบลดหนี้ | ฟิลด์ `od19_tax_invoice_doc_type` + block "อ้างอิงใบกำกับภาษีเดิม/เหตุผล" บนรายงานใบกำกับภาษี | `models/account_move.py`, `report/tax_invoice_forms.xml` |

### Wave 2C — WHT + e-Tax ให้สมบูรณ์
- **ภ.ง.ด.54** report เฉพาะ
- **e-Tax Invoice**: XML ตรง ขมธอ.3-2560 ครบทุก Document Family + XAdES + PDF/A-3 + ช่องทางยื่น RD
- **e-Withholding Tax**: integration นำส่งผ่านธนาคาร

### Wave 3 — ภาษีเงินได้นิติบุคคล + มาตรฐานบัญชี
- **ภ.ง.ด.50 / ภ.ง.ด.51**: รายงาน + ประมาณการ
- **TAS 12 Deferred Tax**: คำนวณผลต่างชั่วคราว + รายงาน
- **TFRS for NPAEs template**: งบการเงินตามแบบ NPAE

### Wave 4 — ภาษีอื่น + การยื่นราชการ
- **ภ.ธ.40 SBT** (กรณีเข้าข่ายธุรกิจเฉพาะ)
- **อากรแสตมป์ / e-Stamp**
- **ส.บช.3 / ยื่นงบ DBD 150 วัน** + retention policy 5 ปี

## 5. ลำดับความสำคัญเชิงธุรกิจ (Criticality)

| ระดับ | รายการ | เหตุผล |
| --- | --- | --- |
| 🔴 วิกฤต (สรรพากร) | ม.82/5, ภ.พ.36, ภ.ง.ด.50/51, e-Tax | ฝ่าฝืนมีโทษ/เบี้ยปรับ |
| 🟠 สูง (Governance) | auditlog, tier validation, lock date สมบูรณ์ | ISO 9001 + Separation of Duties |
| 🟡 กลาง (มาตรฐาน) | TAS 12, NPAEs, ส.บช.3 | ต้องใช้ตอนปิดงบ/ส่งผู้สอบ |
| 🟢 ต่ำ (เฉพาะกิจ) | SBT, อากรแสตมป์, ภ.ง.ด.54 | ขึ้นกับประเภทธุรกิจ |

## 6. การเชื่อมโยงเอกสาร

| เอกสาร | ความสัมพันธ์ |
| --- | --- |
| `accounting-requirements-coverage.md` | มุม "ข้อกำหนดฝ่ายบัญชี" (requirement checklist) — เอกสารนี้เป็นมุม "ข้อบังคับกฎหมาย" เสริมกัน |
| `domain-wave-matrix.md` | Wave 2 Focus ระบุ finance controls ที่สอดคล้องกับแผนในข้อ 4 |
| `2026-10-21-odoo19-enterprise-wave-2-custom-finance-controls.md` | Wave 2 child spec — งาน Wave 2A/2B/2C ควรอัปเดตในเอกสารนี้ |
