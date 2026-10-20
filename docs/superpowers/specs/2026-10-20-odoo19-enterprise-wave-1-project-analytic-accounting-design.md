# Odoo 19 CE Wave 1: Project & Analytic Accounting

## Control Metadata
- Child spec ID: W1-PROJECT-ANALYTIC
- Wave: Wave 1 (Commercial and financial core)
- Status: Approved — decisions D1–D7 confirmed by business owner 2026-10-20; ready for implementation plan
- Owner: Commercial domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Index row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` (Wave 1 Baseline Snapshot → Project & Analytic Accounting)
- Date: 2026-10-20
- Primary readers: ฝ่ายขาย, ฝ่ายบัญชี, ฝ่ายจัดซื้อ, ผู้จัดการโครงการ, ทีมเทคนิค

## Discovery Evidence
- Current-state references (Odoo 19):
  - `custom_addons/od19_project_analytic/`
  - `custom_addons/od19_project_document_sequence/`
  - `custom_addons/od19_project_enhanced/`
  - `custom_addons/od19_sales_project_context/`
  - `custom_addons/od19_accounting_money_in_report/`
  - `custom_addons/od19_contacts_partner_roles/`
  - `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
- Legacy references (Odoo 15 baseline):
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_project/` (job_no, job_type, project_department_id, sale_person_id, analytic account creation)
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_project_form/` (job assignment form + JRXML report)
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_project_risk_report/` (project risk / P&L SQL view)
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_data_link_project/` (sale order ↔ project ↔ invoice bridge)
  - `Odoo15Backup/odoo/custom15_autoinfo/project_type/` (`project.type` hierarchical category)
  - `Odoo15Backup/odoo/odoo15_mods/dtr_project/` (project site, task category, task code, task sequence)
- Evidence coverage gaps:
  - ยังไม่มีหลักฐานเจ้าของธุรกิจยืนยันว่ารูปแบบ Job Number และ Project Type Set ของ Odoo 15 ต้องคงไว้ทั้งชุดหรือปรับ
  - ยังไม่มี profiling ข้อมูลจริงว่าโครงการเดิมมีสัดส่วน job type ใด และ department ใดถูกใช้จริง
  - ยังไม่ได้ยืนยันว่าเอกสารบังคับก่อนเข้าพื้นที่ (document required entry to work) ยังใช้อยู่ในกระบวนการปัจจุบัน
  - ยังไม่มีการวัดคุณภาพข้อมูล analytic distribution ของใบแจ้งหนี้เดิม (มี/ไม่มี/ผิดสัดส่วน)

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 Contacts Partner Roles baseline approved (`od19_is_commercial_customer`, `od19_is_project_owner`, `od19_is_contractor`)
  - Wave 1 Sales Contract Core baseline approved (`sale.order` project context)
  - Wave 1 Accounting Operational Closure baseline approved (posted move lines, AR)
  - `od19_purchase_document_sequence` baseline approved (`hr.department.od19_dept_code`, `pr_sequence_id`, `po_sequence_id`)
  - Odoo 19 core: `project`, `analytic`, `account`, `hr`, `purchase_stock`, `sale_project`
- Gate readiness:
  - Spec-ready: canonical model, job number rules, field ownership map, analytic/P&L approach และผลกระทบต่อ Sales/Purchase/Accounting ถูกนิยามชัด (เอกสารนี้ปิดประเด็นเหล่านี้)
  - Plan-ready: business owner ยืนยันคำตัดสิน D1–D7 ที่ค้างอยู่, ไม่มีความกำกวมเรื่อง field ownership และ module boundaries, test strategy เพียงพอ
  - Build-ready: implementation plan ถูกเขียนและอนุมัติ, owner-reporting impact ได้รับการยืนยัน, และยืนยันว่าจะไม่ดึง Wave 2 finance controls หรือ Wave 3 service flows เข้ามาในรอบนี้

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบ `Project & Analytic Accounting` สำหรับ Wave 1 โดยยึด **standard `project.project` ของ Odoo 19** เป็น canonical model เพียงหนึ่งเดียว ไม่สร้างโมเดลโครงการใหม่ และไม่แตะ Odoo core

เป้าหมายคือทำให้ "โครงการ" กลายเป็นศูนย์กลางที่ Sales, Purchase, และ Accounting อ้างอิงร่วมกันได้จริง ผ่าน 3 กลไกหลัก:

1. **Job Number** ที่สร้างอัตโนมัติจาก แผนก + ประเภทโครงการ + อักษรย่อผู้ขาย + ปี + เลขรัน
2. **Analytic Account** ที่ถูกสร้างและผูกกับโครงการอัตโนมัติ เพื่อให้ทุกรายการบัญชีวิ่งเข้าโครงการได้
3. **Project P&L** ที่อ่านจาก `account.analytic.line` และใช้ `analytic_profitability` ของ Odoo 19 ในการแยกรายได้กับต้นทุนโดยไม่ต้องประดิษฐ์ logic แยกเอง

## 2. เป้าหมายของ Child Spec นี้

