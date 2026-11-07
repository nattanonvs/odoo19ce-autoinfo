# รายงานวิเคราะห์การจัดระเบียบเมนู NavBar — Odoo 19 CE (AutoInfo)

- **วันที่**: 2026-11-06
- **ฐานข้อมูลที่ตรวจ**: `odoo19_pdev` (อ่านอย่างเดียว)
- **ขอบเขต**: แถบเมนู (NavBar sections) ของทุกแอพ — รวมแอพ Core ของ Odoo
- **สถานะ**: รายงานวิเคราะห์ (ยังไม่แก้ข้อมูล) — รออนุมัติก่อนลงมือ
- **วิธีเก็บข้อมูล**: เชื่อมต่อ PostgreSQL โดยตรง (read-only) ดึงตาราง `ir_ui_menu` + `ir_model_data` ทั้งหมด **938 เมนู / 34 แอพ** สคริปต์: `_tmp_dumpcheck/menu_dump.py` (ไม่ commit)

---

## 1. บทสรุปผู้บริหาร

1. NavBar ของ Odoo 19 แสดง **หัวข้อเมนูระดับบนสุดของแต่ละแอพ** (เรียกว่า *sections*) เป็นแถวเดียว โดย **วัดความกว้างจริงบนหน้าจอ** ถ้าล้นจะย้ายหัวข้อส่วนท้ายไปกองที่ปุ่ม **"+" (More navigator)** ให้อัตโนมัติ — ไม่มีตัวเลขตายตัวว่า "เกิน 10 แล้วตัด" (เลข 10 ในเทมเพลตใช้แค่กำหนดคีย์ลัดเท่านั้น)
2. ปัญหาหลักที่พบคือ **หัวข้อซ้ำชื่อกันในแอพเดียวกัน** และ **หัวข้อที่เกี่ยวข้องกันถูกแยกเป็นหลายหัวข้อ** ทำให้กินความกว้างเกินจำเป็นและต้องกด "+" บ่อย
3. **แก้ไข (ตรวจซ้ำด้วยกลไกการแสดงผลจริง)**: เมนูชื่อซ้ำ 3 จุดที่ได้จากตารางดิบ (Project / Maintenance / Settings) **ไม่ปรากฏบน NavBar จริงในปัจจุบัน** เพราะ Odoo ตัดเมนูที่ไม่มี action และไม่มีเมนูย่อยที่ถือ action ออกทั้งหมด (ดูข้อ 2.1) — ปัญหาจริงที่เหลือคือ **จำนวนหัวข้อล้นแถว** และ **จุดทับซ้อนเชิงความหมาย ~7 จุด** (Sales, Accounting, Employees, Knowledge ฯลฯ)
4. แอพที่เสี่ยงล้นแถวมากที่สุด (นับหัวข้อที่แสดงจริง): **Accounting (13), Sales (12), Project (10), Settings (8), Inventory (7)**
5. ข้อเสนอ: จัดกลุ่มหัวข้อที่เกี่ยวข้องให้เป็นหัวข้อเดียว (มีเมนูย่อยข้างใน) + เปลี่ยนชื่อหัวข้อที่ซ้ำ/กำกวม + เรียงลำดับใหม่ — ดำเนินการผ่าน **custom module override** (ไม่แตะไฟล์ Core)

---

## 2. กลไก NavBar ของ Odoo 19 (อ้างอิงจากโค้ด Core)

