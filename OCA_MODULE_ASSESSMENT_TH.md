# การประเมินโมดูล OCA — Odoo 19 CE (`odoo19`)

**บทบาท:** สถาปนิกเทคนิค Odoo อาวุโส / ผู้ตรวจสอบโมดูล OCA
**ขอบเขต:** วิเคราะห์และให้ข้อเสนอแนะเท่านั้น — **ไม่มีการติดตั้ง อัปเกรด ถอน หรือรันโมดูลใด ๆ**
**แหล่งหลักฐาน:** `odoo.conf`, `.gitmodules`, `custom_addons/*`, manifest ใน `third_party/oca/*`, เอกสารกำกับดูแลใน `docs/superpowers/**`, `OCA_MODULE_MATCHING.md`, `GAP_ANALYSIS_OD15_to_OD19.md`
**วันที่ประเมิน:** 2026-10-15

> ⚠️ **สถานะ (อัปเดต 2026-10-19):** เอกสารนี้เป็น *การประเมินและข้อเสนอแนะ* ณ 2026-10-15 (ก่อนดำเนินการจริง)
> สำหรับสถานะส่งมอบล่าสุด ให้ยึด [GAP_ANALYSIS_OD15_to_OD19.md](GAP_ANALYSIS_OD15_to_OD19.md) (หัวข้อ "สถานะจริง ณ 2026-10-19")
> และผลการติดตั้งชุดเต็ม 251 โมดูล (custom 79 + OCA + core) ที่ผ่านความสะอาดของ log เมื่อ 2026-10-19

> หมายเหตุด้านความเข้ากันได้: โมดูล OCA ที่อ้างถึงทั้งหมดได้รับการตรวจสอบว่า **ประกาศเวอร์ชัน `19.0.x` ใน manifest บน branch `19.0`** (ตรวจ 291 manifest) นี่เป็นการตรวจสอบ **ระดับ manifest เท่านั้น** **ไม่ใช่** การพิสูจน์ว่าทำงานได้จริงในระดับรันไทม์ จุดที่ยืนยันพฤติกรรมรันไทม์ไม่ได้ จะระบุว่า **COMPATIBILITY NOT VERIFIED (runtime)**

---

# เฟส 1 — การวิเคราะห์ระบบปัจจุบัน

## 1.1 ข้อเท็จจริงของแพลตฟอร์ม

| รายการ | ผลที่พบ |
| --- | --- |
| เวอร์ชัน Odoo | 19.0 (Community Edition) |
| อนุกรมสคีมาฐานข้อมูล | 19.0.1.3 |
| ฐานข้อมูล | `odoo19` (PostgreSQL 16.15), `dbfilter = ^odoo19$` |
| Edition | **Community (CE)** — ไม่มีโมดูล Enterprise |
| HTTP | Nginx 1.27.2 → `http_port = 8070`, `gevent_port = 8072`, `proxy_mode = True` |
| URL สาธารณะ | `https://pdev-erp.auto-info.com` (Cloudflare Flexible SSL + DDNS) |
| OS | Windows (Local/Pre-UAT); Linux `/var/odoo` (เป้าหมายเซิร์ฟเวอร์) |
| Workers | `workers = 0` (ปิดโหมด multi-process) |
| Cron threads | `max_cron_threads = 2` |
| Memory guard | soft 2 GB / hard 2.5 GB |
| Time guard | `limit_time_real = 120`, `limit_time_cpu = 60` |
| Logging | `log_level = info`, `logfile = C:\odoo-dev\odoo19\odoo_server.log` |
| DB manager | `list_db = True` ⚠️ |
| Secrets | พบ `db_password` ใน `odoo.conf`; `admin_passwd` แฮชแล้ว (pbkdf2) ⚠️ |

## 1.2 สถาปัตยกรรม Addon

- `addons_path` (พาธสัมบูรณ์ คั่นด้วยจุลภาค): `addons` ของ Odoo core, `custom_addons` และ **OCA Git submodules 13 รายการ** ใต้ `third_party/oca`
- Repository ของ OCA (ทั้งหมด branch `19.0`): `l10n-thailand`, `sale-blanket`, `sale-workflow`, `server-backend`, `server-tools`, `server-ux`, `helpdesk`, `account-financial-tools`, `purchase-workflow`, `tier-validation`, `reporting-engine`, `knowledge`, `website`
- **โมดูลกำหนดเอง:** ประมาณ 80 โมดูลใต้ `custom_addons` นำหน้าด้วย `od19_*`
- **โมดูลที่ติดตั้งแล้ว:** ประมาณ 234 (custom + OCA บางส่วน + core)

## 1.3 OCA ที่ติดตั้งแล้ว (มีอยู่แล้ว — อย่าเสนอเป็น "ของใหม่")

`base_user_role`, `base_exception`, `base_revision`, `base_tier_validation`, `purchase_request_tier_validation`, `sale_blanket_order`, `sale_delivery_state` (sale_stock_delivery_state), `sale_exception`, `sale_order_revision`, `sale_company_currency`, `account_asset_management`, `account_fiscal_year`, `l10n_th_account_tax`, `l10n_th_amount_to_text`, `l10n_th_base_sequence`, `l10n_th_base_utils`, `helpdesk_mgmt`, `helpdesk_mgmt_project`, `helpdesk_product`, `purchase_request`, `report_xlsx`, `report_xlsx_helper`, `document_knowledge`, `document_page`

## 1.4 สถาปัตยกรรมความปลอดภัย / สิทธิ์การเข้าถึง

- **กลุ่มตามบทบาท** ผ่าน `base_user_role` (เป็นพื้นฐานที่ดี)
- **ความปลอดภัยระดับทีม** ในโมดูล helpdesk ที่ขยายเอง (`od19_helpdesk_extension`, `od19_internal_issue`) โดยใช้ group + record rules ใน `security/*.xml`
- **โมดูลควบคุม ISO** (9 โมดูล) พร้อมลำดับเอกสารแยกตามแผนก
- **ไม่มีบันทึกการตรวจสอบระดับเรกคอร์ด (audit trail)** — `auditlog` มีอยู่ใน repo แต่ **ยังไม่ติดตั้ง**
- **ไม่มีประวัติการเปลี่ยนสิทธิ์ผู้ใช้/บทบาท** — `base_user_role_history` มีแต่ยังไม่ติดตั้ง
- **ไม่มีข้อจำกัดการ export** — `base_export_manager` มีแต่ยังไม่ติดตั้ง
- **DB manager เปิดเผย** (`list_db = True`)
- **Secrets อยู่ในไฟล์ config** (`db_password`)

## 1.5 กลไกรายงาน (Reporting)

- QWeb PDF + XLSX ของ Odoo (`report_xlsx`, `report_xlsx_helper` ติดตั้งแล้ว)
- สะพาน Jasper กำหนดเอง (`od19_reporting_jasper`), รายงานภาษีไทย (`od19_thai_tax_reports`), รายงาน WHT, รายงาน payment voucher และโมดูลรายงานอย่างเดียวอีกจำนวนมาก
- **ไม่มีชั้นรายงาน SQL ที่ผู้ใช้กำหนดเองได้** (`bi_sql_editor` / `sql_request_abstract` มีแต่ยังไม่ติดตั้ง)
- **ไม่มีพารามิเตอร์รายงาน** (`report_qweb_parameter` ยังไม่ติดตั้ง)

## 1.6 การมอนิเตอร์ / ล็อก / ระบบอัตโนมัติ

- ล็อกเป็นไฟล์อย่างเดียวที่ระดับ `info`; **ไม่ได้ตั้งค่า log rotation** ใน Odoo
- **ไม่มีการมอนิเตอร์ข้อผิดพลาด** (`sentry` ยังไม่ติดตั้ง)
- **ไม่มีการแจ้งเตือนเมื่อ cron ล้มเหลว** (`scheduler_error_mailer` ยังไม่ติดตั้ง)
- **ไม่มีการสำรองข้อมูลอัตโนมัติ** (`auto_backup` ยังไม่ติดตั้ง) — ขณะที่ baseline ความพร้อมใช้งานจริงกำหนดให้ต้องมีหลักฐาน backup + restore ก่อน go-live
- มีระบบอัตโนมัติผ่าน scheduled/server actions ของ Odoo และเอกสาร discovery ระบุว่าเป็น **จุดเสี่ยงที่รู้อยู่แล้ว**

## 1.7 จุดอ่อนที่พบ (ผลลัพธ์เฟส 1)