- ทำให้ `project.project` (standard) เป็น canonical project master ของทั้งระบบ
- กำหนดกติกา Job Number เพียงชุดเดียวที่ทั้งฝ่ายขายและฝ่ายปฏิบัติการยอมรับได้
- กำหนดเจ้าของ field อย่างชัดเจน เพื่อไม่ให้มี field ซ้ำความหมายกันหลายโมดูล (ปัญหาที่พบในปัจจุบัน)
- ผูกโครงการกับ Analytic Account แบบ 1:1 เพื่อให้ P&L รายโครงการเกิดขึ้นได้จริง
- ทำให้ P&L รายโครงการอ่านได้จากข้อมูลบัญชีที่ post แล้วเท่านั้น (auditable) ไม่ใช่การประมาณจากยอดขาย
- ไม่ทำให้ Sales / Purchase / Accounting ที่ทำเสร็จแล้ว regress
- ไม่ดึง Wave 2 (finance controls) หรือ Wave 3 (service/after-sales) เข้ามาในรอบนี้

## 3. ขอบเขตของ Child Spec

### 3.1 สิ่งที่อยู่ในก้อนนี้

- การเสริม `project.project` ด้วย Job Number, ประเภทโครงการ, แผนกเจ้าของงาน, เจ้าของโครงการ, ผู้รับเหมา
- การสร้างและผูก Analytic Account อัตโนมัติต่อโครงการ
- การกำหนดชุด Project Type (Job / Server / PM / Service) และชุด Sequence ต่อแผนก
- การทำ Project P&L รายโครงการจาก `account.analytic.line`
- การทำ Project Risk / Margin report ให้สอดคล้องกับ P&L (เกณฑ์ความเสี่ยงต้องสอดคล้องกันทั้งระบบ)
- การตรวจสอบความสอดคล้อง (reconciliation) ระหว่าง Risk Report แบบเดิมที่ใช้ `analytic_distribution` กับ P&L ที่ใช้ analytic line
- การปรับ view/search/filter ของโครงการให้เห็น Job Number, แผนก, ประเภท, เจ้าของ, คู่สัญญา
- การยืนยัน compatibility กับ `od19_sales_project_context`, `od19_purchase_document_sequence`, `od19_accounting_money_in_report`, `od19_accounting_operational_closure`
- การยืนยัน compatibility กับ standard `sale_project` (โครงการที่ถูกสร้างจากใบสั่งขาย)

### 3.2 สิ่งที่ยังไม่ลงลึกในก้อนนี้

- Project Site / Project Site Database และ Task Category แบบละเอียด (ของ legacy `dtr_project`) — พิจารณาใน Wave 3/4
- เอกสารบังคับก่อนเข้าพื้นที่ (document required entry to work, JSA, สำเนาบัตรประชาชน ฯลฯ) แบบครบชุด — ต้องรอคำตัดสิน D4
- Project Revision / Project Locking (legacy ไม่มี ระบบปัจจุบันก็ไม่มี)
- Tier validation / approval workflow ของโครงการ (legacy มีเฉพาะ `dtr.project.analysis` ซึ่งไม่ใช่ `project.project`)
- JasperReports ของใบมอบหมายงาน — Wave 2 เป็นเจ้าของ Jasper foundation ตาม Dual Report Format
- ระบบ timesheet / ค่าแรง ต่อโครงการ
- การแก้ไข Odoo core หรือ `analytic_distribution` ของ core

## 4. Current-State Summary

### 4.1 สถานะจริงบน Odoo 19 (ณ 2026-10-20)

ระบบปัจจุบันมีอยู่แล้ว 4 โมดูลที่แตะโดเมนนี้:

| โมดูล | บทบาทปัจจุบัน |
| --- | --- |
| `od19_project_analytic` | เจ้าของ field `job_no`, `od19_department_id`, `project_owner_id`, `contractor_ids` + auto-create analytic account |
| `od19_project_document_sequence` | เจ้าของ field `od19_project_type`, `od19_sale_person_id`, `od19_task_code` + sequence ต่อแผนก + Job Number algorithm |
| `od19_project_enhanced` | เจ้าของ `od19_project_type_id` (Project Category), responsible/coordinator, scope of work, `od19.project.risk.report` |
| `od19_sales_project_context` | เชื่อม `sale.order` → `project.project` (standard) + owner consistency guard |

ประเด็นสำคัญที่ต้องบันทึก:

- **ข้อความใน index ล้าสมัยแล้ว**: ระบุว่า `od19_sales_project_context` ใช้ custom model `od19.sales.project` — ตรวจสอบแล้วไม่จริง ปัจจุบัน `sale.order.od19_project_id` ชี้ `project.project` ตรง ๆ ดังนั้น scope "bridge to standard project" **เสร็จแล้ว**
- **Job Number ใช้ได้จริงแล้ว** (Job/Server/PM/Service × แผนก × อักษรย่อ × ปี)
- **Analytic account ถูกสร้างอัตโนมัติแล้ว** เมื่อสร้างโครงการ
- **Project P&L รายโครงการยังไม่มี** — สิ่งที่ใกล้ที่สุดคือ `od19.project.risk.report` ซึ่งเป็น SQL view ที่อ่านจาก `analytic_distribution` ของ `sale_order_line`, `account_move_line`, `hr_expense`, `purchase_order_line` โดยตรง ไม่ได้อ่านจาก `account.analytic.line`

