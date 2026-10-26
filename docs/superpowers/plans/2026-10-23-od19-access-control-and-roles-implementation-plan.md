# OD19 Access Control & User Roles — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโครงสร้างสิทธิ์การเข้าถึง Odoo 19 ด้วยสองแกน (บทบาท = `res.users.role` จาก OCA, แผนก = record rule) โดยแยกเป็น 2 โมดูลเพื่อตัด dependency วน

**Architecture:** Layer 1 `od19_security_roles` (privilege + กลุ่มกลาง 4 ตัว + `res.users.od19_department_id` + cron mirror + ไม่รู้จักโมดูลธุรกิจ) → Layer 2 `od19_role_catalog` (สร้าง `res.users.role` ~40 บทบาทเป็น data เท่านั้น และผูก `implied_ids` กับกลุ่มธุรกิจ) → โมดูลธุรกิจเพิ่ม department record rule (เฟส B)

**Tech Stack:** Odoo 19 Enterprise, Python 3.12, OCA `base_user_role` 19.0.1.3.1, XML data, `TransactionCase` tests

**Spec:** [2026-10-23-od19-access-control-and-roles-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-10-23-od19-access-control-and-roles-design.md)

**Decisions ที่ยืนยันแล้ว:** D1 เฟส A→B→C · D2 บทบาท=หน้าที่/แผนก=rule · D3 hr.employee เป็นแหล่งความจริง · D4 Role Matrix §7 ของสเปก · D5 rule เฉพาะ 11 โมเดล · D6 ไม่ auto-map · D7 แยก 2 โมดูล · D8 วงเงินบน res.company · D9 แผนกของตัวเอง

---

## Test / Run Convention

- Python venv: `c:\odoo-dev\odoo19\venv19\Scripts\python.exe`
- Odoo binary: `c:\odoo-dev\odoo19\odoo-bin`
- Config: `c:\odoo-dev\odoo19\odoo.conf` · DB: `odoo19_pdev` (เดียวเท่านั้น)

ติดตั้ง + รันเทสต์ Layer 1:

```powershell
Set-Location c:\odoo-dev\odoo19
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev `
  -i od19_security_roles --test-enable --test-tags /od19_security_roles `
  --stop-after-init --no-http
```

ติดตั้ง Layer 2 (ต้องมีโมดูลธุรกิจครบก่อน):

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev `
  -i od19_role_catalog --stop-after-init --no-http
```

> **ข้อควรระวัง:** ก่อนรันทุกครั้งให้ปิด Odoo service ที่รันอยู่ เพื่อไม่ให้แย่ง DB

---

## File Structure

**สร้างใหม่ — `custom_addons/od19_security_roles/`**

| ไฟล์ | หน้าที่ |
|---|---|
| `__manifest__.py` | depends `["base", "base_user_role", "hr"]` + data list |
| `__init__.py` | import models |
| `models/__init__.py` | import ลำดับ model |
| `models/res_users.py` | `od19_department_id`, `od19_department_code`, sync + guard |
| `models/hr_employee.py` | hook mirror แผนกไปยัง user |
| `models/hr_department.py` | `od19_member_user_ids` |
| `data/od19_security_role_privilege.xml` | privilege "บทบาท OD19" |
| `data/ir_cron_data.xml` | cron ตรวจสอบ/ซ่อม mirror แผนก |
| `security/od19_security_groups.xml` | กลุ่มกลาง 4 ตัว |
| `security/ir.model.access.csv` | ACL ของโมดูล |
| `views/res_users_views.xml` | เพิ่มฟิลด์แผนกในหน้าผู้ใช้ |
| `views/role_menus.xml` | เมนู Settings → Roles |
| `tests/__init__.py` | import test |
| `tests/common.py` | helper สร้างแผนก/พนักงาน/ผู้ใช้ |
| `tests/test_roles_install.py` | ตรวจ privilege + กลุ่มกลาง |
| `tests/test_department_sync.py` | ตรวจ mirror + cron |
| `tests/test_role_assignment.py` | ตรวจการมอบ/ถอน role |
| `i18n/th.po` | คำแปลไทย |