**ประสิทธิภาพ (Performance)**
- `workers = 0` → ไม่มีการสเกลแบบ worker/multi-process; request ที่ใช้เวลานานจะบล็อก loop แบบ threaded นี่คือข้อจำกัดการสเกลที่ใหญ่ที่สุดสำหรับ ERP หลายผู้ใช้
- ไม่ได้ตั้ง `limit_request` (ค่าเริ่มต้น 8192) → เสี่ยง request ที่อายุยืนรั่วหน่วยความจำในโหมด worker
- ไม่มี log rotation → ไฟล์ล็อกโตไม่จำกัดทั้งบน Windows และ Linux
- ไม่ควบคุม cron ซ้อนทับ (มี 2 cron threads; ไม่มี guard กันซ้อน)

**ความซ้ำซ้อน / การบำรุงรักษา**
- โมดูลออกเลขเอกสารใกล้เคียงกัน 6 ตัว: `od19_document_sequence`, `od19_accounting_document_sequence`, `od19_quotation_document_sequence`, `od19_purchase_document_sequence`, `od19_project_document_sequence`, `od19_partner_document_sequence`
- `od19_misc_features` เป็นโมดูลรวมของหลายอย่าง (logo ISO, sequence guard, data link, runtime guard, รายงานลูกค้าซื้อซ้ำ) — ผิดหลัก cohesion
- หลายโมดูลดูเหมือนเป็น **โครงร่างเปล่า หรือ report-only** ที่ `models/`/`report/`/`wizard/` มีแต่ `__init__.py` ว่าง (เช่น `od19_accounting_reporting`, `od19_accounting_money_in_report`, `od19_service_card`; ส่วน `od19_accounting_payment_voucher_reports` เป็น report-only ตามดีไซน์) **ต้องตรวจสอบก่อนถือว่าทำงานได้**

**การควบคุมที่ขาดหาย**
- ไม่มี audit trail สำหรับการเขียน/ลบ, ไม่มีประวัติการเปลี่ยนสิทธิ์, ไม่มีการควบคุมการ export
- ไม่มีเครื่องมือจัดระเบียบ/ลบ object ขยะใน DB
- ไม่มีการจัดการ/มองเห็น session (ใครล็อกอินอยู่ที่ไหน)

**จุดอ่อนด้านความปลอดภัย**
- `list_db = True` เปิดช่อง endpoint ของ database manager
- รหัสผ่าน DB เก็บในไฟล์ config แบบข้อความธรรมดา; ต้องยืนยันว่าไม่ถูก commit เข้า VCS
- ไม่มีการบังคับ dbfilter ที่ระดับ proxy (`dbfilter_from_header`) แม้ใช้ Nginx + Cloudflare
- ไม่มีข้อจำกัด "technical user" สำหรับบัญชี service

**ช่องว่างด้านการสังเกตระบบ (Observability)**
- ไม่มีการเก็บข้อผิดพลาดแบบรวมศูนย์, ไม่มีการแจ้งเตือน cron ล้มเหลว, ไม่มีหน้าสืบค้น audit

**ความเสี่ยงด้านคุณภาพข้อมูล**
- การออกเลขเอกสารตามปีและรหัสอ้างอิงคู่ค้าเป็นแบบกำหนดเอง; หากไม่มี audit trail การแก้ไขย้อนหลังจะมองไม่เห็น

---

# เฟส 2 — การค้นหาโมดูล OCA (จำแนกหมวด)

โมดูลทั้งหมดด้านล่างมีอยู่ใน submodule `third_party/oca` ที่ pin ไว้ (branch 19.0) โดยคอลัมน์ "ติดตั้งแล้ว" หมายถึงโมดูลที่ใช้งานอยู่แล้ว

| # | หมวด | ชื่อเทคนิค | Repo | ติดตั้งแล้ว |
| --- | --- | --- | --- | --- |
| 1 | B Monitoring | `auditlog` | server-tools | ไม่ |
| 2 | B Monitoring | `sentry` | server-tools | ไม่ |
| 3 | B Monitoring | `scheduler_error_mailer` | server-tools | ไม่ |
| 4 | D Prevention | `auto_backup` | server-tools | ไม่ |
| 5 | C Troubleshooting | `database_cleanup` | server-tools | ไม่ |
| 6 | A/D Performance/Prevention | `base_cron_exclusion` | server-tools | ไม่ |
| 7 | G Security | `base_export_manager` | server-ux | ไม่ |
| 8 | C/G Troubleshooting/Security | `session_db` | server-tools | ไม่ |
| 9 | F Reporting | `bi_sql_editor` (+`sql_request_abstract`) | reporting-engine | ไม่ |
| 10 | F Reporting | `date_range` (+`date_range_account`) | server-ux | ไม่ |
| 11 | F Reporting | `report_qweb_parameter` | reporting-engine | ไม่ |
| 12 | E/F Workflow/Reporting | `base_comment_template` | reporting-engine | ไม่ |
| 13 | G Security | `base_user_role_history` | server-backend | ไม่ |
| 14 | E Workflow | `server_action_mass_edit` | server-ux | ไม่ |
| 15 | F Reporting | `report_qr` | reporting-engine | ไม่ |
| 16 | D Prevention | `base_cancel_confirm` | server-ux | ไม่ |
| 17 | C Troubleshooting | `upgrade_analysis` | server-tools | ไม่ |
| 18 | E Utility | `base_technical_features` | server-ux | ไม่ |
| 19 | G Security | `base_technical_user` | server-tools | ไม่ |
| 20 | D Prevention | `base_optional_quick_create` | server-ux | ไม่ |
| 21 | D Prevention | `base_time_window` | server-tools | ไม่ |
| 22 | E/D Workflow | `base_substate` | server-ux | ไม่ |
| 23 | G Security | `base_menu_visibility_restriction` | server-ux | ไม่ |
| 24 | E Utility | `filter_multi_user` | server-ux | ไม่ |
| 25 | E Utility | `document_quick_access` | server-ux | ไม่ |
| 26 | A Performance | `base_partition` | server-tools | ไม่ |
| 27 | G Security | `dbfilter_from_header` | server-tools | ไม่ |
| 28 | F Reporting | `report_async` | reporting-engine | ไม่ |
| 29 | F Reporting | `report_qweb_element_page_visibility` | reporting-engine | ไม่ |
| 30 | F Reporting | `kpi` | reporting-engine | ไม่ |
| 31 | B Monitoring | `tracking_manager` | server-tools | ไม่ |
| 32 | E Utility | `base_view_inheritance_extension` | server-tools | ไม่ |
| 33 | D Prevention | `module_auto_update` | server-tools | ไม่ (ดู P4) |

---

# เฟส 3–5 — การประเมินโมดูลแบบละเอียด (17 ฟิลด์ต่อโมดูล)

## 1. `auditlog` — บันทึกการตรวจสอบ (Audit Trail) ✅ P1