### 4.2 ช่องว่างเทียบกับ legacy Odoo 15

| ประเด็น | Odoo 15 legacy | Odoo 19 ปัจจุบัน | สถานะ |
| --- | --- | --- | --- |
| Job Type | `job`, `pm`, `service`, `sale` (sale ใช้ sequence ของ salesperson ไม่ใช้แผนก) | `job`, `server`, `pm`, `service` | **ต่างกัน** (ดู D1) — `server` ถูกถอดออกตามคำสั่งเจ้าของธุรกิจ 2026-10-20 |
| Job number algorithm | แผนก×type หรือ salesperson sequence | แผนก×type + แทรกอักษรย่อก่อนปี | ยกระดับแล้ว |
| ชื่อโครงการ | `job_no + ':' + name` | ไม่ผสม | **ต่างกัน** (ดู D3) |
| แผนกเจ้าของงาน | `project_department_id` (required, fallback `hr.dep_administration`) | `od19_department_id` (optional ที่ model, default จากพนักงาน) | อ่อนลงโดยเจตนาเพื่อ compatibility |
| Project P&L | `autoinfo.project.risk.report` 12 คอลัมน์ (contract, invoiced, actual_cost, committed_cost, total_cost, margin, margin_pct, billed_pct, cost_pct, overdue_ar, risk_score, risk_level) | `od19.project.risk.report` 7 คอลัมน์ ขาด total_cost, margin, billed_pct, cost_pct, partner, due date | **ยังห่าง** |
| เกณฑ์ risk | margin<15 → 40, overdue>0 → 30, เลยกำหนด → 30; high ≥70, medium ≥40 | margin<15 → 40, overdue>0 → 30, เลยกำหนด → 30; high ≥60, medium ≥30 | **ไม่ตรงกัน** (ดู D2) |
| เอกสารบังคับก่อนเข้าพื้นที่ | ~25 boolean/char fields | มีเพียง text 2 ช่อง | **ยังห่าง** (ดู D4) |
| ใบมอบหมายงาน | JRXML (Jasper) | QWeb | Wave 2 owns Jasper |
| Project Site / DB / Task Category | มีใน `dtr_project` | ไม่มี | Wave 3/4 |

## 5. Keep / Refactor / Replace / Retire

### 5.1 Keep
- Keep `project.project` (standard) เป็น canonical project master
- Keep แนวทาง Job Number = แผนก × ประเภท × อักษรย่อ × ปี × เลขรัน (ตรงกับ legacy)
- Keep แนวทาง Analytic Account 1:1 ต่อโครงการ
- Keep partner roles (`od19_is_project_owner`, `od19_is_contractor`) เป็นตัวกรอง ไม่ใช่ model ใหม่
- Keep sequence ต่อแผนกบน `hr.department` และอักษรย่อบน `res.users`
- Keep แนวคิด Risk Report แบบ SQL view ที่อ่านข้อมูลจริง

### 5.2 Refactor
- Refactor Risk Report ให้เป็นส่วนหนึ่งของ P&L เดียวกัน ไม่ใช่สูตรคู่ขนานที่ให้ผลไม่ตรงกัน
- Refactor เกณฑ์ risk ให้เป็นค่าที่ประกาศไว้ที่เดียวและสอดคล้องกันทุกจุด
- Refactor Job Number ให้มีกติกาเดียวเรื่องค่าเริ่มต้นของ Job Type และแผนก
- Refactor `od19_accounting_money_in_report` ให้ใช้ `od19_project_type` เป็นมิติ Job Type แทน field ที่ไม่มีอยู่แล้ว (ทำแล้วในรอบนี้)

### 5.3 Replace
- Replace การอ่านข้อมูล P&L จาก `analytic_distribution` ของเอกสารต้นทาง ด้วยการอ่านจาก `account.analytic.line` ที่อ้าง `account_id` ของโครงการ (auditable กว่า และตรงกับสัญญาณบัญชีจริง)
- Replace การใช้เกณฑ์ risk ซ้ำสองชุด ด้วยชุดเดียว

### 5.4 Retire
- Retire ความคิดที่จะสร้างโมเดลโครงการใหม่ซ้อน `project.project` (ไม่เคยมีจริงใน Odoo 19 และห้ามสร้าง)
- Retire field ที่ซ้ำความหมายกันหลายเจ้าของ (`job_type` เดิมถูกถอดออกแล้ว)
- Retire การประกาศ `od19_department_id` ซ้ำหลายโมดูล (ปัจจุบันเหลือเจ้าของเดียว)

## 6. Future-State Design

### 6.1 Canonical Model

`project.project` คือ canonical model เพียงหนึ่งเดียว โครงการถูกสร้างได้จาก 3 ทางเท่านั้น:

1. สร้างตรงจากเมนู Project
2. สร้างจากใบสั่งขายผ่าน standard `sale_project`
3. สร้างผ่าน API/import โดยต้องมี `od19_department_id` และ `od19_project_type` ถ้าต้องการ Job Number

ห้ามสร้าง model โครงการใหม่ และห้ามแก้ `project.project` ใน core

### 6.2 Field Ownership Map (ข้อบังคับ)

เพื่อยุติปัญหา field ซ้ำความหมาย ให้ถือตารางนี้เป็นสัญญา:

| Field | Model | เจ้าของ (ประกาศที่เดียว) | ผู้ใช้ |
| --- | --- | --- | --- |
| `job_no` | `project.project` | `od19_project_analytic` | document_sequence (สร้างค่า), enhanced (รายงาน) |
| `od19_department_id` | `project.project` | `od19_project_analytic` | document_sequence, enhanced, tours |
| `project_owner_id` | `project.project` | `od19_project_analytic` | sales_project_context, enhanced, partner roles hook |
| `contractor_ids` | `project.project` | `od19_project_analytic` | enhanced, partner roles hook |
| `od19_project_type` | `project.project` | `od19_project_document_sequence` | money_in_report, enhanced, tours |
| `od19_sale_person_id` | `project.project` | `od19_project_document_sequence` | document_sequence |
| `od19_project_type_id` | `project.project` | `od19_project_enhanced` | enhanced, job assignment report |
| `od19_responsible_person_ids` / `od19_coordinator_ids` | `project.project` | `od19_project_enhanced` | enhanced |
| `od19_scope_of_work` / `od19_document_requirements` | `project.project` | `od19_project_enhanced` | enhanced |
| `od19_task_code` | `project.task` | `od19_project_document_sequence` | document_sequence |
| `od19_project_type_id` (task) | `project.task` | `od19_project_enhanced` | enhanced |
| sequence fields | `hr.department` | `od19_purchase_document_sequence` (`od19_dept_code`) / `od19_project_document_sequence` (project sequences) | ทั้งโดเมน |
| `od19_initials` | `res.users` | `od19_project_document_sequence` | job number |

กติกา: โมดูลที่ depend ไม่ครบห้ามประกาศซ้ำเด็ดขาด ถ้าจำเป็นต้องใช้ ให้เพิ่ม dependency แทน

### 6.3 Job Number Contract

รูปแบบ: `{TYPE_PREFIX}{DEPT_CODE}{INITIALS}{YY}-{RUNNING}` ตัวอย่าง `JBNV26-0001`

- `TYPE_PREFIX`: `J` (Job), `PM` (Preventive Maintenance), `S` (Service), `JS` (Sales)
- `DEPT_CODE`: `hr.department.od19_dept_code` (เจ้าของ `od19_purchase_document_sequence`)
- `INITIALS`: `res.users.od19_initials` ของ `od19_sale_person_id`
- `YY`: ปี 2 หลักของ `date_start`
- Sequence ถูกกำหนดต่อแผนกต่อประเภท (`project_job_*`, `project_pm_*`, `project_service_*`); ประเภท `sale` ใช้ `res.users.project_sale_sequence_id` ของ salesperson ไม่ใช่ sequence ของแผนก

> **การถอด Job Type `server` (คำสั่งเจ้าของธุรกิจ 2026-10-20):** ชุด Job Type ของ Odoo 19 ต้องตรงกับ legacy คือ `job`, `pm`, `service`, `sale` เท่านั้น — `server` และ `project_server_sequence_id` / `project.server.*` ถูกถอดออกทั้งหมดในรอบนี้ (ตรวจ DB `odoo19_pdev` แล้ว: ไม่มีโครงการหรือแผนกใดใช้ type/sequence นี้)

กติกาความถูกต้อง:

- `job_no` ไม่ unique ที่ฐานข้อมูลไม่ได้ — ต้องมี `unique(job_no)` constraint ระดับ DB
- `job_no` ต้อง optional ที่ model (เพื่อให้ `sale_project` และ core สร้างโครงการได้) แต่ required ที่ UI
- ถ้าสร้างโครงการโดยไม่มีแผนกหรือไม่มี sequence ให้ Job Number ว่างได้ แต่ต้องไม่ทำให้ create ล้มเหลว
- การเปลี่ยนแผนก/ประเภท/ผู้ขาย ต้องไม่เปลี่ยน Job Number ของโครงการที่มีอยู่แล้ว

### 6.4 Project Owner และ Contractor

- `project_owner_id` เป็น Many2one `res.partner` กรองด้วย `od19_is_project_owner`
- `contractor_ids` เป็น Many2many `res.partner` กรองด้วย `od19_is_contractor`
- ต้องมี validation ว่า partner ที่เลือกมี role จริง (ไม่พึ่ง domain ที่ UI เท่านั้น เพราะ import/API ข้าม domain ได้)
- `sale.order.od19_project_owner_id` ต้องตรงกับ `project.project.project_owner_id` เสมอ (มีอยู่แล้ว) และห้ามผ่อนคลายกฎนี้