**สร้างใหม่ — `custom_addons/od19_role_catalog/`**

| ไฟล์ | หน้าที่ |
|---|---|
| `__manifest__.py` | depends ทุกโมดูลธุรกิจที่ถูกอ้าง + `od19_security_roles` |
| `data/od19_roles_governance.xml` | ครอบครัว A/B/C |
| `data/od19_roles_operations.xml` | ครอบครัว D/E/F |
| `data/od19_roles_backoffice.xml` | ครอบครัว G/H/I/J |
| `tests/test_role_catalog.py` | ตรวจว่า role ทุกตัวโหลดได้ + implied group ตรง matrix |

---

## สัญญากลาง (Freeze ก่อนเริ่มทุก task)

| องค์ประกอบ | ชื่อที่ล็อก |
|---|---|
| Privilege | `od19_security_roles.od19_role_privilege` |
| กลุ่ม scope แผนก | `od19_security_roles.group_od19_department_scope` |
| กลุ่มเห็นทุกแผนก | `od19_security_roles.group_od19_department_all` |
| กลุ่มจัดการบทบาท | `od19_security_roles.group_od19_role_manager` |
| กลุ่มอนุมัติเครดิต | `od19_security_roles.group_od19_credit_approver` |
| ฟิลด์แผนกบนผู้ใช้ | `res.users.od19_department_id` |
| ชื่อ role xml id | `role_<family>_<role>` ใน namespace ของ `od19_role_catalog` |

---

# เฟส A — โมดูล Layer 1 + Layer 2

## Task 1: Scaffolding `od19_security_roles` + ติดตั้งผ่าน

**Files:**
- Create: `custom_addons/od19_security_roles/__manifest__.py`
- Create: `custom_addons/od19_security_roles/__init__.py`
- Create: `custom_addons/od19_security_roles/models/__init__.py`
- Create: `custom_addons/od19_security_roles/security/ir.model.access.csv`
- Create: `custom_addons/od19_security_roles/tests/__init__.py`
- Test: `custom_addons/od19_security_roles/tests/test_roles_install.py`

- [ ] **Step 1: เขียน failing test** — ตรวจว่าติดตั้งแล้วมี privilege + กลุ่มกลางครบ
- [ ] **Step 2: รันเทสต์ให้เห็น fail** (`-u od19_security_roles --test-tags /od19_security_roles`)
- [ ] **Step 3: เขียน `__manifest__.py` + `__init__.py` ให้ติดตั้งผ่าน**
- [ ] **Step 4: รันเทสต์ให้ผ่าน**
- [ ] **Step 5: Commit** `feat(od19_security_roles): scaffold access-control layer`

## Task 2: กลุ่มกลาง 4 ตัว + privilege

**Files:**
- Create: `security/od19_security_groups.xml`
- Create: `data/od19_security_role_privilege.xml`

- [ ] **Step 1: เขียน XML** — privilege `od19_role_privilege` + 4 กลุ่ม โดย `group_od19_department_scope.implied_ids = base.group_user`
- [ ] **Step 2: รันเทสต์** ให้ผ่าน (`test_roles_install`)
- [ ] **Step 3: Commit** `feat(od19_security_roles): add central groups and role privilege`

## Task 3: `res.users.od19_department_id` + mirror จากพนักงาน

**Files:**
- Create: `models/res_users.py`, `models/hr_employee.py`, `models/hr_department.py`
- Create: `views/res_users_views.xml`
- Test: `tests/test_department_sync.py`