1. **หมวด:** B — Monitoring & Anomaly Detection
2. **ชื่อโมดูล:** Audit Log
3. **ชื่อเทคนิค:** `auditlog`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/auditlog`
5. **วัตถุประสงค์:** บันทึกการตรวจสอบระดับ ORM ครบถ้วนสำหรับ create/write/unlink บนโมเดลที่กำหนด
6. **ปัญหาที่แก้ในปัจจุบัน:** ยังไม่มี audit trail ของการเขียน/ลบ; ISO 9001 และความสมบูรณ์ทางการเงินต้องการการตรวจสอบย้อนหลัง รวมถึงการลบ (`auditlog` บันทึก `unlink`) เอกสาร discovery ระบุว่าระบบอัตโนมัติและการแก้ไขข้อมูลเป็นความเสี่ยงที่ยังไม่ปิด
7. **คุณสมบัติหลัก:** ตั้งกฎรายโมเดล; บันทึกค่าเก่า→ใหม่ระดับฟิลด์; บันทึกผู้ใช้, IP, HTTP method; บันทึกการลบ; ค้นหา/export ล็อก; รองรับ trigger ระดับ DB (ทางเลือก)
8. **สถานะความเข้ากันได้:** Manifest `19.0.2.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`, `mail`
10. **ความขัดแย้งที่อาจเกิด:** น้อยมาก. เพิ่มตาราง/trigger. อย่าปรับใช้กับโมเดลชั่วคราวที่ปริมาณสูง (เช่น `mail.message`, `bus.*`, `ir.logging`) เพื่อหลีกเลี่ยง write amplification
11. **ผลกระทบฐานข้อมูล:** เพิ่มตาราง `auditlog.*` และ trigger (ทางเลือก); โตขึ้นตามเวลา — ต้องวางแผน retention
12. **ผลกระทบด้านความปลอดภัย:** เชิงบวก; แสดงประวัติการเปลี่ยนแปลงให้เฉพาะผู้มีสิทธิ์ (มี ACL ของตัวเอง)
13. **ระดับความเสี่ยง:** **MEDIUM**
14. **คำอธิบายความเสี่ยง:** เกี่ยวเข้าไปในเส้นทาง ORM write สำหรับโมเดลที่ตั้งค่า; หากตั้งกฎผิดขอบเขตจะเพิ่ม latency และขนาด DB อย่างมีนัยสำคัญ ถอนติดตั้งได้ แต่ควร archive ตารางล็อกก่อน
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้ง แล้วจำกัดขอบเขตเฉพาะโมเดลที่สำคัญทางการเงิน/ISO
17. **เหตุผล:** ปิดช่องว่างด้านธรรมาภิบาลที่ใหญ่ที่สุดโดยตรง (การตรวจสอบย้อนหลัง) ตามข้อกำหนด ISO 9001 และ baseline ความพร้อมใช้งานจริง

## 2. `sentry` — มอนิเตอร์ข้อผิดพลาด ✅ P1

1. **หมวด:** B — Monitoring & Anomaly Detection
2. **ชื่อโมดูล:** Sentry Integration
3. **ชื่อเทคนิค:** `sentry`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/sentry`
5. **วัตถุประสงค์:** ส่ง exception ของ Python/Odoo (พร้อม traceback, ผู้ใช้, context) ไปยังเซิร์ฟเวอร์ Sentry
6. **ปัญหาที่แก้:** ไม่มีการเก็บข้อผิดพลาดแบบรวมศูนย์; ข้อผิดพลาดบนโปรดักชันอยู่แค่ในไฟล์ล็อกภายในเครื่องและไม่มีการแจ้งเตือน
7. **คุณสมบัติหลัก:** hook ของ logger + WSGI exception, เสริมข้อมูลผู้ใช้/context, ตั้งค่า DSN และ environment, breadcrumbs
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.1`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`; ไลบรารี Python `sentry-sdk` (ต้อง pip เพิ่ม)
10. **ความขัดแย้งที่อาจเกิด:** ไม่คาดว่าจะขัดกับ core; ต้องมีเครือข่ายออกไปยัง endpoint ของ Sentry
11. **ผลกระทบฐานข้อมูล:** **ไม่มี**
12. **ผลกระทบด้านความปลอดภัย:** ส่ง context ข้อผิดพลาดออกนอกเครื่อง — ต้องปิดข้อมูลส่วนบุคคลและห้ามส่ง secrets; หากกังวลเรื่องที่ตั้งข้อมูลควรใช้ DSN แบบ self-hosted
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** ไม่มีการเปลี่ยนสคีมา; ความเสี่ยงคือความเป็นส่วนตัวของข้อมูลขาออก และ dependency `sentry-sdk` ที่ขาดจะทำให้โหลดโมดูลไม่ผ่าน
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งพร้อม DSN ที่ตรวจสอบแล้วและตั้งค่ากรองข้อมูลส่วนบุคคล
17. **เหตุผล:** ให้ประโยชน์ด้าน observability สูงสุดโดยแทบไม่มีต้นทุน DB; เป็นข้อกำหนดเบื้องต้นของ baseline "ต้องมี logging และ monitoring ก่อน go-live"

## 3. `auto_backup` — สำรองฐานข้อมูลอัตโนมัติ ✅ P1

1. **หมวด:** D — Prevention & Protection
2. **ชื่อโมดูล:** Database Auto-Backup
3. **ชื่อเทคนิค:** `auto_backup`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/auto_backup`
5. **วัตถุประสงค์:** dump ฐานข้อมูลตามกำหนดเวลา (และ filestore ถ้าต้องการ) พร้อม retention
6. **ปัญหาที่แก้:** baseline ความพร้อมใช้งานจริงกำหนดให้ต้องมี backup **รวม filestore** และเส้นทาง restore ที่ทดสอบได้; ยังไม่มีโมดูล backup อัตโนมัติติดตั้งอยู่
7. **คุณสมบัติหลัก:** cron backup ราย DB ไปยังโฟลเดอร์ที่กำหนด, retention ตามจำนวน/วัน, backup filestore (ทางเลือก), "backup now" แบบ manual, แจ้งเตือนทางอีเมล
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.1`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มีในเชิงฟังก์ชัน. บน Windows พาธ/สิทธิ์ปลายทางต้องเขียนได้โดยบัญชี service ของ Odoo
11. **ผลกระทบฐานข้อมูล:** ไม่กระทบสคีมา; ผลิตไฟล์ dump บนดิสก์ (ต้องตั้ง retention กันดิสก์เต็ม)
12. **ผลกระทบด้านความปลอดภัย:** ไฟล์ backup มีข้อมูลทั้งหมด — เก็บในพาธที่ป้องกัน, ห้ามเปิดผ่านเว็บ, จำกัดการเข้าถึง
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** ไม่มีการเปลี่ยน ORM/สคีมา; ความเสี่ยงคือดิสก์เต็ม (ไม่ตั้ง retention) และไฟล์ backup ไม่ถูกป้องกัน
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้ง; เขียน backup ออกนอกเครื่องแอป; ทดสอบ restore แยกต่างหาก
17. **เหตุผล:** backup + restore เป็นด่านบังคับก่อน go-live. หมายเหตุ: backup ด้วยโมดูล **ไม่ใช่** สิ่งทดแทนการทดสอบ restore และสำเนานอกสถานที่

## 4. `scheduler_error_mailer` — แจ้งเตือน cron ล้มเหลว ✅ P1

1. **หมวด:** B — Monitoring & Anomaly Detection
2. **ชื่อโมดูล:** Scheduler Error Mailer
3. **ชื่อเทคนิค:** `scheduler_error_mailer`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/scheduler_error_mailer`
5. **วัตถุประสงค์:** ส่งอีเมลหาผู้ดูแลเมื่อ scheduled job (`ir.cron`) ล้มเหลว
6. **ปัญหาที่แก้:** baseline เตือนว่า "job ที่ล้มเหลวแบบเงียบ" เป็นตัวบล็อกความพร้อม; ปัจจุบัน cron ที่ล้มเหลวมองไม่เห็น
7. **คุณสมบัติหลัก:** เกี่ยวเข้ากับการจัดการข้อผิดพลาดของ cron, ส่งเมลหาผู้รับที่กำหนดพร้อม job ที่ล้มและ traceback
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`, `mail`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มี
11. **ผลกระทบฐานข้อมูล:** ไม่มี
12. **ผลกระทบด้านความปลอดภัย:** traceback อาจเปิดเผยข้อมูลภายใน — ส่งเฉพาะผู้ดูแลภายใน
13. **ระดับความเสี่ยง:** **LOW**
14. **คำอธิบายความเสี่ยง:** เป็น hook ระดับเมลเท่านั้น; ไม่เปลี่ยนสคีมา; ไม่ override core นอกเส้นทาง cron error
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งและส่งไปยัง alias ของผู้ดูแลภายใน
17. **เหตุผล:** ต้นทุนต่ำ ปิดช่องว่าง "cron ล้มเหลวเงียบ" โดยตรง

## 5. `database_cleanup` — สุขอนามัย DB / แก้ปัญหา ✅ P1

1. **หมวด:** C — Troubleshooting & Fixes
2. **ชื่อโมดูล:** Database Cleanup
3. **ชื่อเทคนิค:** `database_cleanup`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/database_cleanup`
5. **วัตถุประสงค์:** ตรวจหาและลบ object DB ที่ตกค้าง/ซ่อนอยู่ (คอลัมน์, ตาราง, ข้อมูลโมเดล) ที่เหลือจากโมดูลที่ถูกถอด
6. **ปัญหาที่แก้:** โมดูลกำหนดเอง ~80 + OCA จำนวนมากหมุนเวียนตาม Wave; คอลัมน์/ตารางที่ตกค้างสะสมและทำให้บำรุงรักษา/อัปเกรดยาก
7. **คุณสมบัติหลัก:** ลบคอลัมน์/ตาราง, ลบแถวข้อมูลตกค้าง, ลบข้อมูลโมเดล/ฟิลด์, ดูตัวอย่างก่อนลบ, ทำงานระดับ DB เท่านั้น
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.6`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มีตอนติดตั้ง; **การดำเนินการลบเป็น manual และต้องตรวจสอบก่อน**
11. **ผลกระทบฐานข้อมูล:** สูงเมื่อใช้งานจริง (ลบคอลัมน์/ตาราง) — แต่เกิดเฉพาะเมื่อผู้ดูแลสั่งชัดเจน
12. **ผลกระทบด้านความปลอดภัย:** จำกัดให้เฉพาะ superuser/กลุ่ม technical
13. **ระดับความเสี่ยง:** **MEDIUM–HIGH**
14. **คำอธิบายความเสี่ยง:** สามารถทำให้ข้อมูลสูญหายแบบย้อนกลับไม่ได้หากใช้โดยไม่ตรวจสอบ ตัวติดตั้งเองไม่เป็นอันตราย ความเสี่ยงอยู่ที่ *การใช้งาน* แนวทางลดความเสี่ยง: backup เต็มก่อน, ใช้ preview แบบ dry-run, จำกัดผู้ดูแลคนเดียว
15. **ลำดับความสำคัญ:** **P1** (ติดตั้งตอนนี้ ใช้อย่างระมัดระวัง)
16. **ข้อเสนอแนะ:** ติดตั้งเพื่อความสามารถด้านบำรุงรักษา; ห้ามรัน purge โดยไม่มี backup ใหม่
17. **เหตุผล:** เครื่องมือบำรุงรักษาระยะยาวที่จำเป็นสำหรับ ERP ที่มีโมดูลกำหนดเองจำนวนมาก; ป้องกันสคีมาเน่าข้าม Wave