### 6.5 Analytic Account Integration

- สร้าง `account.analytic.account` อัตโนมัติ 1 ใบต่อ 1 โครงการ เมื่อ `account_id` ยังว่าง
- ชื่อ analytic account ใช้ `job_no` ก่อน ถ้าไม่มีให้ใช้ชื่อโครงการ
- ผูกกับ analytic plan ที่ชื่อว่า `Projects` ถ้าหาไม่พบให้ fallback เป็น plan แรก และต้อง log/รายงานให้ผู้ดูแลทราบเพื่อไม่ให้เงียบ
- ถ้า core (ผ่าน `sale_project`) สร้าง analytic account ให้แล้ว ระบบต้องใช้ใบนั้นและไม่สร้างซ้ำ
- **ห้ามเขียนทับ** พฤติกรรม `project.project.write()` ของ core ที่ sync ชื่อ analytic account ตามชื่อโครงการ

### 6.6 Project P&L (หัวใจของก้อนนี้)

**หลักการ:** P&L รายโครงการต้องอ่านจาก **`account.analytic.line` ที่ผูกกับ `account_id` ของโครงการ** และต้องอ้างเฉพาะรายการที่ **post แล้ว** เท่านั้น เพื่อให้ตรงกับสัญญาณบัญชีจริงและตรวจสอบย้อนกลับได้

เหตุผลเชิงเทคนิคที่ทำให้ทำได้บน Odoo 19 CE โดยไม่ต้อง custom logic แยก:

- `account.analytic.line.move_line_id` (Many2one `account.move.line`) มีอยู่จริงใน core → ใช้ตรวจสถานะการ post และหาข้อมูลเอกสารต้นทาง
- `account.analytic.line.general_account_id` (related `move_line_id.account_id`, stored) มีอยู่จริง → ใช้รู้ว่ามาจากบัญชี General ใด
- `account.analytic.line.analytic_profitability` เป็น Selection ที่ core compute ให้แล้ว: `revenue` / `loss` / `uncategorized` โดยดูจาก `general_account_id.account_type` (`income*` → revenue, `expense*`/`asset_*` → loss) → **นี่คือวิธีแยกรายได้กับต้นทุนแบบ Odoo-native ที่ต้องใช้ แล้วห้ามประดิษฐ์เกณฑ์เอง**
- เครื่องหมายของ `amount`: `amount = -balance × distribution/100` ดังนั้นรายได้ (credit) ให้ `amount` บวก และต้นทุน (debit) ให้ `amount` ลบ

**นิยามตัวชี้วัด:**

| ตัวชี้วัด | สูตร | ที่มา |
| --- | --- | --- |
| Revenue | `SUM(amount)` ของบรรทัดที่ `analytic_profitability = 'revenue'` | analytic line, posted |
| Cost | `-SUM(amount)` ของบรรทัดที่ `analytic_profitability = 'loss'` | analytic line, posted |
| Gross Margin | Revenue − Cost | คำนวณ |
| Margin % | Gross Margin ÷ Revenue × 100 | คำนวณ, ป้องกันการหารศูนย์ |
| Uncategorized | `SUM(amount)` ของบรรทัดที่ `analytic_profitability = 'uncategorized'` | ต้องแสดงแยก ห้ามเงียบ |
| Contract Amount | ยอดใบสั่งขายที่ผูกโครงการและ state เป็น `sale`/`done` | sale order |
| Invoiced Amount | ยอดใบแจ้งหนี้ลูกค้าที่ post แล้วที่ผูกโครงการ | account move |
| Committed Cost | มูลค่า PO ที่สั่งแล้วแต่ยังไม่รับรู้ | purchase order |
| Overdue AR | ยอดคงค้างเกินกำหนดของใบแจ้งหนี้ที่ผูกโครงการ | account move |

**ข้อกำหนดสำคัญ:**

- ต้องแสดงยอด `uncategorized` แยกเสมอ เพราะถ้ามีบรรทัดที่จัดประเภทไม่ได้ กำไรจะผิดโดยไม่มีใครรู้
- P&L ต้องกรองตามบริษัท (multi-company) และตามช่วงวันที่ได้
- P&L และ Risk Report ต้องใช้ชุดตัวเลขชุดเดียวกัน (ไม่ให้สองรายงานให้กำไรไม่ตรงกัน)

### 6.7 Risk Score Contract (ชุดเดียว)

Risk score ต้องประกาศไว้ที่เดียวและใช้ร่วมกันทั้ง P&L และ Risk Report:

| เงื่อนไข | คะแนน |
| --- | --- |
| Margin % < 15 | 40 |
| Overdue AR > 0 | 30 |
| เลยกำหนดส่งมอบ | 30 |

ระดับ: `high` ≥ 70, `medium` ≥ 40, `low` < 40 (คะแนนเต็ม 100)

> หมายเหตุ: ค่าระดับปัจจุบันของ Odoo 19 ใช้ 60/30 ซึ่งไม่ตรงกับ legacy และไม่ตรงกับช่วงคะแนน 100 — ต้องแก้ให้เป็นชุดเดียว (ดู D2)