- [ ] **Step 1: เขียน failing test** — สร้างแผนก + พนักงาน + ผู้ใช้ แล้วตรวจว่า `od19_department_id` ตรง; ย้ายแผนกพนักงานแล้วผู้ใช้ตามไป
- [ ] **Step 2: รันเทสต์ให้เห็น fail**
- [ ] **Step 3: เขียนโค้ด**
  - `res.users`: ฟิลด์ stored M2o + `_od19_sync_department_from_employee()` เรียกใน `create`/`write`
  - `hr.employee`: `write()` ถ้า `department_id` เปลี่ยน → อัปเดต user ที่ผูก
  - `hr.department`: One2many ย้อนกลับ
- [ ] **Step 4: เพิ่มฟิลด์ในหน้าผู้ใช้ (readonly)**
- [ ] **Step 5: รันเทสต์ให้ผ่าน**
- [ ] **Step 6: Commit** `feat(od19_security_roles): mirror employee department onto users`

## Task 4: cron ตรวจสอบ/ซ่อม mirror

**Files:**
- Create: `data/ir_cron_data.xml`
- Modify: `models/res_users.py` (เพิ่ม `_od19_cron_sync_all_departments`)

- [ ] **Step 1: เขียนเทสต์** — ตั้งค่าแผนกไม่ตรงด้วย SQL-less write (ข้าม hook) แล้วสั่ง cron แล้วตรวจว่าตรง
- [ ] **Step 2: เขียน cron + เมธอดกวาด (`search` ผู้ใช้ที่มี employee แล้ว `write` ค่าให้ตรง)**
- [ ] **Step 3: รันเทสต์ให้ผ่าน**
- [ ] **Step 4: Commit** `feat(od19_security_roles): add daily department mirror cron`

## Task 5: ตัวช่วย record rule + เมนูผู้ดูแล

**Files:**
- Create: `views/role_menus.xml` (เมนู Settings → Users & Companies → Roles)
- Modify: `security/ir.model.access.csv` (ให้ `group_od19_role_manager` เข้าถึง `res.users.role`)
- Test: `tests/test_role_assignment.py`

- [ ] **Step 1: เขียน failing test** — ผู้ใช้ที่มี `group_od19_role_manager` เห็นและแก้ `res.users.role` ได้; ผู้ใช้ทั่วไปแก้ไม่ได้
- [ ] **Step 2: เขียน ACL + เมนู**
- [ ] **Step 3: รันเทสต์ให้ผ่าน**
- [ ] **Step 4: Commit** `feat(od19_security_roles): role manager ACL and menu`

## Task 6: โมดูล `od19_role_catalog` — โครง + data บทบาททั้งหมด

**Files:**
- Create: `custom_addons/od19_role_catalog/__manifest__.py`, `__init__.py`, `tests/__init__.py`
- Create: `data/od19_roles_governance.xml`, `data/od19_roles_operations.xml`, `data/od19_roles_backoffice.xml`
- Test: `tests/test_role_catalog.py`

- [x] **Step 1: เขียน failing test** — role จาก matrix (§7 ของสเปก) โหลดครบ และ `implied_ids` ตรงตามที่ระบุ
- [x] **Step 2: เขียน data XML ทั้ง 43 บทบาท** ( `noupdate="1"`, `group_privilege_id` = `od19_role_privilege`)
- [x] **Step 3: ติดตั้ง + รันเทสต์ให้ผ่าน** (7 tests, 0 failed/0 error)
- [x] **Step 4: ตรวจ SoD** — เทสต์ว่าไม่มี role ใด imply ทั้ง `group_sale_salesman` และ `group_od19_credit_approver`
- [x] **Step 5: Commit** `feat(od19_role_catalog): add 40 business role definitions`

---

# เฟส B — Department record rule (11 โมเดล)

> **หมายเหตุ:** แต่ละโมดูลต้องเพิ่ม `od19_security_roles` ใน `depends` + สร้าง `security/od19_department_rule.xml` และลงทะเบียนใน `data` list