## 6. `base_cron_exclusion` — ป้องกัน cron ซ้อนทับ ✅ P1

1. **หมวด:** A — Performance & Optimization / D — Prevention
2. **ชื่อโมดูล:** Base Cron Exclusion
3. **ชื่อเทคนิค:** `base_cron_exclusion`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/base_cron_exclusion`
5. **วัตถุประสงค์:** ป้องกันไม่ให้ scheduled job เดียวกันรันพร้อมกัน (และ mutual-exclusion ระหว่าง job)
6. **ปัญหาที่แก้:** `max_cron_threads = 2` โดยไม่มี guard กันซ้อน → cron ตัวเดิมที่ใช้เวลานานซ้อนทับกันได้ ทำให้ประมวลผลซ้ำและโหลดพุ่ง
7. **คุณสมบัติหลัก:** เพิ่มฟิลด์ "exclusive" บน `ir.cron`; ข้ามการรันถ้า job เดียวกัน/ที่อนุญาตยังรันอยู่
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มี
11. **ผลกระทบฐานข้อมูล:** ไม่มี
12. **ผลกระทบด้านความปลอดภัย:** ไม่มี
13. **ระดับความเสี่ยง:** **LOW**
14. **คำอธิบายความเสี่ยง:** เพิ่มฟิลด์เล็ก ๆ บน `ir.cron`; ไม่แทนที่ตรรกะ core
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งและทำเครื่องหมาย job ที่ใช้เวลานานเป็น exclusive
17. **เหตุผล:** ปรับปรุงเสถียรภาพ/การสเกลโดยตรงด้วยความเสี่ยงน้อยมาก; เสริมรันไทม์แบบ threaded (`workers=0`)

## 7. `base_export_manager` — กำกับการ export ✅ P1

1. **หมวด:** G — Access Rights & Security
2. **ชื่อโมดูล:** Base Export Manager
3. **ชื่อเทคนิค:** `base_export_manager`
4. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/base_export_manager`
5. **วัตถุประสงค์:** ควบคุมว่าใคร export ได้ และจำกัดว่าจะ export โมเดล/ฟิลด์ใดได้
6. **ปัญหาที่แก้:** ปัจจุบันผู้ใช้ทุกคน export แบบ mass ได้ทุกอย่าง — เป็นความเสี่ยงการนำข้อมูลออกสำหรับ ERP ที่มีข้อมูลลูกค้า/การเงิน
7. **คุณสมบัติหลัก:** กฎ export รายโมเดล, allow-list ของฟิลด์, สิทธิ์ export ตามกลุ่ม, UI จัดการกฎ
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`, `web`
10. **ความขัดแย้งที่อาจเกิด:** ต่ำ; เพิ่ม ACL. เปลี่ยน UX การ export — ควรแจ้งผู้ใช้
11. **ผลกระทบฐานข้อมูล:** เพิ่มตารางกฎ `ir.exports.*` ขนาดเล็ก
12. **ผลกระทบด้านความปลอดภัย:** **เชิงบวกอย่างมีนัยสำคัญ** — ลดการเปิดเผยข้อมูลแบบ mass export
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** เปลี่ยนโมเดลสิทธิ์ข้อมูล; กฎที่ตั้งผิดอาจจำกัด export ที่ถูกต้องเกินไป
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งและตั้งค่าเริ่มต้นแบบ deny สำหรับโมเดลอ่อนไหว
17. **เหตุผล:** ปิดช่องว่างการนำข้อมูลออกที่มีอยู่จริง ด้วยโมดูลเบาและขอบเขตชัดเจน

## 8. `session_db` — ควบคุม/ดูแล session ✅ P1

1. **หมวด:** C — Troubleshooting / G — Security
2. **ชื่อโมดูล:** Session DB
3. **ชื่อเทคนิค:** `session_db`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/session_db`
5. **วัตถุประสงค์:** เก็บ HTTP session ในฐานข้อมูล ทำให้ดูรายการ session และสั่ง terminate ได้
6. **ปัญหาที่แก้:** ไม่มีทางดูหรือสั่งปิด session ที่ใช้งานอยู่; จำเป็นต่อการรับมือเหตุการณ์และการคง session ข้ามการรีสตาร์ต
7. **คุณสมบัติหลัก:** session store บน DB, มุมมอง session สำหรับผู้ดูแล, บังคับ logout, ตั้งอายุได้
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** session คงอยู่ข้ามการรีสตาร์ต (ผู้ใช้อาจสังเกตได้); ต้องมี cron ทำความสะอาด
11. **ผลกระทบฐานข้อมูล:** เพิ่มตาราง `session.db`-style พร้อมทำความสะอาดเป็นระยะ; มี write ทุกครั้งที่ session refresh (ปานกลาง)
12. **ผลกระทบด้านความปลอดภัย:** เชิงบวก — สั่งปิด session รวมศูนย์เพื่อรับมือเหตุการณ์
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** เปลี่ยนที่จัดเก็บ session; หากไม่ทำความสะอาดตารางจะโต ไม่ override core นอกเหนือ session store
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งพร้อม job ทำความสะอาด session ตามกำหนด
17. **เหตุผล:** คุณค่าด้านปฏิบัติการ/ความปลอดภัยสูงสำหรับ instance ที่เปิดผ่าน Cloudflare; ผลกระทบวงกว้างน้อย

## 9. `bi_sql_editor` (+ `sql_request_abstract`) — รายงานที่กำหนดค่าได้ ✅ P1