ไฟล์ที่เกี่ยวข้อง:
- เทมเพลต: [navbar.xml](file:///c:/odoo-dev/odoo19/addons/web/static/src/webclient/navbar/navbar.xml#L147-L264)
- ตรรกะ: [navbar.js](file:///c:/odoo-dev/odoo19/addons/web/static/src/webclient/navbar/navbar.js#L119-L203)

พฤติกรรมที่ต้องทราบก่อนจัดเมนู:

| กลไก | รายละเอียด |
|---|---|
| **Sections** | หัวข้อเมนู = ลูกโดยตรงของ root menu ของแอพ (`getMenuAsTree(app).childrenTree`) |
| **การแสดงผล** | เรนเดอร์ทุกหัวข้อก่อน แล้ววัดความกว้าง (`adapt()`); ถ้าความกว้างรวม > พื้นที่ว่าง จะซ่อนหัวข้อ **ส่วนท้าย** และย้ายไปปุ่ม "+" |
| **ปุ่ม "+" (More navigator)** | `web.NavBar.SectionsMenu.MoreDropdown` — แสดงหัวข้อที่ซ่อน พร้อมเมนูย่อยข้างใน จึงยังเข้าถึงได้ครบ |
| **คีย์ลัด** | หัวข้อลำดับที่ 1–10 ได้คีย์ลัด Alt+1..Alt+0 (ตัวเลข `Math.min(10, …)`) — **ไม่เกี่ยวกับการตัดหัวข้อ** |
| **มือถือ** | `ui.isSmall` = true จะไม่แสดง sections ในแถว แต่ใช้ sidebar (hamburger) แทน |

**ผลที่ตามมา**: วิธีทำให้ "เห็นหัวข้อครบในแถวเดียว" ที่ได้ผลจริงคือ **ลดจำนวนหัวข้อ + ย่อชื่อหัวข้อ** ไม่ใช่ตั้งค่าตัวเลขจำนวนสูงสุด

> เกณฑ์ที่ใช้ในรายงานนี้: ถ้าจำนวนหัวข้อ ≤ 6 = ปลอดภัย, 7–9 = เฝ้าระวัง (แล้วแต่ความยาวชื่อ/ความกว้างจอ), ≥ 10 = เสี่ยงล้นแน่นอน

### 2.1 กฎการแสดงเมนูจริง (สำคัญ — ใช้แก้ตัวเลขทั้งรายงาน)

จาก [ir_ui_menu.py](file:///c:/odoo-dev/odoo19/odoo/addons/base/models/ir_ui_menu.py#L121-L134) เมนูจะถูกนับเป็น "มองเห็นได้" **ก็ต่อเมื่อ** เข้าเงื่อนไขใดเงื่อนไขหนึ่ง:

1. มี `action` (ที่ผู้ใช้มีสิทธิ์อ่าน), หรือ
2. เป็น **แม่ (ancestor)** ของเมนูที่มี `action`

เมนูที่ **ไม่มี action และไม่มีเมนูย่อยที่ถือ action** จะถูกตัดออกจาก NavBar ทั้งหมด (เป็น merely "ที่ว่าง" ไม่แสดง) และยังต้อง `active = True`

**ผลต่อรายงานนี้**: ตารางในข้อ 3 เดิมนับจาก raw DB จึงรวมเมนูที่ว่างด้วย ทำให้ตัวเลขสูงเกินจริง โดยเฉพาะ Settings (10 → 8) และ Maintenance (6 → 5) และเมนูชื่อซ้ำทั้ง 3 จุดในข้อ 4.1 จริง ๆ แล้วไม่แสดง (ดูสคริปต์ `_tmp_dumpcheck/menu_visible.py` ที่จำลองกฎนี้)

---

## 3. ภาพรวมทุกแอพ (34 แอพ)

| # | แอพ (root menu) | xmlid | จำนวนหัวข้อ | สถานะ |
|---|---|---|---:|---|
| 1 | Discuss | `mail.menu_root_discuss` | 5 | ปลอดภัย |
| 2 | Calendar | `calendar.mail_menu_calendar` | 3 | ปลอดภัย |
| 3 | Contacts | `contacts.menu_contacts` | 2 | ปลอดภัย |
| 4 | CRM | `crm.crm_menu_root` | 5 | ปลอดภัย |
| 5 | **Sales** | `sale.sale_menu_root` | **12** | **เสี่ยงล้น** |
| 6 | Billing Requests | `od19_billing_request.menu_od19_billing_request_root` | 2 | ปลอดภัย |
| 7 | **Accounting** | `account.menu_finance` | **13** | **เสี่ยงล้น** |
| 8 | Dashboards | `spreadsheet_dashboard.spreadsheet_dashboard_menu_root` | 6 | ปลอดภัย |
| 9 | Link Tracker | `utm.menu_link_tracker_root` | 1 | ปลอดภัย |
| 10 | Purchase | `purchase.menu_purchase_root` | 4 | ปลอดภัย |
| 11 | Purchase Requests | `purchase_request.parent_menu_purchase_request` | 1 | ปลอดภัย |
| 12 | Stock Requests | `stock_request.menu_stock_request_root` | 3 | ปลอดภัย |
| 13 | Inventory | `stock.menu_stock_root` | 7 | เฝ้าระวัง |
| 14 | Repairs | `repair.menu_repair_order` | 4 | ปลอดภัย |
| 15 | **Maintenance** | `maintenance.menu_maintenance_title` | **6** | เฝ้าระวัง (มีชื่อซ้ำ) |
| 16 | **Project** | `project.menu_main_pm` | **10** | **เสี่ยงล้น** (มีชื่อซ้ำ) |
| 17 | Timesheets | `hr_timesheet.timesheet_menu_root` | 4 | ปลอดภัย |
| 18 | Helpdesk | `helpdesk_mgmt.helpdesk_ticket_main_menu` | 6 | เฝ้าระวัง |
| 19 | Signing | `od19_document_sign.menu_od19_document_sign_root` | 2 | ปลอดภัย |
| 20 | Employees | `hr.menu_hr_root` | 7 | เฝ้าระวัง |
| 21 | Attendances | `hr_attendance.menu_hr_attendance_root` | 6 | ปลอดภัย |
| 22 | Recruitment | `hr_recruitment.menu_hr_recruitment_root` | 3 | ปลอดภัย |
| 23 | Fleet | `fleet.menu_root` | 3 | ปลอดภัย |
| 24 | Time Off | `hr_holidays.menu_hr_holidays_root` | 5 | ปลอดภัย |
| 25 | Expenses | `hr_expense.menu_hr_expense_root` | 4 | ปลอดภัย |
| 26 | Website | `website.menu_website_configuration` | 4 | ปลอดภัย |
| 27 | Knowledge | `document_knowledge.menu_document_root` | 5 | เฝ้าระวัง (ทับซ้อน) |
| 28 | Announcements | `od19_announcement.announcement_main_menu` | 1 | ปลอดภัย |
| 29 | ISO Management | `od19_iso_document_control.menu_iso_root` | 4 | ปลอดภัย |
| 30 | To-do | `project_todo.menu_todo_todos` | 0 | — |
| 31 | User Guide | `od19_user_guide_tours.menu_od19_user_guide_root` | 1 | ปลอดภัย |
| 32 | Apps | `base.menu_management` | 4 | ปลอดภัย |
| 33 | **Settings** | `base.menu_administration` | **10** | เฝ้าระวัง (แสดงจริง 8) |
| 34 | Tests | `base.menu_tests` | 0 | — |

> **หมายเหตุ**: คอลัมน์ "จำนวนหัวข้อ" ข้างบนนับจาก raw DB (ลูกโดยตรงของ root) ซึ่ง **นับเกินจริง** ตามที่อธิบายในข้อ 2.1 — ตัวเลขที่แสดงจริงสรุปในหัวข้อ 3.1

### 3.1 จำนวนหัวข้อที่แสดงจริงบน NavBar (visible sections)

คำนวณตามกฎ `_visible_menu_ids` (นับเมนูที่ไม่ว่าง — มี action หรือเป็นแม่ของเมนูที่มี action, `active=True`; ไม่คิดสิทธิ์กลุ่ม = เพดานบนของผู้ใช้ระดับผู้ดูแล):

| แอพ | แสดงจริง | นับดิบ | สถานะ |
|---|---:|---:|---|
| Accounting | 13 | 13 | เสี่ยงล้น |
| Sales | 12 | 12 | เสี่ยงล้น |
| Project | 10 | 10 | เสี่ยงล้น |
| Settings | **8** | 10 | เฝ้าระวัง (ดิบ 2 ตัวไม่แสดง) |
| Inventory | 7 | 7 | เฝ้าระวัง |
| Employees | 6 | 7 | ปลอดภัย |
| Attendances | 6 | 6 | ปลอดภัย |
| Helpdesk | 6 | 6 | ปลอดภัย |
| Maintenance | **5** | 6 | ปลอดภัย (ดิบ 1 ตัวไม่แสดง) |
| Dashboards | **5** | 6 | ปลอดภัย |

แอพที่เหลือมี ≤ 5 ทุกตัว — รวมทั้งหมด **146 หัวข้อที่แสดงจริง / 32 แอพ**

---

## 4. เมนูที่ซ้ำ / ทับซ้อน (สิ่งที่ต้องแก้)

### 4.1 ชื่อซ้ำตรงตัวในแอพเดียวกัน — **ตรวจแล้ว: ไม่มีคู่ใดแสดงพร้อมกันจริง**

หลังตรวจตามกฎข้อ 2.1 + สิทธิ์กลุ่ม พบว่าทั้ง 3 คู่ถูกซ่อนอยู่ (ไม่ใช่ปัญหาที่ผู้ใช้เห็นในตอนนี้):

| แอพ | หัวข้อที่ซ้ำ | xmlid | แสดงจริงบน NavBar? |
|---|---|---|---|
| Project | "Projects" ×2 | `project.menu_projects` / `project.menu_projects_group_stage` | ❌ ตัวที่สองต้องมีกลุ่ม **"Use Stages on Project"** (ปัจจุบันสมาชิก 0 คน) — ถ้าเปิดใช้ในอนาคตจะซ้ำทันที → ควรเปลี่ยนชื่อเชิงป้องกัน |
| Maintenance | "Reporting" ×2 | `maintenance.menu_m_reports` (seq 3) / `maintenance.maintenance_reporting` (seq 20) | ❌ `menu_m_reports` ไม่มี action และลูก (OEE / Losses) ก็ไม่มี action → ไม่แสดงอยู่แล้ว |
| Settings | "General Settings" ×2 | `base_setup.menu_config` (seq 0) / `base.menu_config` (seq 3) | ❌ `base.menu_config` ไม่มี action/ลูก → ไม่แสดงอยู่แล้ว |
| Discuss | "Discuss" (root) + "Discuss" (ลูก) | `mail.menu_root_discuss` / `mail.main_menu_discuss` | ปกติของ Odoo (หัวข้อแรกของแอพชื่อซ้ำกับชื่อแอพ) |

### 4.2 ทับซ้อนเชิงความหมาย (ควรจัดกลุ่ม/เปลี่ยนชื่อ)

| แอพ | หัวข้อที่ทับซ้อน | ข้อเสนอ |
|---|---|---|
| Sales | `Sales Contracts` + `Revenue Recognition Schedule` + `Retentions (เงินประกันผลงาน)` | รวมเป็นหัวข้อ **"Contracts"** เดียว (มีเมนูย่อย: สัญญา / ตารางรับรู้รายได้ / เงินประกันผลงาน) |
| Sales | `Product Returns` กับ `Orders` | ย้าย Product Returns เข้าเป็นเมนูย่อยในหัวข้อ **Orders** |
| Sales | `Sales Services` + `After-Sales Reporting` | จัดกลุ่มเป็น **"After-Sales"** เดียว (ใบงานบริการ + รายงานหลังการขาย) |
| Accounting | `Cheques` + `Advance Payments` + `Petty Cash` | รวมเป็นหัวข้อ **"Treasury"** (เงินสด/เช็ค/เงินทดรอง/ petty cash) |
| Accounting | `Finance Control Board` + `Dashboard` | สองแดชบอร์ดในแอพเดียว — รวม/เปลี่ยนชื่อให้ชัด (เช่น "Finance Control Board" กับ "Journal Dashboard") |
| Accounting | `Accounting Entries` + `Review` | ตรวจว่าซ้อนกันไหม (Core เป็นผู้ให้ทั้งคู่) — พิจารณายุบ Review เข้า Entries |
| Employees | `Human Resources` (ชื่อหัวข้อ) + `Employees` (แอพ) + `Directory` | เปลี่ยนชื่อหัวข้อแรกไม่ให้ซ้ำความหมาย กับ `Employees`/`Directory` |
| Knowledge | `Browse Wiki Content` + `Pages` + `Articles` + `Documents` | รวมเป็น **"Content"** เดียว (เรียกดู/หน้า/บทความ/เอกสาร) |
| Helpdesk | `Products` ในแอพ Helpdesk | ตรวจว่าจำเป็นต้องอยู่ระดับหัวข้อหรือย้ายเข้า Configuration |
| Repairs | `Orders` + `Warranty Claims` (seq เท่ากัน 10) | จัดลำดับใหม่/รวมเป็น **"Repairs"** เดียว |
| Inventory | `Logistics Board` + `Overview` | สองหน้า "ภาพรวม" — รวมหรือเปลี่ยนชื่อให้ต่างกันชัดเจน |
| Settings | `Approval Center`, `Notifications`, `Misc Features`, `OD19 Modules` | จัดกลุ่มให้เป็นระเบียบ (ดูข้อ 5) |

---

## 5. ข้อเสนอการจัดกลุ่ม — เฉพาะแอพที่เกินกำหนด

### 5.1 Sales (12 → 9 หัวข้อ)

| ปัจจุบัน | ข้อเสนอ |
|---|---|
| Orders (group) | **Orders** — ย้าย Product Returns เข้าเป็นเมนูย่อย |
| To Invoice (group) | คงไว้ |
| Products (group) | คงไว้ |
| Sales Contracts | **Contracts** — รวม 3 เมนู: Sales Contracts + Revenue Recognition Schedule + Retentions |
| Revenue Recognition Schedule | → ย้ายเข้า Contracts |
| Retentions (group) | → ย้ายเข้า Contracts |
| Sale Projects | คงไว้ |
| Product Returns | → ย้ายเข้า Orders |
| Sales Services (group) | **After-Sales** — รวม Sales Services + After-Sales Reporting |
| Reporting (group) | คงไว้ |
| After-Sales Reporting (group) | → รวมเข้า After-Sales |
| Configuration (group) | คงไว้ (ท้ายสุด) |

ผลลัพธ์: **9 หัวข้อ** (ลด 3) — พอดีแถวเดียว

### 5.2 Accounting (13 → 10 หัวข้อ)

| ปัจจุบัน | ข้อเสนอ |
|---|---|
| Finance Control Board | รวมกับ Dashboard เป็นกลุ่ม **Dashboards** หรือเปลี่ยนชื่อให้ต่างชัดเจน |
| Dashboard (group) | → รวมเป็น **Dashboards** |
| Customers (group) | คงไว้ |
| Vendors (group) | คงไว้ |
| Accounting Entries (group) | คงไว้ |
| Review (group) | พิจารณายุบเข้า Accounting Entries |
| Assets (group) | คงไว้ |
| Cheques | **Treasury** — รวม Cheques + Advance Payments + Petty Cash |
| Advance Payments | → ย้ายเข้า Treasury |
| Petty Cash (group) | → ย้ายเข้า Treasury |
| e-Tax Invoice (group) | คงไว้ |
| Reporting (group) | คงไว้ |
| Configuration (group) | คงไว้ (ท้ายสุด) |

ผลลัพธ์: **10 หัวข้อ** (ลด 3)

### 5.3 Project (10 → 9 หัวข้อ)

| ปัจจุบัน | ข้อเสนอ |
|---|---|
| Projects | **Projects** (แก้ปัญหาชื่อซ้ำ — ดูว่าตัว `menu_projects_group_stage` ควรยุบรวม) |
| Projects (`menu_projects_group_stage`) | → ยุบ/เปลี่ยนชื่อ |
| Tasks (group) | คงไว้ |
| Project Types | **Project Master Data** — รวม Project Types + (ตัวช่วยอื่น) |
| Risk Report | จัดกลุ่มเป็น **Project Reports** ร่วมกับ P&L / data-quality |
| P&L Report | → เข้า Project Reports |
| Projects without Job Number | → เข้า Project Reports (data quality) |
| Projects without Analytic Account | → เข้า Project Reports (data quality) |
| Reporting (group) | คงไว้ |
| Configuration (group) | คงไว้ |

ผลลัพธ์: **~8–9 หัวข้อ**

### 5.4 Settings (10 → 8 หัวข้อ)

| ปัจจุบัน | ข้อเสนอ |
|---|---|
| General Settings (`base_setup.menu_config`) | เหลืออันเดียว (ลบ/ซ่อนตัวซ้ำ `base.menu_config`) |
| Users & Companies (group) | คงไว้ |
| Translations (group) | คงไว้ |
| General Settings (`base.menu_config`) | → ยุบรวม |
| Custom Shortcuts | คงไว้ |
| Notifications (group) | จัดกลุ่ม **OD19 Tools** ร่วมกับ Approval Center / Misc Features / OD19 Modules |
| Approval Center (group) | → เข้า OD19 Tools |
| OD19 Modules | → เข้า OD19 Tools |
| Misc Features (group) | → เข้า OD19 Tools |
| Technical (group) | คงไว้ (ท้ายสุด) |

ผลลัพธ์: **8 หัวข้อ**

### 5.5 Maintenance (6 หัวข้อ แต่มีชื่อซ้ำ) — เปลี่ยนชื่อ/ยุบ Reporting ตัวซ้ำ

### 5.6 Knowledge (5 หัวข้อ ทับซ้อน) — รวมเป็น Content เดียว

### 5.7 Helpdesk / Repairs / Inventory — ปรับชื่อและลำดับเล็กน้อย

---

## 6. แนวทางดำเนินการ (เมื่อได้รับอนุมัติ)

1. **ไม่แก้ไฟล์ Core** ตาม AGENTS.md — ใช้กลไก override ใน custom module
2. ขยายแนวทางเดิมของ [od19_ui_defaults](file:///c:/odoo-dev/odoo19/custom_addons/od19_ui_defaults/models/ir_ui_menu.py) หรือสร้างโมดูลใหม่ `od19_navbar_menu` โดย:
   - เปลี่ยน **ชื่อหัวข้อ** ที่ซ้ำ/กำกวม (`ir.ui.menu.name` + แปลงไทยผ่าน `update_field_translations`)
   - **รวมกลุ่ม**: สร้างหัวข้อแม่ใหม่ แล้ว `parent_id` ของเมนูเดิมย้ายเข้าไป
   - **ปรับ `sequence`** ให้หัวข้อหลักมาก่อน และ Configuration อยู่ท้ายสุด (มีกลไกนี้อยู่แล้ว)
   - ทำแบบ **idempotent** ผ่าน post-init hook + `env.ref(..., raise_if_not_found=False)` เพื่อไม่ให้ผูก dependency หนักกับทุกแอพ
3. **1 commit = 1 แอพ/1 โดเมน** ตามกฎ AGENTS.md (feature branch `feature/od19-navbar-menu`)
4. ทดสอบ: เปิดแต่ละแอพวัดว่าหัวข้อครบในแถวเดียว (หรือกด "+" แล้วเห็นครบ) บนจอ standard + จอเล็ก

---

## 7. ลำดับความสำคัญที่เสนอ

| ลำดับ | งาน | เหตุผล |
|---|---|---|
| P1 | จัดกลุ่ม **Accounting** (13 → 10): Treasury = Cheques+Advance Payments+Petty Cash, รวมแดชบอร์ด | แอพเมนูเยอะสุดและล้นจริง (หัวข้อที่แสดงจริงมากสุด) |
| P2 | จัดกลุ่ม **Sales** (12 → 9): Contracts, After-Sales, ย้าย Product Returns เข้า Orders | แอพหลักของงานขาย ล้นรองลงมา |
| P3 | จัดกลุ่ม **Project** (10 → ~8) + เปลี่ยนชื่อ **"Projects"** ตัวที่ซ้ำ (เชิงป้องกัน) | ล้น + มีชื่อซ้ำแฝงที่รอโผล่ |
| P4 | **Settings** (8 → 7): จัดกลุ่ม OD19 Tools (Notifications/Approval Center/OD19 Modules/Misc Features) | จัดบ้านให้เมนูที่โปรเจกต์เพิ่มเอง |
| P5 | Inventory (7) / Knowledge / Helpdesk / Repairs | ปรับปรุงความสวยงาม |
| (optional) | ซ่อนเมนู Core ที่ว่าง (`base.menu_config`, `maintenance.menu_m_reports`) | ไม่กระทบการแสดง (ถูกซ่อนอยู่แล้ว) — ทำเพื่อความสะอาดของข้อมูลเท่านั้น |

---

## 8. ความเสี่ยง / ข้อควรระวัง

- การย้าย `parent_id` ของเมนู Core อาจกระทบ **action/สิทธิ์ (groups_id)** ที่ผูกไว้ — ต้องย้ายทั้งก้อนพร้อม action ให้ครบ
- การเปลี่ยนชื่อเมนู Core ต้องอัปเดต **คำแปลไทย** ด้วยเสมอ (บทเรียนเดิมจาก `od19_accounting_reporting` เรื่อง `update_field_translations`)
- จำนวนหัวข้อที่แสดงจริงขึ้นกับ **ความกว้างจอ** — จอเล็กอาจยังต้องกด "+" แม้จัดกลุ่มแล้ว (ยอมรับได้ เพราะปุ่ม "+" ยังเข้าถึงครบ)
- ห้ามลบเมนู Core โดยตรง ให้ **ซ่อน (`action` ว่าง/hidden) หรือยุบรวม** เท่านั้น เพื่อความปลอดภัยเวลา Core อัปเดต