- [x] **Task B1** `od19_goods_issue` → `stock.request.order.department_id`
- [x] **Task B2** `od19_project_analytic` → `project.project.od19_department_id`
- [x] **Task B3** `od19_iso_document_control` → `od19.iso.document.department_id`
- [x] **Task B4** `od19_iso_nonconformity` → `od19.iso.nonconformity.department_id`
- [x] **Task B5** `od19_iso_risk` → `od19.risk.department_id`
- [x] **Task B6** `od19_iso_training` → `od19.training.department_id`
- [x] **Task B7** `od19_iso_calibration` → `od19.calibration.department_id`
- [x] **Task B8** `od19_iso_internal_audit` → `od19.audit.auditee_department_id`
- [x] **Task B9** `od19_internal_issue` → `helpdesk.ticket.department_id`
- [x] **Task B10** `od19_announcement` → `od19.announcement.department_id`
- [x] **Task B11** `od19_fleet_accounting` → `fleet.vehicle.department_id`
- [x] **Task B12** เทสต์รวม: ผู้ใช้แผนก A เห็นเฉพาะเอกสาร A + เอกสารที่ไม่มีแผนก; ผู้มี `group_od19_department_all` เห็นทั้งหมด

> **แก้ไขระหว่างพัฒนา (B11/B12):** แต่ละโมดูลมี **2 rule** ต่อโมเดล —
> (1) scope rule สำหรับ `group_od19_department_scope` (domain ตาม §8.1)
> (2) **all rule** สำหรับ `group_od19_department_all` (domain `[(1, '=', 1)]`)
>
> **เหตุผล:** `role_employee_base` เป็น `is_default=True` และ imply `group_od19_department_scope`
> → ผู้ใช้ใหม่ทุกคนติด scope group แม้จะได้บทบาทระดับบริหาร/บัญชี/คลังที่ imply
> `group_od19_department_all` มาด้วย (ทำให้ §8.1 ข้อสันนิษฐาน "dept-all ไม่อยู่ใน scope group"
> ไม่เป็นจริงในทางปฏิบัติ) เนื่องจากกฎระดับกลุ่มถูก **OR** กัน การเพิ่ม all rule ทำให้
> กลุ่ม `group_od19_department_all` ชนะ scope rule เสมอ → เห็นข้อมูลทุกแผนกได้จริง
> โดยไม่ลดทอนการจำกัดของผู้ใช้ที่เป็นพนักงานทั่วไป

---

# เฟส C — Role Matrix สำหรับ migration (เอกสาร)

- [x] **Task C1** สร้างตาราง `docs/superpowers/programs/odoo19-enterprise/discovery/role-matrix.md` (พนักงาน ↔ บทบาท) จาก Role Matrix §7
- [x] **Task C2** ระบุผู้ใช้ Odoo 15 ที่ได้ `group_od19_department_all` (บัญชี/คลัง/ผู้บริหาร) — เกณฑ์คัดเลือก (ทางตรง/ทางอ้อม) + ทะเบียนลงทะเบียนอยู่ใน role-matrix.md §5; **รายชื่อจริงรอข้อมูลผู้ใช้ Odoo 15** (ยังไม่มี dump ในเครื่องนี้)

---

# เฟส D — วงเงินอนุมัติบน `res.company` (D8)

- [x] **Task D1** เพิ่มฟิลด์ `res.company`: `od19_so_manager_approval_threshold`, `od19_so_director_approval_threshold` (และคง `od19_po_director_approval_threshold` เดิม)
- [x] **Task D2** ปรับ `od19_sales_oca_bridge_workflow` ให้สร้าง `tier.definition` จากค่าบริษัท (hook `post_init`/`_create_tier_definitions`) แทน domain ฮาร์ดโค้ด
- [x] **Task D3** เพิ่มฟิลด์ตั้งค่าใน Settings → Companies
- [x] **Task D4** เทสต์: เปลี่ยนวงเงินแล้ว tier เปลี่ยนตาม