1. **หมวด:** F — Data Processing & Reporting
2. **ชื่อโมดูล:** BI SQL Editor (dependency: SQL Request Abstract)
3. **ชื่อเทคนิค:** `bi_sql_editor`, `sql_request_abstract`
4. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/bi_sql_editor`, `.../sql_request_abstract`
5. **วัตถุประสงค์:** สร้าง SQL view แบบอ่านอย่างเดียวและเปิดเป็นรายงาน list/pivot/graph พร้อม export โดยไม่ต้องเขียนโค้ด
6. **ปัญหาที่แก้:** KPI/การรวมข้อมูลเพื่อเจ้าของกิจการในปัจจุบันต้องสร้างโมดูลรายงาน Python เฉพาะทีละรายงาน; โมดูลนี้ให้ admin นิยามผลลัพธ์เชิงวิเคราะห์เองได้
7. **คุณสมบัติหลัก:** เครื่องมือแก้ SQL view พร้อม validation, สร้าง list/pivot/graph อัตโนมัติ, action drill-down, materialised view, สร้างเมนู/action, ACL
8. **สถานะความเข้ากันได้:** Manifest `bi_sql_editor` `19.0.2.0.1`, `sql_request_abstract` `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `sql_request_abstract` → `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มีกับโมดูลรายงานที่มีอยู่ (อยู่ร่วมกันได้) หากโมดูลกำหนดเองเปิด query เดียวกันอยู่แล้ว ควรเลือกแหล่งเดียว
11. **ผลกระทบฐานข้อมูล:** สร้าง DB view/materialised view — เป็น object สคีมาที่โมดูลเป็นเจ้าของ; ต้องจัดทำเอกสาร
12. **ผลกระทบด้านความปลอดภัย:** **สูงขึ้น** — SQL ดิบมีพลังมาก ต้องจำกัดให้กลุ่มที่เชื่อถือได้; ควรใช้ **DB role แบบ read-only** สำหรับ view
13. **ระดับความเสี่ยง:** **MEDIUM**
14. **คำอธิบายความเสี่ยง:** ให้สิทธิ์เขียน SQL แก่ผู้ใช้ระดับสูงและสร้าง object DB ถาวร การใช้ผิดอาจเสี่ยงเปิดเผยข้อมูลหรือ query หนัก แนวทางลดความเสี่ยง: ใช้กลุ่ม read-only และทบทวน query
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งสำหรับ admin จำนวนน้อย; บังคับ SQL read-only และทบทวน query
17. **เหตุผล:** สนับสนุนเป้าหมายรายงานเพื่อเจ้าของกิจการของโปรแกรมโดยตรง และลดโค้ดกำหนดเองต่อรายงาน ทางเลือกอื่น (โมดูลกำหนดเองหนึ่งต่อรายงาน) บำรุงรักษามากกว่า

## 10. `date_range` (+ `date_range_account`) — ช่วงเวลารายงาน ✅ P2

1. **หมวด:** F — Reporting
2. **ชื่อเทคนิค:** `date_range`, `date_range_account`
3. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/date_range`, `date_range_account`
4. **วัตถุประสงค์:** ช่วงวันที่ที่ใช้ซ้ำได้และผู้ใช้กำหนดเอง (รอบบัญชี, ช่วงเวลากำหนดเอง) ใช้ในตัวกรอง/domain ของรายงาน
5. **ปัญหาที่แก้:** รายงานตามรอบบัญชีปัจจุบันทำแบบ ad-hoc; `date_range_account` เป็น dependency มาตรฐานของรายงานบัญชีตามรอบ
6. **คุณสมบัติหลัก:** ช่วงที่มีชื่อ (แบบ fix/window), กฎตัวสร้าง, แยกรายบริษัท, hook รวมกับรายงาน
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`; `date_range_account` → `account`, `date_range`
9. **ความขัดแย้ง:** ไม่มี (อาจถูกดึงเป็น dependency โดยโมดูลรายงาน OCA อื่น)
10. **ผลกระทบ DB:** ตาราง `date_range.*` ขนาดเล็ก
11. **ผลกระทบด้านความปลอดภัย:** เป็นกลาง
12. **ความเสี่ยง:** **LOW** — เพิ่มเติม เบา
13. **คำอธิบายความเสี่ยง:** ไม่ override core; เป็นเพียงข้อมูลอ้างอิงใหม่
14. **ลำดับความสำคัญ:** **P2**
15. **ข้อเสนอแนะ:** ติดตั้งเมื่อตั้งค่ารายงานตามรอบเวลา
16. **เหตุผล:** เป็น building block มาตรฐาน; คุณค่าต่ำจนกว่ารายงานจะนำไปใช้ จากนั้นให้ประโยชน์สูง

## 11. `report_qweb_parameter` — พารามิเตอร์รายงานที่ผู้ใช้ตั้งได้ ✅ P2

1. **หมวด:** F — Reporting
2. **ชื่อเทคนิค:** `report_qweb_parameter`
3. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qweb_parameter`
4. **วัตถุประสงค์:** เพิ่มพารามิเตอร์ที่ผู้ใช้แก้ได้และมี validation ให้รายงาน QWeb (เลี่ยงการแก้ template ด้วยมือ)
5. **ปัญหาที่แก้:** การปรับรายงาน (ข้อความหัวบริษัท, หมายเหตุท้าย) ต้องให้นักพัฒนาแก้ XML
6. **คุณสมบัติหลัก:** นิยามพารามิเตอร์ต่อรายงาน พร้อมชนิด/validation, แก้ได้ตอนสั่งพิมพ์
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** ไม่คาดว่าเกิด; เสริมรายงาน QWeb/ISO ที่กำหนดเอง
10–11. **DB/ความปลอดภัย:** ตารางพารามิเตอร์เล็ก; ความปลอดภัยเป็นกลาง
12–13. **ความเสี่ยง:** **LOW** — ไม่ override core
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งสำหรับรายงานที่ต้องการพารามิเตอร์รันไทม์
16. **เหตุผล:** ลดรอบการแก้ไขโดยนักพัฒนาสำหรับการเปลี่ยนรายงานroutine

## 12. `base_comment_template` — บล็อกความเห็นที่ใช้ซ้ำได้ ✅ P2

1. **หมวด:** E/F — Workflow / Reporting
2. **ชื่อเทคนิค:** `base_comment_template`
3. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/base_comment_template`
4. **วัตถุประสงค์:** นิยามบล็อกความเห็นที่ใช้ซ้ำได้ แนบกับเอกสารและพิมพ์บนรายงาน
5. **ปัญหาที่แก้:** ข้อกำหนด/หมายเหตุถูกทำซ้ำในแต่ละโมดูล (`od19_sale_terms`, `od19_purchase_terms`) — คลัง template เดียวจะลดความซ้ำซ้อน
6. **คุณสมบัติหลัก:** โมเดล template, ใช้ตาม domain, เปิด/ปิดการพิมพ์/placeholder, โหมดแทนที่หรือต่อท้าย
7. **ความเข้ากันได้:** Manifest `19.0.0.0.2` (หมายเหตุ: การ port 19.0 ยังอยู่ในช่วงต้นมาก). รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** อาจ **ทับซ้อน** กับโมดูลข้อกำหนดกำหนดเองที่มีอยู่ — ต้องตัดสินใจแหล่งข้อมูลเดียว (source of truth) ก่อนนำมาใช้
10–11. **DB/ความปลอดภัย:** ตาราง template เล็ก; เป็นกลาง
12–13. **ความเสี่ยง:** **LOW–MEDIUM** — ความเสี่ยงทางเทคนิคต่ำ แต่ port ระยะต้นและทับซ้อนเชิงฟังก์ชัน
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ประเมินเทียบกับ `od19_*_terms` ก่อนนำมาใช้; อย่ารันทั้งสองพร้อมกัน
16. **เหตุผล:** เครื่องมือลดความซ้ำที่ดี แต่ใช้ได้ต่อเมื่อมัน *แทนที่* (ไม่ใช่ทำซ้ำ) ข้อกำหนดกำหนดเองที่มีอยู่

## 13. `base_user_role_history` — ตรวจสอบการเปลี่ยนสิทธิ์ ✅ P2

1. **หมวด:** G — Access Rights & Security
2. **ชื่อเทคนิค:** `base_user_role_history`
3. **Repo OCA:** `OCA/server-backend` → `third_party/oca/server-backend/base_user_role_history`
4. **วัตถุประสงค์:** ติดตามการเปลี่ยนแปลงของผู้ใช้/บทบาท (ใครเปลี่ยนอะไร เมื่อไร)
5. **ปัญหาที่แก้:** การเปลี่ยนสิทธิ์ไม่มีการติดตาม; ตอบคำถาม "ใครให้สิทธิ์นี้" ได้ยาก
6. **คุณสมบัติหลัก:** ล็อกประวัติการเปลี่ยนบทบาท/ผู้ใช้, snapshot บทบาทปัจจุบัน/ก่อนหน้า, รวมกับ chatter
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**. ต้องพึ่ง `base_user_role` ที่ติดตั้งแล้ว
8. **Dependencies:** `base_user_role`
9. **ความขัดแย้ง:** ไม่มี (ขยายโมเดลบทบาทที่ติดตั้งแล้ว)
10–11. **DB/ความปลอดภัย:** เพิ่มแถวประวัติ; **คุณค่าด้านความปลอดภัยเชิงบวก**
12–13. **ความเสี่ยง:** **LOW** — เพิ่มเติมบนฐานที่ติดตั้งแล้ว
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งคู่กับ `auditlog`
16. **เหตุผล:** การตรวจสอบความปลอดภัยที่ตรงจุดและต้นทุนต่ำสำหรับชั้น RBAC

## 14. `server_action_mass_edit` — แก้ไขเป็นกลุ่ม ✅ P2

1. **หมวด:** E — Utilities & Workflow
2. **ชื่อเทคนิค:** `server_action_mass_edit`
3. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/server_action_mass_edit`
4. **วัตถุประสงค์:** server action ประเภทแก้ไขฟิลด์เป็นกลุ่มบนเรกคอร์ดที่เลือก
5. **ปัญหาที่แก้:** การแก้ไขข้อมูลเป็นกลุ่มในปัจจุบันต้องใช้สคริปต์เฉพาะกิจหรือแก้ทีละเรกคอร์ด
6. **คุณสมบัติหลัก:** mass update ตาม domain, ดูตัวอย่างเรกคอร์ดที่จะกระทบ, กำหนดค่าต่อฟิลด์, รันจาก server action
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** ไม่มี
10–11. **DB/ความปลอดภัย:** เขียนหลายเรกคอร์ดพร้อมกันได้ → จำกัดให้กลุ่มที่เชื่อถือได้; เพิ่มเฉพาะการตั้งค่า action
12–13. **ความเสี่ยง:** **MEDIUM** — mass write อาจเปลี่ยนข้อมูลวงกว้างโดยไม่ตั้งใจหาก domain ผิด
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้ง จำกัดให้กลุ่ม admin/technical
16. **เหตุผล:** เพิ่มผลิตภาพจริงสำหรับงานแก้ไขข้อมูล แต่ต้องมี guard ด้านสิทธิ์