และ **ต้องไม่ใช้ non-stored computed field ใน `_order`** (บทเรียนจาก Odoo 19: ทำให้เกิด invalid SQL)

### 6.8 Module Boundaries

- `od19_project_analytic` = field + analytic account + constraint ของโครงการ
- `od19_project_document_sequence` = ประเภทโครงการ + sequence + Job Number + Task code
- `od19_project_enhanced` = category, responsible/coordinator, scope, risk report, job assignment report
- `od19_sales_project_context` = ความสัมพันธ์ sale order ↔ project
- Project P&L: **ต้องตัดสินว่าจะเป็นส่วนหนึ่งของ `od19_project_enhanced` (ต่อยอด risk report) หรือเป็นโมดูลใหม่ `od19_project_pnl`** (ดู D5) — ห้ามสร้าง P&L ซ้ำสองที่

## 7. Reporting และ KPI Needs

รายงานที่ต้องมีหลังปิดก้อนนี้:

1. **Project P&L** ต่อโครงการ ต่อช่วงวันที่: Revenue, Cost, Gross Margin, Margin %, Uncategorized
2. **Project Risk / Margin Report**: รวม P&L + contract + invoiced + committed + overdue + risk score/level
3. **Job Assignment Report** (มีอยู่แล้วเป็น QWeb): Job No, ลูกค้า, แผนก, Project Category, ผู้รับผิดชอบ, ผู้ประสานงาน, ผู้รับเหมา, Scope of Work, เอกสารที่ต้องใช้

KPI ขั้นต่ำ:

- จำนวนโครงการที่ยังไม่มี Analytic Account (ต้องเป็นศูนย์)
- จำนวนโครงการที่ยังไม่มี Job Number
- มูลค่า Uncategorized ต่อโครงการ (ใช้เป็นตัวชี้วัดคุณภาพข้อมูล analytic distribution)
- Margin % ต่อโครงการ และสัดส่วนโครงการที่ Margin < 15
- จำนวนโครงการที่เลยกำหนดส่งมอบและมีลูกหนี้ค้าง

ข้อกำหนดของรายงานที่พิมพ์ออกจากระบบ: ต้องทำทั้ง Odoo 19 Native (QWeb) และ Odoo 15 Legacy Compatible (JasperReports) ตาม Dual Report Format — ส่วน Jasper foundation อยู่ใน Wave 2 จึงให้ส่งมอบ QWeb ในก้อนนี้และบันทึก Jasper เป็นงานค้างของ Wave 2

## 8. Security และ Approval Model

- ใช้ `project.group_project_user` และ `project.group_project_manager` เป็นแกนของ access rights
- `od19.project.risk.report` และ P&L: อ่านได้ด้วย `project.group_project_user` เขียนไม่ได้เลย
- โครงการที่มีข้อมูลบัญชีแล้ว: ห้ามลบ ถ้าจำเป็นให้ archive
- ห้ามสร้าง approval workflow ของโครงการใน Wave 1
- การเปลี่ยน Job Number ของโครงการที่มีอยู่แล้วต้องไม่เกิดขึ้นจาก automation ต้องมีคนสั่งเท่านั้น
- ชื่อกลุ่มและ access right ต้องมีความหมาย ห้ามปล่อยว่าง และห้ามตั้งชื่อซ้ำข้ามโมดูล (บทเรียนจากระบบปัจจุบัน)

## 9. Migration Assumptions

- ระบบ Odoo 15 เป็น reference เชิงธุรกิจ ไม่ใช่ของที่ย้ายตรงตัว
- ข้อมูลโครงการเดิมต้องถูก map เป็น `project.project` + `od19_department_id` + `od19_project_type` และต้องสร้าง analytic account ให้ครบก่อนเริ่มใช้งาน P&L
- Job Number เดิมจาก Odoo 15 ต้องถูกนำมาใช้เป็นค่าตั้งต้น (`job_no` ที่ import) เพื่อไม่ให้เอกสารเก่าและใหม่ขาดความต่อเนื่อง
- ต้องมี data-cleansing queue สำหรับโครงการที่ map แผนก/ประเภทไม่ได้
- ต้องตรวจก่อน cutover ว่าใบแจ้งหนี้ที่ผูกโครงการมี `analytic_distribution` ชี้ analytic account ของโครงการจริง ถ้าไม่มี P&L จะขาดรายได้
- รายละเอียด migration script ให้อยู่ใน implementation plan / migration workstream แยก

## 10. Training Impact

ผู้ใช้ที่ต้องอบรม:

- ฝ่ายขาย: ต้องตั้งประเภทโครงการและแผนกให้ถูกตั้งแต่สร้างโครงการ เพราะมีผลกับ Job Number โดยตรง; เข้าใจว่าอักษรย่อของตนเองถูกใช้ในเลข Job
- ฝ่ายบัญชี: ต้องเข้าใจว่า P&L รายโครงการมาจาก analytic line, ต้องตรวจ `uncategorized` และต้องรู้ว่าใบแจ้งหนี้ที่ไม่มี analytic distribution จะไม่เข้า P&L
- ฝ่ายจัดซื้อ: ต้องใส่ analytic distribution / โครงการลงใน PO line เพื่อให้ Committed Cost ถูกต้อง
- ผู้จัดการโครงการ: เข้าใจความต่างของ Risk Score และ Margin และอ่าน P&L ได้
- ผู้ดูแลระบบ: การตั้งค่า sequence ต่อแผนก, `od19_dept_code`, และ `od19_initials`

## 11. Test Strategy

ต้องมี test อย่างน้อย 4 กลุ่ม:

1. **Job Number**: รูปแบบต่อประเภท × แผนก, การแทรกอักษรย่อก่อนปี, ความไม่ซ้ำ, กรณีไม่มีแผนก/ไม่มี sequence, การไม่เปลี่ยนเลขเมื่อแก้ข้อมูลภายหลัง
2. **Analytic Account**: สร้างอัตโนมัติ, ไม่สร้างซ้ำเมื่อ core สร้างให้แล้ว, ชื่อ analytic ตาม job_no, fallback plan
3. **Project P&L**: แยกรายได้/ต้นทุนจาก `analytic_profitability` ถูกต้องพร้อมเครื่องหมายถูก, ตัด draft ออก, นับ `uncategorized` แยก, multi-company, ช่วงวันที่, หารศูนย์
4. **Compatibility**: `sale_project` สร้างโครงการได้โดยไม่มี Job Number, `od19_sales_project_context` guard ยังทำงาน, Risk Report และ P&L ให้ตัวเลขสอดคล้องกัน, `_order` ไม่มี non-stored field, test ของ `od19_accounting_money_in_report` ยังผ่าน

## 12. Known Unknowns และคำตัดสินที่ต้องขออนุมัติ

| ID | ประเด็น | ทางเลือก | ผลกระทบ |
| --- | --- | --- | --- |
| D1 | legacy มี Job Type `sale` (ใช้ sequence ของ salesperson ไม่ใช้แผนก) แต่ Odoo 19 ใช้ `server` แทน | (ข) เพิ่ม `sale` กลับเพื่อรองรับงานขายตรง + ถอด `server` ออกให้ตรง legacy | **อนุมัติ (ข)** — `sale` ได้รับอนุมัติเป็น D1 และ `server` ถูกถอดออกตามคำสั่งเจ้าของธุรกิจ 2026-10-20 |
| D2 | เกณฑ์ risk ปัจจุบัน (high ≥60, medium ≥30) ไม่ตรง legacy (≥70, ≥40) และไม่ตรงช่วงคะแนน 100 | (ก) แก้เป็น 70/40 ตาม legacy (ข) คง 60/30 | ถ้าไม่แก้ ตัวเลขความเสี่ยงจะไม่ต่อเนื่องจากระบบเดิม |
| D3 | legacy ตั้งชื่อโครงการเป็น `job_no + ':' + name` | (ก) ไม่ผสม (ตามปัจจุบัน) (ข) ผสมแบบ legacy | มีผลกับความคุ้นเคยของผู้ใช้และ search |
| D4 | เอกสารบังคับก่อนเข้าพื้นที่ (~25 ฟิลด์ใน legacy) | (ก) ไม่อยู่ใน Wave 1 (ข) ยกมาทั้งชุด | ถ้าดึงมาจะทำให้ก้อนนี้ใหญ่ขึ้นมากและต้องกำหนดเจ้าของฟิลด์ใหม่ |
| D5 | Project P&L อยู่ใน `od19_project_enhanced` หรือโมดูลใหม่ `od19_project_pnl` | (ก) ต่อยอดใน enhanced (ข) แยกโมดูลใหม่ | แยกโมดูลใหม่ทำให้ขอบเขตชัด แต่เพิ่ม dependency |
| D6 | P&L อ่านจาก `analytic_distribution` (แบบ risk report เดิม) หรือ `account.analytic.line` | (ก) `account.analytic.line` + `analytic_profitability` (ข) คงแบบเดิม | (ก) auditable และแยก revenue/cost ได้ถูกต้อง (ข) เสี่ยงกำไรไม่ตรงกับบัญชี |
| D7 | โครงการที่ไม่มี Analytic Account จะทำอย่างไรกับ P&L | (ก) P&L แสดง 0 พร้อมเตือน (ข) บังคับสร้าง analytic ก่อนปิดงวด | มีผลกับ KPI คุณภาพข้อมูล |

### 12.1 คำตัดสินที่อนุมัติแล้ว (2026-10-20)