> **แก้ไขระหว่างพัฒนา (D1–D4):** `tier.definition.definition_domain` เป็น Char ที่เครื่องยนต์
> tier validation ประเมินด้วย `literal_eval()` ⇒ domain ต้องเป็น string ของ Python literal
> และต้อง **สร้างใหม่** ทุกครั้งที่วงเงินเปลี่ยน (ทำ dynamic ไม่ได้)
>
> แนวทางที่ใช้:
> - เก็บวงเงินไว้ที่ `res.company` (2 ฟิลด์ใหม่; ค่าเริ่มต้น manager 100,000 / director 500,000 ตามเดิม)
> - `res.company._od19_sync_sale_tier_definitions()` สร้าง/ปรับปรุง tier definition **แยกตามบริษัท**
>   (`company_id = company`) ให้ตรงกับวงเงินปัจจุบัน พร้อมลบ record แบบเดิมที่ `company_id = False`
> - เรียก sync จาก (1) `<function>` ใน `data/od19_sale_tier_definition.xml` (ไม่ใส่ `noupdate`
>   เพื่อให้รันทั้งตอน install และ upgrade — `<function>` ในบล็อก noupdate จะถูกข้ามตอน upgrade),
>   (2) override `res.company.write()` เมื่อวงเงินเปลี่ยน, (3) override `res.company.create()`
>   สำหรับบริษัทใหม่
> - ยังคงค่าเริ่มต้น 100,000/500,000 เพื่อให้เทสต์เดิมใน `test_oca_bridge.py` ผ่านโดยไม่ต้องแก้

---

## Verification

- [x] ติดตั้ง `od19_security_roles` + รันเทสต์ผ่านทั้ง 4 ไฟล์ — 30 tests, 0 failed/0 error
- [x] ติดตั้ง `od19_role_catalog` + รันเทสต์ผ่าน — 9 tests, 0 failed/0 error
- [x] Upgrade ทุกโมดูลที่แก้ในเฟส B ด้วย `-u all` แล้วไม่มี warning — รัน `-u all` บน `odoo19_pdev` แล้ว **EXIT=0 และ log ขนาด 0 ไบต์** (ไม่มี WARNING/ERROR/CRITICAL/Traceback)
- [x] ตรวจว่า Settings → Users → เลือกผู้ใช้ → แท็บ Roles แสดงบทบาทครบ — combined form arch ของ `res.users` มี `role_line_ids` (จาก `base_user_role.view_res_users_form_inherit`) และ `od19_department_id` (จาก `od19_security_roles.view_users_form_od19_department`); มี view ที่ inherit `base.view_users_form` ทั้งหมด 11 ตัว
- [x] ตรวจว่า Settings → Roles แสดงบทบาท grouped by privilege — **ได้ 43 บทบาท** (ไม่ใช่ 40 ตามที่เขียนไว้เดิม) อยู่ใต้ privilege `OD19 Roles` (category `User roles`, sequence 10) ทั้งหมด; เมนูจริงคือ **Settings → Users & Companies → User Roles** (มาจาก OCA `base_user_role.menu_action_res_users_role_tree` ไม่ใช่เมนูแยกชื่อ "Roles"); บทบาท default ที่ให้ผู้ใช้ใหม่คือ "พนักงานทั่วไป"; ไม่มีบทบาทใดที่ไม่มี implied groups (0 รายการ)

> **หมายเหตุการตรวจ:** เครื่องนี้ไม่มี Chrome/Edge สำหรับ browser automation จึงตรวจ 2 ข้อหลังผ่าน ORM
> (`odoo-bin shell` + `res.users.get_view()`) ซึ่งตรวจสอบซ้ำได้และให้หลักฐานเทียบเท่า; การเปิดหน้าเว็บดูด้วยตาจริงยังไม่ได้ทำในรอบนี้