## 15. `report_qr` — QR Code บนรายงาน ✅ P2

1. **หมวด:** F — Reporting
2. **ชื่อเทคนิค:** `report_qr`
3. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qr`
4. **วัตถุประสงค์:** แสดง QR code ในรายงาน QWeb
5. **ปัญหาที่แก้:** ระบบ e-tax/e-invoice ไทยและการตรวจสอบมีแนวโน้มต้องมีเนื้อหา QR บนเอกสารพิมพ์
6. **คุณสมบัติหลัก:** helper QWeb สำหรับฝังภาพ QR จาก payload ใด ๆ
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**; ต้องมีไลบรารี Python `qrcode` (pip เพิ่ม)
8. **Dependencies:** `base` (+ ไลบรารี `qrcode`)
9. **ความขัดแย้ง:** ไม่มี
10–11. **DB/ความปลอดภัย:** ไม่มี/น้อยมาก
12–13. **ความเสี่ยง:** **LOW** — เป็น helper แสดงผลเท่านั้น
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งเมื่อต้องมีเอกสารที่มี QR
16. **เหตุผล:** เล็ก เป็นมาตรฐาน และเปิดทางให้ผลลัพธ์การพิมพ์พร้อม compliance

## 16. `base_cancel_confirm` — guard การยกเลิก ✅ P2

1. **หมวด:** D — Prevention & Protection
2. **ชื่อเทคนิค:** `base_cancel_confirm`
3. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/base_cancel_confirm`
4. **วัตถุประสงค์:** บังคับให้ยืนยันชัดเจนก่อนยกเลิกเรกคอร์ด
5. **ปัญหาที่แก้:** การยกเลิกออเดอร์/ใบแจ้งหนี้โดยไม่ตั้งใจสามารถเกิดขึ้นได้โดยไม่มี guard เพิ่มเติม — ตรงกับวัตถุประสงค์ "ป้องกันข้อผิดพลาดในการปฏิบัติงาน" ของโครงการ
6. **คุณสมบัติหลัก:** wizard ยืนยันตอนยกเลิกสำหรับโมเดลที่เปิดใช้
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** ไม่คาดว่าเกิด; ตรวจสอบกับ override การยกเลิกใน `od19_sale_wizards`/`od19_purchase_wizards`
10–11. **DB/ความปลอดภัย:** ไม่มี; เป็น guard ระดับ UX ที่เพิ่มเติม
12–13. **ความเสี่ยง:** **LOW** — guard ระดับ UI
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งสำหรับโมเดลที่มีนัยสำคัญทางการเงิน
16. **เหตุผล:** บริการวัตถุประสงค์ด้านการป้องกันโดยตรงด้วยความเสี่ยงน้อยมาก

---

## เฟส 3–5 — การประเมินแบบย่อ (P3 / P4)

| โมดูล | หมวด | Repo | เวอร์ชัน (manifest) | ความเสี่ยง | เหตุผล | ลำดับ |
| --- | --- | --- | --- | --- | --- | --- |
| `upgrade_analysis` | C | server-tools | 19.0.1.1.4 | MEDIUM | เทียบสคีมา/ข้อมูลข้ามเวอร์ชัน; สำคัญต่อความปลอดภัยในการอัปเกรด OCA/custom; ต้องมี reference revision | P2 |
| `base_technical_features` | E | server-ux | 19.0.1.0.0 | LOW | เปิดฟิลด์เทคนิคให้กลุ่มเฉพาะ; ช่วยแก้ปัญหา | P3 |
| `base_technical_user` | G | server-tools | 19.0.1.0.0 | LOW | บล็อกการใช้ผู้ใช้ "technical" เป็นทางลัด API; hardening | P3 |
| `base_optional_quick_create` | D | server-ux | 19.0.1.0.0 | LOW | ป้องกันการสร้างเร็วซ้ำโดยไม่ตั้งใจ | P3 |
| `base_time_window` | D | server-tools | 19.0.1.0.0 | LOW–MEDIUM | ตรวจสอบช่วงวันที่ไม่ทับซ้อน; เหมาะกับสัญญา/แผนงาน | P3 |
| `base_substate` | E | server-ux | 19.0.1.0.0 | LOW | สถานะย่อยของเรกคอร์ด; ทับซ้อนฟิลด์สถานะกำหนดเอง | P3 |
| `base_menu_visibility_restriction` | G | server-ux | 19.0.1.0.0 | LOW | ซ่อนเมนูตามกลุ่ม — สะอาดกว่าการทำเมนูซ้ำ | P3 |
| `filter_multi_user` | E | server-ux | 19.0.1.0.0 | LOW | ตัวกรองใช้ร่วมในทีม; ได้ UX | P3 |
| `document_quick_access` | E | server-ux | 19.0.1.0.0 | LOW | ลิงก์เอกสารเร็ว; UX เล็กน้อย | P3 |
| `base_partition` | A | server-tools | 19.0.1.0.0 | MEDIUM–HIGH | partition ตารางขนาดใหญ่มาก (log/auditlog). ใช้เมื่อพิสูจน์แล้วว่าโตจริง | P3 |
| `dbfilter_from_header` | G | server-tools | 19.0.1.0.0 | MEDIUM | บังคับ dbfilter ที่ proxy — แต่โครงการ pin `dbfilter` และใช้ DB เดียวอยู่แล้ว; เกี่ยวเฉพาะ multi-DB ผ่าน Nginx | P3 |
| `report_async` | F | reporting-engine | 19.0.1.0.0 | MEDIUM | สร้างรายงานหนักแบบ async; ต้องมี queue. ใช้เมื่อมีรายงานใหญ่ | P3 |
| `report_qweb_element_page_visibility` | F | reporting-engine | 19.0.1.0.0 | LOW | แสดง/ซ่อนองค์ประกอบหน้าแรก/หน้าสุดท้าย — รองรับข้อกำหนดวาง footer ISO | P3 |
| `kpi` | F | reporting-engine | 19.0.1.0.1 | LOW–MEDIUM | คำนวณ/แสดง KPI; ทับซ้อน BI SQL Editor + dashboard. เลือกอย่างเดียว | P3 |
| `tracking_manager` | B | server-tools | 19.0.1.0.1 | LOW | ตั้งค่า field tracking โดยไม่เขียนโค้ด; ทับซ้อน `auditlog` | P3 |
| `base_view_inheritance_extension` | E | server-tools | 19.0.1.0.0 | LOW | XPath ที่ยืดหยุ่นขึ้นใน view ที่ inherit; สะดวกเฉพาะนักพัฒนา | P3 |
| `base_kanban_stage` | E | server-tools | 19.0.1.0.0 | LOW | โมเดล stage ทั่วไป; ใช้เมื่อสร้าง kanban pipeline | P3 |
| `attachment_unindex_content` | A | server-tools | 19.0.1.0.0 | LOW–MEDIUM | ข้ามการทำดัชนีเนื้อหาไฟล์แนบเพื่อลดโหลด — แต่โครงการ *ต้องการ* ทำดัชนี PDF (pdfminer.six); ขัดกับเจตนา | P4 ตามเจตนาปัจจุบัน |
| `sequence_python` | E | server-tools | 19.0.1.0.0 | LOW | ค่าลำดับจาก Python; โมดูลกำหนดเองอาจครอบคลุมแล้ว | P3 |
| `module_auto_update` | D | server-tools | 19.0.1.0.1 | **HIGH** | อัปเดตโมดูลอัตโนมัติเมื่อโค้ดเปลี่ยน — อันตรายกับ 13 OCA submodule + ~80 โมดูลกำหนดเอง; อาจกระตุ้นการอัปเกรดสคีมาโดยไม่ตั้งใจตอนโหลด | **P4** |
| `module_change_auto_install` | D | server-tools | 19.0.1.0.0 | MEDIUM | ติดตั้งโมดูลอัตโนมัติเมื่อไฟล์เปลี่ยน; ความเสี่ยงคลาสเดียวกับข้างบน | P3–P4 |
| `rpc_helper` | C | server-tools | 19.0.1.0.0 | LOW | ตัวช่วย RPC/ดีบัก URL — เครื่องมือนักพัฒนาเท่านั้น | P3 |
| `base_search_fuzzy` | A | server-tools | 19.0.1.0.0 | MEDIUM | ค้นหาแบบ trigram; เพิ่ม DB extension และต้นทุน index. ใช้เมื่อพิสูจน์ว่าค้นหาช้า | P4 |
| `base_external_dbsource` | — | server-backend | 19.0.1.0.0 | **HIGH** | เชื่อมต่อ DB ภายนอกได้ตามอำเภอใจ — พื้นผิวโจมตี/นำข้อมูลออก. ไม่แนะนำ | **P4** |
| `bus_alt_connection` | — | server-tools | 19.0.1.0.0 | MEDIUM | bus/IM connection อีกทาง; ยังไม่พบความจำเป็น | P4 |
| `iap_alternative_provider` | — | server-tools | 19.0.1.0.0 | MEDIUM | ใช้เมื่อต้องเปลี่ยนผู้ให้บริการ IAP ของ Odoo | P4 |
| `onchange_helper` | E | server-tools | 19.0.1.0.0 | LOW | ตัวช่วยนักพัฒนา; ไม่มีความจำเป็นทางธุรกิจ | P4 |
| `base_fontawesome` | E | server-tools | 19.0.1.0.0 | LOW | แพ็กชุดไอคอน; Odoo มีไอคอนให้แล้ว | P4 |
| `base_write_diff` | B | server-tools | 19.0.1.0.0 | LOW | ล็อก write diff ลงไฟล์; ทับซ้อน `auditlog` | P4 |

