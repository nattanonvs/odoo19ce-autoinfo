# HR Expense Portal (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มพอร์ทัลพนักงานสำหรับใบเบิกค่าใช้จ่าย (`/my/expenses`) ให้พนักงานที่ไม่มีสิทธิ์หลังบ้านยื่นใบเบิก (รวม Mileage) และติดตามสถานะการอนุมัติ 3 ชั้นได้จากมือถือ

**Architecture:**
- ขยายโมดูลเดิม `od19_hr_expense_portal` (v19.0.1.0.0 → **19.0.2.0.0**) เพิ่มชั้น portal — ไม่สร้างโมดูลใหม่
- Route + QWeb ใช้ `portal.portal_layout` (สืบทอด `web.frontend_layout`) · ติดตั้ง dependency ใหม่: `portal`, `base_tier_validation`
- **การควบคุมสิทธิ์:** controller ทำงานด้วย `request.env` ของผู้ใช้พอร์ทัล แล้วเรียก `.sudo()` เฉพาะระดับ ORM (uid คงเดิม → `self.env.user` ยังเป็นผู้ใช้จริง) พร้อมกรองด้วยโดเมนเจ้าของ `[('employee_id.user_id', '=', request.env.user.id)]` ทุกครั้ง — ใบเบิกของคนอื่นต้องได้ 404
- เสริมด้วย `ir.rule` (`base.group_portal`) และ `ir.model.access` แบบ read-only ให้ผู้ใช้พอร์ทัลอ่านได้เฉพาะของตัวเอง (defense-in-depth)
- การสร้าง/ส่งใบเบิกใช้ wizard เดิม `od19.expense.quick.create` (Phase 2) เพื่อ reuse ตรรกะ Mileage/plain

**Tech Stack:** Odoo 19 CE · `portal` · OCA `base_tier_validation` · QWeb · `HttpCase` + `TransactionCase`

**ข้อกำหนดอ้างอิง:** AGENTS.md (ห้ามแตะ core · Conventional Commits · ห้าม `git add -A` · รัน Unit Test บน `odoo19_pdev`) · Spec §6.3, §10, §11 (Phase 3), §12 (T4, T8)

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_hr_expense_portal/__manifest__.py` | depends + data + version | แก้ |
| `custom_addons/od19_hr_expense_portal/__init__.py` | import controllers | แก้ |
| `custom_addons/od19_hr_expense_portal/controllers/__init__.py` | import portal | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/controllers/portal.py` | route `/my/expenses*` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/views/portal_templates.xml` | QWeb 3 หน้า (list/detail/new) | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/security/od19_hr_expense_portal_security.xml` | `ir.rule` ของพอร์ทัล | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/security/ir.model.access.csv` | สิทธิ์ read-only ของพอร์ทัล | แก้ |
| `custom_addons/od19_hr_expense_portal/tests/test_portal.py` | T4 + T8 | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/tests/__init__.py` | import ไฟล์เทสต์ใหม่ | แก้ |

---

## Task 1: Routes + controller (`/my/expenses`)

**Files:** `controllers/__init__.py`, `controllers/portal.py`, `__init__.py`

- [ ] **Step 1: สร้าง `controllers/__init__.py`**

```python
# -*- coding: utf-8 -*-
from . import portal
```

- [ ] **Step 2: สร้าง `controllers/portal.py`**

Route:
- `GET /my/expenses` (+ `/my/expenses/page/<int:page>`) — รายการใบเบิกของผู้ใช้ (paged)
- `GET /my/expenses/new` — ฟอร์มยื่นใบเบิก
- `POST /my/expenses/new` — สร้างใบเบิก (ใช้ wizard) แล้ว redirect ไปหน้ารายละเอียด
- `GET /my/expenses/<int:expense_id>` — รายละเอียด + timeline อนุมัติ 3 ชั้น
- `POST /my/expenses/<int:expense_id>/submit` — ส่งใบเบิก (เฉพาะเจ้าของ, state=draft)

หลักการ:
```python
def _expense_domain(self):
    return [('employee_id.user_id', '=', request.env.user.id)]

def _expense_check_access(self, expense_id):
    expense = request.env['hr.expense'].sudo().search(
        self._expense_domain() + [('id', '=', expense_id)], limit=1)
    if not expense:
        raise MissingError / request.not_found()
    return expense
```

- [ ] **Step 3: เพิ่ม import ใน `__init__.py`** (`from . import controllers`)

- [ ] **Step 4: ตรวจไวยากรณ์แบบ static**

Run: `venv19\Scripts\python.exe -m py_compile custom_addons/od19_hr_expense_portal/controllers/portal.py`
Expected: ไม่มี error

## Task 2: QWeb templates

**Files:** `views/portal_templates.xml`

- [ ] **Step 1: `portal_my_expenses`** — ตารางรายการ + ปุ่ม "ยื่นใบเบิก" + `portal.pager`
- [ ] **Step 2: `portal_my_expense_detail`** — ข้อมูลใบเบิก + timeline `review_ids` (`sequence`, `name`, `display_status`, `done_by`, `reviewed_date`) + เหตุผลเมื่อถูกปฏิเสธ
- [ ] **Step 3: `portal_my_expense_new`** — ฟอร์ม (category/date/description + amount | mileage: distance/vehicle/origin/destination) + checkbox submit_now + csrf token
- [ ] **Step 4: ตรวจ XML well-formed**

Run: `venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_hr_expense_portal/views/portal_templates.xml')"`
Expected: ไม่มี error

## Task 3: Security (ir.rule + access)

**Files:** `security/od19_hr_expense_portal_security.xml`, `security/ir.model.access.csv`

- [ ] **Step 1: `ir.rule`** — `base.group_portal` เห็นเฉพาะ `['|',('employee_id.user_id','=',user.id),('create_uid','=',user.id)]`
- [ ] **Step 2: `ir.model.access.csv`** — เพิ่ม `base.group_portal` read-only บน `hr.expense` (1,0,0,0) — การสร้าง/ส่งทำผ่าน controller (sudo)

## Task 4: Tests (T4, T8)

**Files:** `tests/test_portal.py`, `tests/__init__.py`

- [ ] **Step 1: T4 — ผู้ใช้พอร์ทัลเห็นเฉพาะใบเบิกของตัวเอง**
  - `TransactionCase`: สร้าง 2 พนักงาน/2 ผู้ใช้พอร์ทัล → search/read ฝั่ง ORM เห็นเฉพาะของตัวเอง + controller detail ของคนอื่น → 403/404
- [ ] **Step 2: T8 — ยื่นใบเบิกผ่าน portal สำเร็จ (HttpCase)**
  - `HttpCase`: ล็อกอินผู้ใช้พอร์ทัล → GET `/my/expenses` (200) → GET `/my/expenses/new` (200) → POST สร้าง (redirect) → ใบเบิกถูกสร้างด้วย employee ที่ถูกต้อง
- [ ] **Step 3: รันเทสต์**

Run:
```powershell
.\run-tests.ps1 -Module od19_hr_expense_portal
```
Expected: `0 failed, 0 error(s)`

## Task 5: Commit

- [ ] `git add -- custom_addons/od19_hr_expense_portal docs/superpowers/plans/2026-11-07-od19-hr-expense-portal-phase3-plan.md`
- [ ] `git commit -m "feat(od19_hr_expense_portal): add employee portal for expense claims (Phase 3)"`
- [ ] `git push -u origin feature/od19_hr_expense_portal`