| ID | คำตัดสิน | ผลบังคับต่อการ implement |
| --- | --- | --- |
| D1 | **เพิ่ม Job Type `sale` กลับ** ตาม legacy | เพิ่ม `('sale', 'Sales')` ใน `project.project.od19_project_type`; Job Number ของประเภท `sale` ใช้ sequence ของ salesperson (`res.users`/employee) ไม่ใช้ `hr.department.od19_dept_code`; ถ้าไม่มี salesperson หรือไม่มี sequence ต้อง raise ValidationError ให้ผู้ใช้ตั้งค่าก่อน (ห้าม fallback เงียบ) |
| D2 | **แก้ risk threshold เป็น high ≥ 70, medium ≥ 40** | แก้ `_compute_risk_level` ใน `od19.project.risk.report`; ต้องมี test ครอบเส้นแบ่ง 39/40 และ 69/70; ต้องตรวจว่าไม่มีจุดอื่นที่ hardcode 60/30 |
| D3 | **ไม่ผสม `job_no` นำหน้า name** (คงพฤติกรรมปัจจุบัน) | ห้ามแก้ `name` ของโครงการเป็น `job_no + ':' + name`; ให้ `display_name`/search ใช้ field `job_no` แยก |
| D4 | **เอกสารบังคับก่อนเข้าพื้นที่ไม่อยู่ใน Wave 1** | ไม่ดึง ~25 ฟิลด์จาก `autoinfo_project_form` เข้ามาในรอบนี้; บันทึกเป็นงานค้าง Wave 3/4 |
| D5 | **Project P&L ต่อยอดใน `od19_project_enhanced`** | ห้ามสร้างโมดูล `od19_project_pnl`; เพิ่ม logic P&L ในโมดูลเดิม และให้ Risk Report ใช้ตัวเลขชุดเดียวกัน |
| D6 | **อ่านจาก `account.analytic.line` + `analytic_profitability`** | ห้ามใช้ `analytic_distribution` ของเอกสารต้นทางเป็นแหล่ง P&L; ต้องกรองเฉพาะบรรทัดที่ post แล้ว |
| D7 | **P&L แสดง 0 พร้อมคำเตือน** เมื่อโครงการไม่มี Analytic Account | ต้องมีตัวชี้วัด "จำนวนโครงการที่ยังไม่มี Analytic Account" เป็น KPI คุณภาพข้อมูล ห้ามบังคับสร้าง analytic แบบ blocking |

## 13. Gate Readiness Summary

### 13.1 Spec-ready
ถือว่า spec-ready เมื่อ:
- canonical model ยืนยันเป็น `project.project` แล้ว ✅
- field ownership map ถูกตรึงแล้ว ✅
- Job Number contract และ P&L contract ถูกนิยามชัด ✅
- ผลกระทบต่อ Sales / Purchase / Accounting ถูกระบุแล้ว ✅

### 13.2 Plan-ready
ถือว่า plan-ready เมื่อ:
- business owner ยืนยันคำตัดสิน D1–D7 ✅ (2026-10-20)
- ไม่มีความกำกวมเรื่องเจ้าของ P&L (D5) และแหล่งข้อมูล P&L (D6) ✅
- test strategy ได้รับการยอมรับจาก technical supervisor ✅

### 13.3 Build-ready
ถือว่า build-ready เมื่อ:
- implementation plan ถูกเขียนและอนุมัติ
- owner-reporting impact ถูกยืนยันแล้ว
- ยืนยันชัดว่าจะไม่ดึง Wave 2 finance controls และ Wave 3 service flows เข้ามาในรอบนี้

### 13.4 Current Checkpoint
- โดเมนนี้มี field/sequence/analytic ทำงานอยู่แล้วบางส่วน และส่วนที่พังจากการ refactor ถูกซ่อมในรอบนี้ ✅
- ยืนยันด้วยการรันเทสต์ 2026-10-20: `od19_project_analytic` 6/6, `od19_project_document_sequence` 8/8, `od19_sales_project_context` 4/4, `od19_accounting_money_in_report` 23/23 (0 failed, 0 errors) ✅
- แก้บั๊กที่พบบอกขอบเขต: `od19_accounting_payment_fee` override `_prepare_move_line_default_vals()` ไม่รับ kwarg `force_balance` ของ Odoo 19 ทำให้ post payment ที่มี write-off ล้มเหลว ✅
- ช่องว่างที่เหลือคือ Project P&L (D5, D6) และความสอดคล้องของ risk threshold (D2) ซึ่งถูกกำหนดคำตัดสินแล้วและรอลงมือใน implementation plan

## 14. คำตัดสินของ Child Spec นี้

Wave 1 - Project & Analytic Accounting ควรปิดช่องว่างด้วยการ **เสริม standard `project.project` ต่อ ไม่รื้อโครงเดิม ไม่สร้างโมดูลโครงการใหม่** และทำให้ P&L รายโครงการเกิดขึ้นจาก `account.analytic.line` โดยใช้ `analytic_profitability` ของ Odoo 19 ซึ่งเป็นเส้นทางที่ auditable, ตรงกับมาตรฐาน Odoo/OCA, และไม่ต้องประดิษฐ์เกณฑ์แยกรายได้/ต้นทุนเอง

แนวทางนี้สมดุลที่สุดระหว่างความเร็วในการส่งมอบ ความเสถียรของ architecture และความพร้อมสำหรับ Wave 2 และ Wave 3 ที่จะต่อยอดจากตัวเลขโครงการชุดเดียวกัน