---

# เฟส 6 — การตรวจสอบความซ้ำซ้อนและความขัดแย้ง

| โมดูลที่เสนอ | Core/EE | OCA ที่ติดตั้ง | โมดูลกำหนดเอง | ข้อสรุป |
| --- | --- | --- | --- | --- |
| `auditlog` | Core มีแค่ tracking ผ่าน `mail.thread` (ระดับฟิลด์ ต่อโมเดล) — **ไม่ใช่** audit trail ของ write/delete เต็มรูปแบบ | — | มีการใช้ `tracking=True` ในโมเดล ISO (บางส่วน) | **เพิ่มความสามารถ** ไม่ใช่ของซ้ำจริง |
| `sentry` | Core ล็อกลงไฟล์เท่านั้น | — | — | ไม่ซ้ำ |
| `auto_backup` | Core ไม่มีตัวจัดตาราง backup ในตัว | — | — | ไม่ซ้ำ |
| `scheduler_error_mailer` | Core ล็อก cron ล้มเหลวแบบเงียบ | — | — | ไม่ซ้ำ |
| `database_cleanup` | `upgrade_analysis` (คนละวัตถุประสงค์) | — | — | ไม่ซ้ำ |
| `base_cron_exclusion` | `ir.cron` ของ core ไม่มี mutual-exclusion | — | `od19_misc_features.runtime_guard` ไม่เกี่ยวข้อง (guard AR/AP) | ไม่ซ้ำ |
| `base_export_manager` | export ของ core ไม่มี ACL | — | — | ไม่ซ้ำ |
| `session_db` | session ของ core อยู่บน filesystem | — | — | ไม่ซ้ำ |
| `bi_sql_editor` | Core มีเฉพาะ "Pivot/Graph" บนโมเดลที่มีอยู่ | `report_xlsx` (เพียงรูปแบบผลลัพธ์) | โมดูลรายงานกำหนดเองหลายตัว | ไม่ซ้ำ; **ลด** โมดูลกำหนดเองในอนาคต |
| `date_range` | Core มี util ปีบัญชี แต่ไม่มีช่วงที่ผู้ใช้กำหนดเอง | — | — | ไม่ซ้ำ |
| `report_qweb_parameter` | QWeb ของ core แก้ต้องเขียนโค้ด | — | — | ไม่ซ้ำ |
| `base_comment_template` | — | — | `od19_sale_terms`, `od19_purchase_terms` | **ทับซ้อน** — นำมาใช้ต่อเมื่อแทนที่โมดูล terms กำหนดเอง |
| `base_user_role_history` | — | `base_user_role` (ติดตั้งแล้ว) | — | เสริมฐานที่ติดตั้งแล้ว |
| `server_action_mass_edit` | Core มี server actions แต่ไม่มี UI mass-edit | — | — | ไม่ซ้ำ |
| `report_qr` | Core ไม่มี helper QR | — | — | ไม่ซ้ำ |
| `base_cancel_confirm` | Core แค่ยกเลิก | — | มี override การยกเลิกกำหนดเอง | ต้องตรวจสอบการทำงานร่วม |
| `module_auto_update` | — | — | — | เสี่ยงและซ้ำซ้อนกับการ deploy แบบควบคุม |
| `attachment_unindex_content` | — | — | memory: ต้องการทำดัชนี PDF (pdfminer.six) | **ขัดกับเจตนา** — ข้าม |
| `base_external_dbsource` | — | — | — | **คำแนะนำเชิงลบด้านความปลอดภัย** |

---

# เฟส 7 — ผลลัพธ์

## บทสรุปผู้บริหาร (Executive Summary)

instance `odoo19` เป็น **Odoo 19 CE greenfield ที่มีโครงสร้างดี** ด้วยแนวทาง "OCA-first, custom-second" อย่างมีวินัย มี OCA submodule 13 รายการที่ pin ไว้ และโมดูลกำหนดเอง `od19_*` ~80 ตัว ครอบคลุม sales, purchasing, accounting, ISO, helpdesk และ inventory รากฐานสถาปัตยกรรมแข็งแรงดี อย่างไรก็ตาม ระบบมีความ **ไม่สมดุลของวุฒิภาวะ** ชัดเจน: ด้าน *ธุรกิจ* ครอบคลุมดี แต่ **ชั้นปฏิบัติการ/ธรรมาภิบาลบาง** สรุปคือ:

1. **ไม่มี audit trail, ไม่มีการมอนิเตอร์ข้อผิดพลาด, ไม่มีการแจ้งเตือน cron ล้มเหลว, ไม่มี backup อัตโนมัติ, ไม่มีการควบคุม export และไม่มีการจัดการ session** — ทั้งหมดนี้ baseline *ความพร้อมใช้งานจริง* ของโครงการเองกำหนดให้ต้องมีก่อน go-live และ ISO 9001 ต้องการการตรวจสอบย้อนหลัง
2. **รันไทม์เป็นแบบ single-process threaded (`workers = 0`)** และไม่มี guard กัน cron ซ้อน — เป็นข้อจำกัดด้านการสเกล/เสถียรภาพหลักสำหรับ ERP หลายผู้ใช้
3. **จุดอ่อนด้านความปลอดภัย 2 จุดชัดเจน:** DB manager เปิดเผย (`list_db = True`) และรหัสผ่าน DB อยู่ในไฟล์ config แบบข้อความธรรมดา (ต้องยืนยันการกันออกจาก VCS)
4. **หนี้ด้านการบำรุงรักษา** ในชั้นกำหนดเอง: โมดูลออกเลขเอกสารขนานกัน 6 ตัว, โมดูลรวมของหลายอย่าง 1 ตัว (`od19_misc_features`) และโมดูลที่ดูเหมือนโครงร่างเปล่า/report-only หลายตัว ควรตรวจสอบหรือรวม

แนวทางที่แนะนำคือ **ไม่** เน้นปริมาณ แต่ใช้ **โมดูล P1 ประมาณ 9 ตัว** ที่ปิดช่องว่างด้านปฏิบัติการ ความปลอดภัย และ observability ด้วยความเสี่ยง LOW–MEDIUM พร้อมรายการ P2 สั้น ๆ สำหรับ reporting และ workflow มีหลายโมดูลที่ **ไม่แนะนำอย่างชัดเจน** (auto-update โมดูล, external DB source, fuzzy search, de-index ไฟล์แนบ) เพราะเพิ่มความเสี่ยงหรือขัดกับเจตนาที่มีอยู่

## ข้อเสนอแนะอันดับต้น (มูลค่าสูงสุด)

| อันดับ | โมดูล | คุณค่า | ความเสี่ยง | ลำดับ |
| --- | --- | --- | --- | --- |
| 1 | `auditlog` | การตรวจสอบ write/delete ครบถ้วน (ISO + การเงิน) | MEDIUM | P1 |
| 2 | `sentry` | มอนิเตอร์ข้อผิดพลาดรวมศูนย์ | LOW–MEDIUM | P1 |
| 3 | `auto_backup` | ระบบสำรองอัตโนมัติ (ด่าน go-live) | LOW–MEDIUM | P1 |
| 4 | `base_export_manager` | หยุดการนำข้อมูลออกแบบ mass | LOW–MEDIUM | P1 |
| 5 | `scheduler_error_mailer` | ยุติปัญหา cron ล้มเหลวเงียบ | LOW | P1 |
| 6 | `base_cron_exclusion` | ป้องกัน cron ซ้อนทับ | LOW | P1 |
| 7 | `database_cleanup` | สุขอนามัยสคีมาระยะยาว | MEDIUM–HIGH (เฉพาะปฏิบัติการ) | P1 |
| 8 | `session_db` | มองเห็น/สั่งปิด session | LOW–MEDIUM | P1 |
| 9 | `bi_sql_editor` | รายงานเพื่อเจ้าของกิจการที่กำหนดค่าได้ | MEDIUM | P1 |

## ข้อเสนอแนะด้านความปลอดภัย (Security)

- **`auditlog`** (P1) — การตรวจสอบ write/delete รากฐานของการตรวจสอบความปลอดภัย/ISO
- **`base_export_manager`** (P1) — จำกัด mass export ของข้อมูลลูกค้า/การเงิน
- **`session_db`** (P1) — เห็นและปิด session ที่ใช้งานอยู่ระหว่างเหตุการณ์
- **`base_user_role_history`** (P2) — ตรวจสอบว่าใครเปลี่ยนบทบาท/สิทธิ์
- **`base_technical_user`** (P3) — เสริมความแข็งแรงเส้นทาง technical/service user
- **`base_menu_visibility_restriction`** (P3) — ซ่อนเมนูตามกลุ่มแทนการทำเมนูซ้ำ
- **คำแนะนำเชิงลบ:** `base_external_dbsource` (ความเสี่ยง HIGH พื้นผิวการนำข้อมูลออก) → **ห้ามติดตั้ง**

**PROPOSED CHANGE — NOT EXECUTED (config ความปลอดภัย ไม่ใช่โมดูล):**
- ตั้ง `list_db = False` ใน `odoo.conf` และใช้ `dbfilter` เพียงอย่างเดียว
- ยืนยันว่า `odoo.conf` (ที่มี `db_password`) ถูกกันออกจาก VCS; ควรใช้ env/กลไก secret แทน
- พิจารณา rate limiting ฝั่ง Nginx และกฎ Cloudflare WAF ซึ่งมีนัยจาก DDNS/proxy ที่ตั้งไว้แล้ว

## ข้อเสนอแนะด้านประสิทธิภาพ (Performance)

- **`base_cron_exclusion`** (P1) — ป้องกัน job ยาวซ้อนทับภายใต้ `max_cron_threads = 2`
- **`base_partition`** (P3) — เฉพาะเมื่อพิสูจน์ได้ว่าตาราง audit/log ใหญ่จริง; มิฉะนั้นข้าม
- **คำแนะนำเชิงลบ:** `base_search_fuzzy` (P4) — เพิ่ม trigram index/DB extension โดยไม่มีความจำเป็นที่พิสูจน์ได้
- **คำแนะนะเชิงลบ:** `module_auto_update` (P4, HIGH) — อัปเกรดอัตโนมัติแบบไม่ควบคุมข้าม 13 OCA submodule + ~80 โมดูลกำหนดเอง

**PROPOSED CHANGE — NOT EXECUTED (runtime/config):**
- ประเมิน `workers = N` (multi-process) สำหรับโปรดักชัน และตั้ง `limit_request`; ตรวจสอบกับขีดจำกัดหน่วยความจำและการ deploy บน Windows
- เพิ่ม log rotation สำหรับ `odoo_server.log` (Odoo ไม่ rotate เองโดยค่าเริ่มต้น)
- ทบทวน `max_cron_threads` เทียบกับระยะเวลาจริงของงาน เมื่อ `base_cron_exclusion` ทำงานแล้ว

## ข้อเสนอแนะด้านปฏิบัติการ (Operations)

- **`sentry`** (P1) — เก็บและแจ้งเตือนข้อผิดพลาด
- **`scheduler_error_mailer`** (P1) — แจ้งเตือน cron ล้มเหลว
- **`auto_backup`** (P1) — backup ตามกำหนด + retention
- **`database_cleanup`** (P1) — ลบ object สคีมาตกค้างในช่วง maintenance window
- **`session_db`** (P1) — ควบคุม session ด้านปฏิบัติการ
- **`upgrade_analysis`** (P2) — ความปลอดภัยในการอัปเกรดบนหลักฐาน
- **`rpc_helper`**, **`base_technical_features`** (P3) — เครื่องมือ admin/วินิจฉัย

## ข้อเสนอแนะด้านเวิร์กโฟลว์ (Workflow)

- **`server_action_mass_edit`** (P2) — แก้ไขข้อมูลเป็นกลุ่มแบบควบคุมได้
- **`base_cancel_confirm`** (P2) — guard การยกเลิกโดยไม่ตั้งใจ
- **`base_comment_template`** (P2) — แทนตรรกะข้อกำหนด/หมายเหตุที่ซ้ำ (เฉพาะถ้าแทนที่ `od19_*_terms`)
- **`filter_multi_user`**, **`base_menu_visibility_restriction`**, **`document_quick_access`** (P3) — UX/ผลิตภาพ
- **การรวม (custom ไม่ใช่ OCA):** รวมโมดูล `*_document_sequence` 6 ตัว และแยก `od19_misc_features` — ลดพื้นผิวการบำรุงรักษา

## ข้อเสนอแนะด้านรายงานและข้อมูล (Reporting & Data)

- **`bi_sql_editor` + `sql_request_abstract`** (P1) — view/รายงานเชิงวิเคราะห์ที่ admin นิยามเองโดยไม่ต้องเขียนโค้ดใหม่
- **`date_range` + `date_range_account`** (P2) — ช่วงเวลารายงานมาตรฐาน
- **`report_qweb_parameter`** (P2) — พารามิเตอร์รายงานที่ผู้ใช้แก้ได้
- **`base_comment_template`** (P2) — หมายเหตุการพิมพ์ที่สม่ำเสมอ
- **`report_qr`** (P2) — QR บนเอกสาร (ความพร้อม e-tax/e-invoice)
- **`report_qweb_element_page_visibility`** (P3) — ควบคุมองค์ประกอบหน้าแรก/สุดท้าย (รองรับการวาง footer ISO)
- **เลือกอย่างใดอย่างหนึ่ง** ระหว่าง `kpi` **หรือ** `bi_sql_editor` สำหรับ dashboard KPI — อย่าซ้อนทั้งสอง

---

# บันทึกการส่งมอบ — สิ่งที่ยังไม่ได้ทำ

ตามข้อจำกัดของการประเมินนี้ **ไม่มีการติดตั้ง อัปเกรด ถอน แก้ไข migrate หรือรีสตาร์ตสิ่งใดเลย** ไม่มีไฟล์ซอร์ส ไฟล์ config สิทธิ์การเข้าถึง หรือ record rule ใดถูกแก้ไข ข้อค้นพบทั้งหมดมาจากการอ่าน `odoo.conf`, `.gitmodules`, manifest ของโมดูล และเอกสารกำกับดูแลใน `docs/superpowers/**`

การเปลี่ยนแปลงด้าน config หรือ runtime ที่กล่าวถึงข้างต้นถูกระบุชัดว่า **"PROPOSED CHANGE — NOT EXECUTED"** และต้องได้รับอนุมัติแยกก่อนดำเนินการ

## ขอบเขตจำกัดของการประเมินนี้

- ความเข้ากันได้ของโมดูลตรวจสอบใน **ระดับ manifest เท่านั้น** (declared `19.0.x` บน branch `19.0`) ไม่ได้รันทดสอบพฤติกรรมจริง และระบุเป็น **COMPATIBILITY NOT VERIFIED (runtime)** ในจุดที่เกี่ยวข้อง
- ชุดโมดูลที่ติดตั้งนำมาจากการ discovery ก่อนหน้า (~234 โมดูล); ควรยืนยันซ้ำจาก `ir_module_module` ก่อนตัดสินใจติดตั้งใด ๆ
- โมดูลกำหนดเองหลายตัวดูเหมือนเป็นโครงร่างเปล่าหรือ report-only และต้องตรวจสอบก่อนนับว่าเป็นความครอบคลุมที่ทำงานได้จริง
