# Expense Claim — ใบเบิกรวมหลายรายการ (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างหัวใบ "ใบเบิก" (`od19.expense.claim`) ที่รวมบรรทัดค่าใช้จ่าย (`hr.expense`) ได้หลายบรรทัด แล้วย้ายการอนุมัติ 3 ชั้น (หัวหน้าแผนก → บัญชี → CEO) มาที่ **หัวใบครั้งเดียว** — ผู้อนุมัติกดอนุมัติ 3 ครั้งต่อใบเบิก (ไม่ใช่ 3 × จำนวนบรรทัด) เมื่อหัวใบอนุมัติครบทุกบรรทัดจะกลายเป็น `approved` และโพสต์บัญชีได้ตามปกติ

**Architecture:**
- สร้าง **โมดูลใหม่** `custom_addons/od19_hr_expense_claim` (K1) — แยกขอบเขต ย้อนกลับง่าย
- โมเดลใหม่ `od19.expense.claim` inherit `["mail.thread", "mail.activity.mixin", "tier.validation"]` แบบเดียวกับ `od19.hr.advance` (โมดูลต้นแบบ)
- เพิ่มฟิลด์ `od19_claim_id` (Many2one) บน `hr.expense` เป็น "บรรทัด" ของหัวใบ (K3: ทุกการเบิกต้องมีหัวใบ ≥ 1 บรรทัด)
- **ย้าย** `tier.definition` 3 ชั้นจาก `od19_hr_expense_thai` (ที่ผูก `hr.expense`) มาผูก `od19.expense.claim` แล้วลบของเดิมออก → `hr.expense` จะไม่มี tier อีก (ปลดบล็อก `write()` ไม่ให้ขึ้น "The expense is under validation.")
- **อนุมัติที่หัวใบ → propagate** `approval_state='approved'` ลงบรรทัดตรง ๆ (K5) โดย **ไม่เรียก** core `action_approve`/`_do_approve` (เลี่ยงการอนุมัติซ้ำซ้อน + ไม่ทับ `manager_id`/`approval_date` ของบรรทัด)
- **โพสต์ที่บรรทัด** (K4) — หัวใบเป็นเพียง "ตัวรวม + ด่านอนุมัติ" สั่ง `line_ids.action_post()` (กลไก core เดิม)

**Tech Stack:** Odoo 19 CE · Python 3 · OCA `base_tier_validation` / `hr_expense_tier_validation` / `base_tier_validation_forward` (ห้ามแก้) · XML data · Odoo `TransactionCase` (`AccountTestInvoicingCommon`)

**ข้อกำหนดอ้างอิง (บังคับ):**
- สเปกที่ล็อกแล้ว (rev2): [2026-11-20-od19-hr-expense-claim-batch-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-11-20-od19-hr-expense-claim-batch-design.md)
- ตาม [AGENTS.md](file:///c:/odoo-dev/odoo19/AGENTS.md): **ห้ามแก้ Odoo core** (`addons/`, `odoo/`) และ **ห้ามแก้ `third_party/oca/`** · commit ได้เองใน `custom_addons/` + `docs/` หลังผ่าน Pre-flight · Conventional Commits · **ห้าม `git add -A`** · Single-writer
- ฐานข้อมูลทดสอบ: `odoo19_pdev`
- **ห้ามรัน Unit Test แทนผู้ใช้** — แผนนี้ระบุคำสั่งไว้ให้ผู้ใช้รันเองบน terminal

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_hr_expense_claim/__init__.py` | โหลด models | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/__manifest__.py` | depends + data + version | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/models/__init__.py` | โหลดโมเดล | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/models/od19_expense_claim.py` | โมเดลหัวใบ `od19.expense.claim` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/models/hr_expense.py` | เพิ่ม `od19_claim_id` บน `hr.expense` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/models/tier_definition.py` | ลงทะเบียนโมเดลกับ `_get_tier_validation_model_names` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/data/ir_sequence_data.xml` | `ir.sequence` code `od19.expense.claim` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/data/tier_definition_data.xml` | `tier.definition` 3 ชั้นบนหัวใบ (seq 30/20/10) | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/security/ir.model.access.csv` | ACL หัวใบ | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/security/od19_expense_claim_security.xml` | `ir.rule` ของตัวเอง + ผู้อนุมัติ | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/views/od19_expense_claim_views.xml` | list/form/kanban/search + action + menu | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/tests/__init__.py` | โหลดเทสต์ | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_claim/tests/test_expense_claim.py` | เทสต์ T1–T9 (Phase 1) | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_thai/__manifest__.py` | ถอด `data/tier_definition_data.xml` ออกจาก data + bump version | แก้ |
| `custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml` | ย้ายไปโมดูลใหม่ | **ลบไฟล์** |
| `custom_addons/od19_hr_expense_thai/migrations/19.0.1.4.0/post-migrate.py` | ลบ `tier.definition` เดิมบน `hr.expense` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py` | ปรับให้ตรวจว่า `hr.expense` ไม่มี tier แล้ว | แก้ |
| `docs/superpowers/plans/2026-11-20-od19-hr-expense-claim-batch-plan.md` | แผนฉบับนี้ | — |

**ลำดับการโหลดข้อมูล (สำคัญ):** ใน `od19_hr_expense_claim/__manifest__.py` ต้องโหลด `security/...` **ก่อน** `data/tier_definition_data.xml` (tier อ้างกลุ่ม CEO `od19_hr_expense_thai.group_od19_expense_ceo_approver` ที่ประกาศใน `od19_hr_expense_thai` — dependency ถูกดึงมาก่อนแล้ว)

---

## กลไกที่ยืนยันจากโค้ดจริง (ใช้อ้างอิงตอน implement)

- **`hr.expense.state` เป็น compute+store** จาก `approval_state` ([hr_expense.py](file:///c:/odoo-dev/odoo19/addons/hr_expense/models/hr_expense.py#L458-L492)): เมื่อไม่มี `account_move_id` → `expense.state = expense.approval_state or 'draft'` ⇒ เขียน `approval_state='approved'` ให้บรรทัด = บรรทัดเป็น `state='approved'` ทันที
- **`_check_can_create_move`** ([L1445](file:///c:/odoo-dev/odoo19/addons/hr_expense/models/hr_expense.py#L1445-L1450)) บังคับ `state == 'approved'` ก่อนสร้าง entry ⇒ propagate `approval_state` ทำให้โพสต์ได้ โดยไม่ต้องเรียก `action_approve`
- **`_do_approve`** ([L1452](file:///c:/odoo-dev/odoo19/addons/hr_expense/models/hr_expense.py#L1452-L1466)) เขียน `approval_state`+`manager_id`+`approval_date` และเรียก `_validate_distribution` ⇒ **ห้ามใช้** กับบรรทัด (เราเขียน `approval_state` ตรง ๆ)
- **`hr_expense_tier_validation.write()`** ([hr_expense.py](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/hr_expense_tier_validation/models/hr_expense.py#L44-L52)) raise `ValidationError("The expense is under validation.")` **ต่อเมื่อ** `approval_state == "submitted"` **และ** มี `review_ids` **และ** `validation_status not in ("validated","rejected")` ⇒ เมื่อลบ tier definitions ออกจาก `hr.expense` แล้ว `review_ids` ว่างเสมอ จึงไม่บล็อก
- **`tier.validation.write()`** ([tier_validation.py](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/base_tier_validation/models/tier_validation.py#L399-L403)) เรียก 3 ตัวตรวจก่อน `super().write()`:
  - `_tier_validation_check_state_on_write` ([L433](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/base_tier_validation/models/tier_validation.py#L433-L458)): เข้าเงื่อนไขเมื่อ state ปัจจุบัน ∈ `_state_from` และค่าใหม่ ∈ `_state_to`; ถ้า `need_validation` → ขอ validation เองและ raise ถ้ายังไม่ครบ; ถ้ามี `review_ids` และ `validation_status != 'validated'` → raise ⇒ **เขียน `state='approved'` ได้เฉพาะเมื่อ validated แล้ว**
  - `_check_tier_state_transition` ([L390](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/base_tier_validation/models/tier_validation.py#L390-L397)) คืน False เมื่อค่าใหม่อยู่ใน `_state_to` ⇒ ไม่บล็อกการเปลี่ยนไป approved
  - `_allow_to_remove_reviews` ([L519](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/base_tier_validation/models/tier_validation.py#L519-L532)) คืน True เมื่อเขียน state ไปเป็น `_cancel_state` ⇒ ตั้ง `_cancel_state="refused"` ทำให้ **ล้าง review อัตโนมัติเมื่อหัวใบถูกปฏิเสธ**
- **mixin ไม่เขียน state ให้เอง** — `_validate_tier` ([L547](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/base_tier_validation/models/tier_validation.py#L547-L612)) เขียนแค่ `tier.review.status` ⇒ โมเดลต้อง override `_validate_tier` เพื่อเขียน `state='approved'` + propagate เอง
- **ลำดับชั้น:** `request_validation()` เรียง `tier.definition` ด้วย `sequence desc` แล้วแปลงเป็น `tier.review.sequence` 1,2,3,... ⇒ definition `sequence` สูงกว่า (30) = ชั้นแรก (หัวหน้าแผนก)
- **`_validate_tier` อนุมัติเฉพาะ review ติดกันของผู้ใช้** และหยุดที่ review แรกที่ไม่ใช่ ⇒ อนุมัติข้ามขั้นไม่ได้
- **ir.rule semantics:** กฎกลุ่ม (ไม่ global) ที่ผู้ใช้เข้าเงื่อนไขถูก **OR** กัน (ดู [hr_expense/security/ir_rule.xml](file:///c:/odoo-dev/odoo19/addons/hr_expense/security/ir_rule.xml)) ⇒ ตั้งกฎ "ของตัวเอง" (base.group_user) + กฎ "ทั้งหมด" (กลุ่มผู้อนุมัติ) ได้
- **`res.users` Odoo 19 ใช้ฟิลด์ `group_ids`** (ไม่ใช่ `groups_id`)
- **โมดูลต้นแบบ:** [od19_hr_advance](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_advance/models/hr_advance.py) — โครง manifest/data/views/security/tests + การเพิ่ม Many2one บน `hr.expense` ([models/hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_advance/models/hr_expense.py))
- **คำสั่งรันเทสต์:** `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim,od19_hr_expense_thai`

---

## Task 0: Pre-flight (บังคับตาม AGENTS.md)

**Files:** ไม่มี (ตรวจสอบสภาพแวดล้อม)

- [ ] **Step 1: ตรวจ branch และสถานะ**

Run:
```powershell
git log -1 --oneline
git status -sb
git branch --show-current
```
Expected: อยู่ที่ branch งาน (`feature/...`) · working tree สะอาดหรือมีเฉพาะไฟล์ที่งานนี้จะแตะ · **ไม่มี** ไฟล์ `.git/index.lock`

- [ ] **Step 2: บันทึก HEAD**

จดค่า SHA จาก `git log -1 --oneline` ไว้รายงานตอนจบ

- [ ] **Step 3: ยืนยัน HEAD ไม่เปลี่ยนใน 2 นาที**

Run:
```powershell
Start-Sleep -Seconds 120; git log -1 --oneline
```
Expected: SHA เท่าเดิม → ผ่าน Single-writer · ถ้าเปลี่ยน ให้ **หยุด** และรายงานผู้ใช้

---

## Task 1: Scaffold โมดูล `od19_hr_expense_claim`

**Files:**
- Create: `custom_addons/od19_hr_expense_claim/__init__.py`
- Create: `custom_addons/od19_hr_expense_claim/__manifest__.py`
- Create: `custom_addons/od19_hr_expense_claim/models/__init__.py`
- Create: `custom_addons/od19_hr_expense_claim/data/ir_sequence_data.xml`
- Create: `custom_addons/od19_hr_expense_claim/security/ir.model.access.csv`
- Create: `custom_addons/od19_hr_expense_claim/tests/__init__.py`

- [ ] **Step 1: สร้าง `__init__.py` และ `models/__init__.py`**

`__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import models
```

`models/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import od19_expense_claim
from . import hr_expense
from . import tier_definition
```

- [ ] **Step 2: สร้าง `__manifest__.py`**

```python
# -*- coding: utf-8 -*-
{
    "name": "OD19 HR - Expense Claim (ใบเบิกค่าใช้จ่ายรวมหลายรายการ)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Expenses",
    "summary": "หัวใบเบิกค่าใช้จ่ายรวมหลายรายการ + อนุมัติ 3 ชั้นที่หัวใบ",
    "depends": [
        "hr_expense",
        "hr_expense_tier_validation",
        "base_tier_validation",
        "base_tier_validation_forward",
        "od19_hr_expense_thai",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/od19_expense_claim_security.xml",
        "data/ir_sequence_data.xml",
        "data/tier_definition_data.xml",
        "views/od19_expense_claim_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
```

> `depends` บน `od19_hr_expense_thai` จะดึง `od19_hr_expense_enhanced` + `od19_accounting_features` + กลุ่ม CEO มาด้วย

- [ ] **Step 3: สร้าง `data/ir_sequence_data.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="seq_od19_expense_claim" model="ir.sequence">
            <field name="name">Expense Claim Sequence</field>
            <field name="code">od19.expense.claim</field>
            <field name="prefix">EXP/%(year)s/</field>
            <field name="padding">5</field>
            <field name="company_id" eval="False"/>
        </record>
    </data>
</odoo>
```

- [ ] **Step 4: สร้าง `security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_expense_claim_user,od19.expense.claim.user,model_od19_expense_claim,hr_expense.group_hr_expense_user,1,1,1,0
access_od19_expense_claim_manager,od19.expense.claim.manager,model_od19_expense_claim,hr_expense.group_hr_expense_manager,1,1,1,1
access_od19_expense_claim_account,od19.expense.claim.account,model_od19_expense_claim,account.group_account_manager,1,1,1,0
access_od19_expense_claim_ceo,od19.expense.claim.ceo,model_od19_expense_claim,od19_hr_expense_thai.group_od19_expense_ceo_approver,1,1,0,0
```

- [ ] **Step 5: สร้าง `tests/__init__.py`**

```python
# -*- coding: utf-8 -*-
from . import test_expense_claim
```

- [ ] **Step 6: ตรวจโครงสร้างก่อนไปต่อ**

Run:
```powershell
Get-ChildItem -Recurse custom_addons\od19_hr_expense_claim | Select-Object FullName
```
Expected: เห็น `__init__.py`, `__manifest__.py`, `models/`, `data/`, `security/`, `tests/`

---

## Task 2: โมเดลหัวใบ `od19.expense.claim` + ฟิลด์ `od19_claim_id`

**Files:**
- Create: `custom_addons/od19_hr_expense_claim/models/od19_expense_claim.py`
- Create: `custom_addons/od19_hr_expense_claim/models/hr_expense.py`
- Create: `custom_addons/od19_hr_expense_claim/models/tier_definition.py`
- Create: `custom_addons/od19_hr_expense_claim/tests/test_expense_claim.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (T1 — ยอดรวม)**

สร้าง `tests/test_expense_claim.py` (โครงเริ่มต้น + helper จะเพิ่มใน Task ถัดไป):

```python
# -*- coding: utf-8 -*-
from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestExpenseClaim(AccountTestInvoicingCommon):

    @classmethod
    def get_default_groups(cls):
        return (
            super().get_default_groups()
            | cls.env.ref("hr.group_hr_user")
            | cls.env.ref("hr_expense.group_hr_expense_user")
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Claim = cls.env["od19.expense.claim"]
        cls.supervisor = new_test_user(
            cls.env, login="od19_claim_supervisor",
            name="Claim Supervisor",
            groups="base.group_user,hr_expense.group_hr_expense_manager",
        )
        cls.accountant = new_test_user(
            cls.env, login="od19_claim_accountant",
            name="Claim Accountant",
            groups="base.group_user,account.group_account_manager",
        )
        cls.ceo = new_test_user(
            cls.env, login="od19_claim_ceo",
            name="Claim CEO",
            groups="base.group_user,od19_hr_expense_thai.group_od19_expense_ceo_approver",
        )
        cls.product = cls.env["product.product"].create({
            "name": "Claim Test Expense",
            "type": "service",
            "property_account_expense_id": cls.company_data["default_account_expense"].id,
        })
        cls.employee = cls.env["hr.employee"].create({"name": "Claim Employee"})

    def _make_claim(self, lines=None):
        lines = lines or [{"name": "Line A", "total_amount": 100.0}]
        return self.Claim.create({
            "employee_id": self.employee.id,
            "company_id": self.env.company.id,
            "line_ids": [
                Command.create({
                    "name": line["name"],
                    "product_id": self.product.id,
                    "total_amount": line["total_amount"],
                    "employee_id": self.employee.id,
                    "payment_mode": "own_account",
                    "company_id": self.env.company.id,
                })
                for line in lines
            ],
        })

    # ---------------------------------------------------------------
    # T1: ยอดรวมหัวใบ = ผลรวมบรรทัด
    # ---------------------------------------------------------------
    def test_claim_total_amount_is_sum_of_lines(self):
        claim = self._make_claim([
            {"name": "Line A", "total_amount": 100.0},
            {"name": "Line B", "total_amount": 250.0},
            {"name": "Line C", "total_amount": 50.0},
        ])
        self.assertEqual(len(claim.line_ids), 3)
        self.assertAlmostEqual(claim.total_amount, 400.0)
        self.assertTrue(claim.name.startswith("EXP/"))
```

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim
```
Expected: **FAIL** (โมเดล `od19.expense.claim` ยังไม่มี)

- [ ] **Step 2: เขียนโมเดลหัวใบ `models/od19_expense_claim.py`**

```python
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Od19ExpenseClaim(models.Model):
    """ใบเบิกค่าใช้จ่าย (หัวใบ) — รวมบรรทัด ``hr.expense`` หลายรายการ.

    การอนุมัติ 3 ชั้นทำที่หัวใบครั้งเดียว (ผ่าน OCA ``tier.validation``)
    เมื่ออนุมัติครบจะ propagate ``approval_state='approved'`` ลงทุกบรรทัด
    เพื่อให้ core ``hr.expense`` โพสต์บัญชีได้ตามปกติ
    """

    _name = "od19.expense.claim"
    _description = "Expense Claim / ใบเบิกค่าใช้จ่าย"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "date desc, id desc"

    # OCA tier.validation — อนุมัติ 3 ชั้นที่หัวใบ
    # ``_state_from=['submitted']`` -> ต้องส่ง (submitted) ก่อนจึงขอ validation
    # ``_state_to=['approved']``   -> validate ครบแล้วเปลี่ยนเป็น approved ได้
    # ``_cancel_state='refused'``  -> ปฏิเสธแล้วล้าง review อัตโนมัติ
    _state_field = "state"
    _state_from = ["submitted"]
    _state_to = ["approved"]
    _cancel_state = "refused"
    _tier_validation_manual_config = False

    name = fields.Char(
        string="Claim Number", default="/", readonly=True, copy=False, index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department", string="Department",
        related="employee_id.department_id", store=True, readonly=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string="Claim Date", required=True,
        default=fields.Date.context_today, tracking=True,
    )
    submit_date = fields.Datetime(string="Submitted On", readonly=True, copy=False)
    approval_date = fields.Datetime(string="Approved On", readonly=True, copy=False)
    line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="Expense Lines",
    )
    total_amount = fields.Monetary(
        string="Total", currency_field="currency_id",
        compute="_compute_total_amount", store=True,
    )
    payment_mode = fields.Selection(
        [("own_account", "Employee (to reimburse)"),
         ("company_account", "Company")],
        string="Paid By", default="own_account", required=True, tracking=True,
    )
    state = fields.Selection(
        [("draft", "Draft"),
         ("submitted", "Submitted"),
         ("approved", "Approved"),
         ("posted", "Posted"),
         ("paid", "Paid"),
         ("refused", "Refused")],
        string="Status", default="draft", tracking=True, copy=False,
    )
    note = fields.Text(string="Notes")

    # ------------------------------------------------------------------
    # Compute / create
    # ------------------------------------------------------------------
    @api.depends("line_ids.total_amount")
    def _compute_total_amount(self):
        for claim in self:
            claim.total_amount = sum(claim.line_ids.mapped("total_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.expense.claim") or "/"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("line_ids.payment_mode")
    def _check_single_payment_mode(self):
        for claim in self:
            modes = set(claim.line_ids.mapped("payment_mode"))
            if len(modes) > 1:
                raise ValidationError(
                    _("ทุกบรรทัดในใบเบิกต้องใช้วิธีจ่าย (Paid By) เดียวกัน")
                )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        """ส่งใบเบิกเพื่อขออนุมัติ 3 ชั้นที่หัวใบ."""
        for claim in self:
            if claim.state != "draft":
                raise UserError(_("ส่งได้เฉพาะใบเบิกที่เป็นฉบับร่าง"))
            if not claim.line_ids:
                raise UserError(_("ใบเบิกต้องมีอย่างน้อย 1 บรรทัด"))
            claim.line_ids.write({"approval_state": "submitted"})
            claim.write({
                "state": "submitted",
                "submit_date": fields.Datetime.now(),
            })
            claim.invalidate_recordset(["need_validation"])
            if claim.need_validation:
                claim.request_validation()
        return True

    def action_refuse(self):
        """ปฏิเสธใบเบิก -> บรรทัดทุกตัวถูกปฏิเสธ (review ล้างอัตโนมัติ)."""
        for claim in self:
            if claim.state in ("posted", "paid"):
                raise UserError(_("ไม่สามารถปฏิเสธใบเบิกที่โพสต์/จ่ายแล้ว"))
            claim.line_ids.write({"approval_state": "refused"})
            claim.write({"state": "refused"})
        return True

    def action_reset(self):
        """ดึงใบเบิกที่ถูกปฏิเสธกลับเป็นฉบับร่างเพื่อแก้ไข/ส่งใหม่."""
        for claim in self:
            if claim.state != "refused":
                raise UserError(_("ดึงกลับได้เฉพาะใบเบิกที่ถูกปฏิเสธ"))
            claim.line_ids.write({"approval_state": False})
            claim.write({
                "state": "draft",
                "submit_date": False,
                "approval_date": False,
            })
        return True

    def action_post(self):
        """โพสต์บันทึกบัญชีที่บรรทัด (กลไก core เดิม)."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("โพสต์ได้เฉพาะใบเบิกที่อนุมัติครบแล้ว"))
        self.line_ids.action_post()
        self.state = "posted"
        return True

    # ------------------------------------------------------------------
    # Tier validation hook — propagate ลงบรรทัดเมื่ออนุมัติครบ
    # ------------------------------------------------------------------
    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers=tiers)
        for claim in self:
            claim.invalidate_recordset(["validation_status"])
            if claim.validation_status == "validated" and claim.state == "submitted":
                claim._od19_on_validation_complete()
        return res

    def _od19_on_validation_complete(self):
        """หัวใบอนุมัติครบ -> ตั้ง approved + propagate ลงทุกบรรทัด (K5)."""
        self.ensure_one()
        self.write({
            "state": "approved",
            "approval_date": fields.Datetime.now(),
        })
        self.line_ids.write({"approval_state": "approved"})
```

- [ ] **Step 3: เพิ่มฟิลด์บน `hr.expense` — `models/hr_expense.py`**

```python
# -*- coding: utf-8 -*-
from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    od19_claim_id = fields.Many2one(
        "od19.expense.claim",
        string="Expense Claim / ใบเบิก",
        copy=False,
        index="btree_not_null",
        ondelete="cascade",
        help="หัวใบเบิกค่าใช้จ่ายที่บรรทัดนี้สังกัด",
    )
```

- [ ] **Step 4: ลงทะเบียนโมเดลกับ tier — `models/tier_definition.py`**

```python
# -*- coding: utf-8 -*-
from odoo import api, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    @api.model
    def _get_tier_validation_model_names(self):
        res = super()._get_tier_validation_model_names()
        res.append("od19.expense.claim")
        return res
```

- [ ] **Step 5: รันเทสต์ T1**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim
```
Expected: **PASS** (T1 ผ่าน — โมเดลถูกสร้าง ยอดรวมถูกต้อง sequence ออกเลข `EXP/...`)

---

## Task 3: ย้าย `tier.definition` 3 ชั้นมาที่หัวใบ + ลบของเดิมบน `hr.expense`

**Files:**
- Create: `custom_addons/od19_hr_expense_claim/data/tier_definition_data.xml`
- Modify: `custom_addons/od19_hr_expense_claim/__manifest__.py` (มี data แล้วใน Task 1)
- Modify: `custom_addons/od19_hr_expense_thai/__manifest__.py`
- Delete: `custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml`
- Create: `custom_addons/od19_hr_expense_thai/migrations/19.0.1.4.0/post-migrate.py`
- Modify: `custom_addons/od19_hr_expense_claim/tests/test_expense_claim.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (T2/T3/T4/T5/T8)**

เพิ่มใน `tests/test_expense_claim.py`:

```python
    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------
    def _claim_definitions(self):
        return self.env["tier.definition"].search([
            ("model", "=", "od19.expense.claim"),
            ("company_id", "=", False),
        ])

    def _approve_claim(self, claim):
        claim.action_submit()
        claim.with_user(self.supervisor).validate_tier()
        claim.invalidate_recordset()
        claim.with_user(self.accountant).validate_tier()
        claim.invalidate_recordset()
        claim.with_user(self.ceo).validate_tier()
        claim.invalidate_recordset()
        return claim

    # ---------------------------------------------------------------
    # T2/T8: tier 3 ชั้นบนหัวใบ (และไม่มีบน hr.expense)
    # ---------------------------------------------------------------
    def test_tier_definition_model_names_include_claim(self):
        names = self.env["tier.definition"]._get_tier_validation_model_names()
        self.assertIn("od19.expense.claim", names)

    def test_three_tier_definitions_on_claim(self):
        defs = self._claim_definitions()
        self.assertEqual(len(defs), 3)

    def test_tier_definition_order_and_groups(self):
        defs = self._claim_definitions().sorted("sequence", reverse=True)
        self.assertEqual(defs.mapped("sequence"), [30, 20, 10])
        self.assertEqual(defs[0].reviewer_group_id,
                         self.env.ref("hr_expense.group_hr_expense_manager"))
        self.assertEqual(defs[1].reviewer_group_id,
                         self.env.ref("account.group_account_manager"))
        self.assertEqual(defs[2].reviewer_group_id,
                         self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver"))
        self.assertTrue(all(defs.mapped("approve_sequence")))
        self.assertTrue(all(defs.mapped("has_forward")))

    def test_no_tier_definition_on_hr_expense(self):
        """หลังย้าย tier ไปหัวใบ hr.expense ต้องไม่มี tier.definition แล้ว"""
        defs = self.env["tier.definition"].search([
            ("model", "=", "hr.expense"),
            ("company_id", "=", False),
        ])
        self.assertFalse(defs)

    def test_hr_expense_need_validation_is_false(self):
        expense = self.env["hr.expense"].create({
            "name": "Free Line", "product_id": self.product.id,
            "total_amount": 10.0, "employee_id": self.employee.id,
            "payment_mode": "own_account", "company_id": self.env.company.id,
        })
        self.assertFalse(expense.need_validation)

    # ---------------------------------------------------------------
    # T2: submit สร้าง review 3 รายการ เรียง seq 1,2,3
    # ---------------------------------------------------------------
    def test_submit_creates_three_reviews(self):
        claim = self._make_claim()
        self.assertTrue(claim.need_validation)
        claim.action_submit()
        self.assertEqual(claim.state, "submitted")
        self.assertEqual(len(claim.review_ids), 3)
        self.assertEqual(
            claim.review_ids.sorted("sequence").mapped("sequence"), [1, 2, 3]
        )
        self.assertIn(claim.validation_status, ("pending", "waiting"))

    # ---------------------------------------------------------------
    # T3: อนุมัติข้ามขั้นไม่ได้
    # ---------------------------------------------------------------
    def test_cannot_approve_out_of_order(self):
        claim = self._make_claim()
        claim.action_submit()
        # CEO (ชั้น 3) พยายามอนุมัติก่อน -> ยังไม่ validated
        claim.with_user(self.ceo).validate_tier()
        claim.invalidate_recordset()
        self.assertNotEqual(claim.validation_status, "validated")
        self.assertEqual(claim.state, "submitted")

    # ---------------------------------------------------------------
    # T4 + T5: อนุมัติครบ 3 ชั้น -> หัวใบ approved + บรรทัด approved
    # ---------------------------------------------------------------
    def test_full_approval_sets_header_and_lines_approved(self):
        claim = self._make_claim([
            {"name": "Line A", "total_amount": 100.0},
            {"name": "Line B", "total_amount": 200.0},
            {"name": "Line C", "total_amount": 300.0},
        ])
        self._approve_claim(claim)
        self.assertEqual(claim.state, "approved")
        self.assertTrue(claim.approval_date)
        for line in claim.line_ids:
            self.assertEqual(line.approval_state, "approved")
            self.assertEqual(line.state, "approved")

    def test_approval_count_is_three_not_per_line(self):
        """จำนวนครั้งที่อนุมัติ (tier.review ที่ approved) = 3 ต่อใบ."""
        claim = self._make_claim([
            {"name": "Line A", "total_amount": 100.0},
            {"name": "Line B", "total_amount": 200.0},
        ])
        self._approve_claim(claim)
        self.assertEqual(len(claim.review_ids), 3)
        self.assertTrue(all(r.status == "approved" for r in claim.review_ids))
```

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim,od19_hr_expense_thai
```
Expected: **FAIL** (`od19.expense.claim` ยังไม่มี tier.definition; `hr.expense` ยังมี 3 รายการเดิม)

- [ ] **Step 2: สร้าง `data/tier_definition_data.xml` บนหัวใบ**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <!--
    Expense Claim Tier Validation — สายอนุมัติ 3 ชั้น (อนุมัติตามลำดับ) ที่ "หัวใบ"
      ชั้นที่ 1  หัวหน้าแผนก   (hr_expense.group_hr_expense_manager)                      sequence 30
      ชั้นที่ 2  ฝ่ายบัญชี     (account.group_account_manager)                             sequence 20
      ชั้นที่ 3  CEO          (od19_hr_expense_thai.group_od19_expense_ceo_approver)      sequence 10

    กลไก OCA ``request_validation`` เรียง ``tier.definition`` ด้วย ``sequence desc``
    แล้วแปลงเป็น ``tier.review.sequence`` 1, 2, 3, ...
    => definition ที่ ``sequence`` สูงกว่า จะถูกอนุมัติก่อน (ชั้น 1 = sequence 30)

    ``has_forward`` มาจากโมดูล base_tier_validation_forward
    -->
    <record id="tier_definition_claim_manager" model="tier.definition">
        <field name="name">Expense Claim - Department Manager (ชั้นที่ 1 หัวหน้าแผนก)</field>
        <field name="model_id" ref="model_od19_expense_claim"/>
        <field name="review_type">group</field>
        <field name="reviewer_group_id" ref="hr_expense.group_hr_expense_manager"/>
        <field name="definition_type">domain</field>
        <field name="definition_domain">[(1, '=', 1)]</field>
        <field name="sequence">30</field>
        <field name="approve_sequence" eval="True"/>
        <field name="has_forward" eval="True"/>
        <field name="company_id" eval="False"/>
        <field name="notify_on_create" eval="True"/>
        <field name="notify_on_pending" eval="True"/>
    </record>

    <record id="tier_definition_claim_accounting" model="tier.definition">
        <field name="name">Expense Claim - Accounting (ชั้นที่ 2 บัญชี)</field>
        <field name="model_id" ref="model_od19_expense_claim"/>
        <field name="review_type">group</field>
        <field name="reviewer_group_id" ref="account.group_account_manager"/>
        <field name="definition_type">domain</field>
        <field name="definition_domain">[(1, '=', 1)]</field>
        <field name="sequence">20</field>
        <field name="approve_sequence" eval="True"/>
        <field name="has_forward" eval="True"/>
        <field name="company_id" eval="False"/>
        <field name="notify_on_create" eval="True"/>
        <field name="notify_on_pending" eval="True"/>
    </record>

    <record id="tier_definition_claim_ceo" model="tier.definition">
        <field name="name">Expense Claim - CEO (ชั้นที่ 3 CEO)</field>
        <field name="model_id" ref="model_od19_expense_claim"/>
        <field name="review_type">group</field>
        <field name="reviewer_group_id" ref="od19_hr_expense_thai.group_od19_expense_ceo_approver"/>
        <field name="definition_type">domain</field>
        <field name="definition_domain">[(1, '=', 1)]</field>
        <field name="sequence">10</field>
        <field name="approve_sequence" eval="True"/>
        <field name="has_forward" eval="True"/>
        <field name="company_id" eval="False"/>
        <field name="notify_on_create" eval="True"/>
        <field name="notify_on_pending" eval="True"/>
    </record>
</odoo>
```

- [ ] **Step 3: ถอด `tier.definition` เดิมออกจาก `od19_hr_expense_thai`**

ลบไฟล์ `custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml` และแก้ `custom_addons/od19_hr_expense_thai/__manifest__.py`:

```python
# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Thai Localization',
    'author': 'OD19',
    'version': '19.0.1.4.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Thai HR expense extensions: cash reimbursement, multi-tier approval',
    'depends': [
        'hr_expense',
        'hr_expense_tier_validation',
        'base_tier_validation',
        'base_tier_validation_forward',
        'od19_hr_expense_enhanced',
        'od19_accounting_features',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_expense_security.xml',
        'views/hr_expense_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    "icon": "/od19_hr_expense_thai/static/description/icon.svg",
}
```
(ตัดบรรทัด `'data/tier_definition_data.xml',` ออก — **คง** `security/` และ `views/`)

- [ ] **Step 4: สร้าง migration ลบ tier.definition เดิม (noupdate ค้างใน DB)**

สร้าง `custom_addons/od19_hr_expense_thai/migrations/19.0.1.4.0/post-migrate.py`:

```python
# -*- coding: utf-8 -*-
"""ลบ tier.definition 3 รายการบน hr.expense ที่เคย seed ไว้ (ย้ายไปหัวใบแล้ว).

ไฟล์ data เดิมเป็น ``noupdate=1`` จึงไม่ถูกลบอัตโนมัติเมื่อถอดออกจาก manifest
ต้องลบ record + ir.model.data ที่ค้างในฐานข้อมูล
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlids = [
        "od19_hr_expense_thai.tier_definition_hr_expense_manager",
        "od19_hr_expense_thai.tier_definition_hr_expense_accounting",
        "od19_hr_expense_thai.tier_definition_hr_expense_ceo",
    ]
    definitions = env["tier.definition"].browse()
    for xmlid in xmlids:
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            definitions |= rec
    if definitions:
        # ล้าง review ที่อ้างถึงก่อน (กัน FK/ตรวจสอบตอน unlink)
        env["tier.review"].search([("definition_id", "in", definitions.ids)]).unlink()
        _logger.info("Removing %s legacy hr.expense tier definition(s)", len(definitions))
        definitions.unlink()
    # ทำความสะอาด ir.model.data ที่อาจค้าง
    stray = env["ir.model.data"].search([
        ("module", "=", "od19_hr_expense_thai"),
        ("name", "in", [x.split(".")[-1] for x in xmlids]),
    ])
    if stray:
        stray.unlink()
```

- [ ] **Step 5: ปรับเทสต์เดิมของ `od19_hr_expense_thai`**

แก้ `custom_addons/od19_hr_expense_thai/tests/test_hr_expense_tier.py` ให้ตรงกับสภาพใหม่ (tier ย้ายไปหัวใบแล้ว) — แทนเนื้อหาด้วย:

```python
# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseTierMoved(TransactionCase):
    """หลังย้ายสายอนุมัติไปที่หัวใบ od19.expense.claim
    hr.expense ต้องไม่มี tier.definition ที่ยัง active เหลืออยู่"""

    def test_no_active_tier_definition_on_hr_expense(self):
        defs = self.env["tier.definition"].search([
            ("model", "=", "hr.expense"),
            ("company_id", "=", False),
        ])
        self.assertFalse(defs)

    def test_ceo_group_still_exists(self):
        group = self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver")
        self.assertEqual(group.name, "Expense CEO Approver")
```

> ตรวจ `tests/__init__.py` ของ `od19_hr_expense_thai` ยังคง import `test_hr_expense_tier` (ไม่ต้องแก้)

- [ ] **Step 6: รันเทสต์ T2/T3/T4/T5/T8**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim,od19_hr_expense_thai
```
Expected: **PASS** ทั้งหมด (3 definitions บนหัวใบ, ไม่มีบน hr.expense, อนุมัติครบ 3 ชั้น → หัวใบ+บรรทัด approved, ข้ามขั้นไม่ได้)

---

## Task 4: Views + เมนู (backend)

**Files:**
- Create: `custom_addons/od19_hr_expense_claim/views/od19_expense_claim_views.xml`

- [ ] **Step 1: สร้างไฟล์ views**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_od19_expense_claim_list" model="ir.ui.view">
        <field name="name">od19.expense.claim.list</field>
        <field name="model">od19.expense.claim</field>
        <field name="arch" type="xml">
            <list string="Expense Claims"
                  decoration-info="state == 'draft'"
                  decoration-warning="state in ('submitted', 'refused')"
                  decoration-success="state in ('approved', 'posted', 'paid')">
                <field name="name"/>
                <field name="employee_id"/>
                <field name="department_id" optional="show"/>
                <field name="date"/>
                <field name="total_amount" sum="Total"/>
                <field name="payment_mode" optional="hide"/>
                <field name="state" widget="badge"/>
                <field name="currency_id" column_invisible="1"/>
            </list>
        </field>
    </record>

    <record id="view_od19_expense_claim_form" model="ir.ui.view">
        <field name="name">od19.expense.claim.form</field>
        <field name="model">od19.expense.claim</field>
        <field name="arch" type="xml">
            <form string="Expense Claim">
                <header>
                    <button name="action_submit" type="object" string="Submit"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_post" type="object" string="Post Journal Entries"
                            class="btn-primary" invisible="state != 'approved'"/>
                    <button name="action_refuse" type="object" string="Refuse"
                            invisible="state not in ('submitted', 'approved')"/>
                    <button name="action_reset" type="object" string="Reset to Draft"
                            invisible="state != 'refused'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,submitted,approved,posted,paid,refused"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="employee_id"
                                   readonly="state != 'draft'"/>
                            <field name="department_id" readonly="1"/>
                            <field name="date" readonly="state != 'draft'"/>
                            <field name="payment_mode" readonly="state != 'draft'"/>
                        </group>
                        <group>
                            <field name="total_amount"/>
                            <field name="currency_id" groups="base.group_multi_currency"/>
                            <field name="company_id" groups="base.group_multi_company"/>
                            <field name="submit_date" readonly="1"/>
                            <field name="approval_date" readonly="1"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Expense Lines" name="lines">
                            <field name="line_ids"
                                   context="{'default_employee_id': employee_id,
                                             'default_payment_mode': payment_mode,
                                             'default_company_id': company_id}">
                                <list editable="bottom">
                                    <field name="name"/>
                                    <field name="product_id"/>
                                    <field name="quantity"/>
                                    <field name="price_unit"/>
                                    <field name="total_amount" sum="Total"/>
                                    <field name="payment_mode" column_invisible="1"/>
                                    <field name="employee_id" column_invisible="1"/>
                                    <field name="company_id" column_invisible="1"/>
                                    <field name="currency_id" column_invisible="1"/>
                                </list>
                            </field>
                        </page>
                        <page string="Notes" name="notes">
                            <field name="note" placeholder="Internal notes..."/>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="view_od19_expense_claim_kanban" model="ir.ui.view">
        <field name="name">od19.expense.claim.kanban</field>
        <field name="model">od19.expense.claim</field>
        <field name="arch" type="xml">
            <kanban default_group_by="state" class="o_kanban_small_column">
                <field name="name"/>
                <field name="employee_id"/>
                <field name="total_amount"/>
                <field name="currency_id"/>
                <field name="state"/>
                <templates>
                    <t t-name="card">
                        <div class="d-flex justify-content-between">
                            <field name="name" class="fw-bold"/>
                            <field name="state" widget="badge"/>
                        </div>
                        <div><field name="employee_id"/></div>
                        <div class="text-end">
                            <field name="total_amount" widget="monetary"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <record id="view_od19_expense_claim_search" model="ir.ui.view">
        <field name="name">od19.expense.claim.search</field>
        <field name="model">od19.expense.claim</field>
        <field name="arch" type="xml">
            <search string="Search Expense Claims">
                <field name="name"/>
                <field name="employee_id"/>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <filter string="Submitted" name="submitted" domain="[('state', '=', 'submitted')]"/>
                <filter string="Approved" name="approved" domain="[('state', '=', 'approved')]"/>
                <filter string="Posted" name="posted" domain="[('state', '=', 'posted')]"/>
                <filter string="Refused" name="refused" domain="[('state', '=', 'refused')]"/>
                <separator/>
                <filter string="My Claims" name="my_claims"
                        domain="[('employee_id.user_id', '=', uid)]"/>
                <group>
                    <filter string="Employee" name="group_employee" context="{'group_by': 'employee_id'}"/>
                    <filter string="Department" name="group_department" context="{'group_by': 'department_id'}"/>
                    <filter string="Status" name="group_state" context="{'group_by': 'state'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="action_od19_expense_claim_my" model="ir.actions.act_window">
        <field name="name">My Expense Claims</field>
        <field name="res_model">od19.expense.claim</field>
        <field name="view_mode">kanban,list,form</field>
        <field name="domain">[('employee_id.user_id', '=', uid)]</field>
        <field name="context">{'search_default_my_claims': 1}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">Create your first expense claim</p>
            <p>รวมค่าใช้จ่ายหลายรายการไว้ในใบเบิกเดียว แล้วอนุมัติครั้งเดียว</p>
        </field>
    </record>

    <record id="action_od19_expense_claim_all" model="ir.actions.act_window">
        <field name="name">All Expense Claims</field>
        <field name="res_model">od19.expense.claim</field>
        <field name="view_mode">list,kanban,form</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">No expense claims yet</p>
        </field>
    </record>

    <menuitem
        id="menu_od19_expense_claim_my"
        name="My Expense Claims"
        parent="hr_expense.menu_hr_expense_root"
        action="action_od19_expense_claim_my"
        sequence="20"
    />
    <menuitem
        id="menu_od19_expense_claim_all"
        name="All Expense Claims"
        parent="hr_expense.menu_hr_expense_root"
        action="action_od19_expense_claim_all"
        sequence="21"
        groups="hr_expense.group_hr_expense_manager,account.group_account_manager"
    />

</odoo>
```

- [ ] **Step 2: ตรวจว่า view โหลดได้ (install/upgrade)**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim
```
Expected: **PASS** (ติดตั้งผ่าน — ถ้า view XML ผิดจะ error ตอน load)

---

## Task 5: ir.rule สิทธิ์ (ของตัวเอง + ผู้อนุมัติ)

**Files:**
- Create: `custom_addons/od19_hr_expense_claim/security/od19_expense_claim_security.xml`
- Modify: `custom_addons/od19_hr_expense_claim/tests/test_expense_claim.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (T9)**

เพิ่มใน `tests/test_expense_claim.py`:

```python
    # ---------------------------------------------------------------
    # T9: พนักงานเห็นเฉพาะใบเบิกของตัวเอง (หลังบ้าน)
    # ---------------------------------------------------------------
    def test_employee_sees_only_own_claims(self):
        employee_user = new_test_user(
            self.env, login="od19_claim_emp",
            name="Claim Employee User",
            groups="base.group_user,hr_expense.group_hr_expense_user",
        )
        other_employee = self.env["hr.employee"].create({
            "name": "Other Employee",
            "user_id": employee_user.id,
        })
        own = self._make_claim()          # employee = self.employee (user = test user หลัก)
        own.write({"employee_id": other_employee.id})
        foreign = self._make_claim([
            {"name": "Foreign", "total_amount": 10.0},
        ])
        visible = self.Claim.with_user(employee_user).search([])
        self.assertIn(own, visible)
        self.assertNotIn(foreign, visible)
```

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim
```
Expected: **FAIL** (ไม่มีการกรองสิทธิ์ — พนักงานเห็นทุกใบ)

- [ ] **Step 2: สร้าง ir.rule**

สร้าง `security/od19_expense_claim_security.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- พนักงานเห็นเฉพาะใบเบิกของตัวเอง (employee_id.user_id หรือ create_uid) -->
    <record id="ir_rule_od19_expense_claim_own" model="ir.rule">
        <field name="name">Expense Claim: own records</field>
        <field name="model_id" ref="model_od19_expense_claim"/>
        <field name="domain_force">['|',
            ('employee_id.user_id', '=', user.id),
            ('create_uid', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <!-- ผู้อนุมัติ (หัวหน้าแผนก/บัญชี/CEO) เห็นทั้งหมด -->
    <record id="ir_rule_od19_expense_claim_all" model="ir.rule">
        <field name="name">Expense Claim: approvers see all</field>
        <field name="model_id" ref="model_od19_expense_claim"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[
            (4, ref('hr_expense.group_hr_expense_manager')),
            (4, ref('account.group_account_manager')),
            (4, ref('od19_hr_expense_thai.group_od19_expense_ceo_approver'))]"/>
    </record>

    <!-- multi-company (global) -->
    <record id="ir_rule_od19_expense_claim_company" model="ir.rule">
        <field name="name">Expense Claim: multi-company</field>
        <field name="model_id" ref="model_od19_expense_claim"/>
        <field name="global" eval="True"/>
        <field name="domain_force">[('company_id', 'in', company_ids)]</field>
    </record>
</odoo>
```

> กฎกลุ่ม (ไม่ global) ที่เข้าเงื่อนไขถูก **OR** กัน → ผู้อนุมัติที่อยู่ในกลุ่ม manager/account/CEO จะเห็นทั้งหมด ส่วนพนักงานทั่วไป (base.group_user) เห็นเฉพาะของตัวเอง

- [ ] **Step 3: รันเทสต์ T9**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim
```
Expected: **PASS** (พนักงานเห็นเฉพาะของตัวเอง)

---

## Task 6: เทสต์ส่วนที่เหลือของ Phase 1 (T6, T7, K6)

**Files:**
- Modify: `custom_addons/od19_hr_expense_claim/tests/test_expense_claim.py`

- [ ] **Step 1: เพิ่มเทสต์ T6/T7/K6**

```python
    # ---------------------------------------------------------------
    # T6: ปฏิเสธที่หัวใบ -> บรรทัดทุกตัว refused
    # ---------------------------------------------------------------
    def test_refuse_propagates_to_lines(self):
        claim = self._make_claim([
            {"name": "A", "total_amount": 10.0},
            {"name": "B", "total_amount": 20.0},
        ])
        claim.action_submit()
        claim.action_refuse()
        self.assertEqual(claim.state, "refused")
        self.assertTrue(all(l.approval_state == "refused" for l in claim.line_ids))

    def test_reset_after_refuse(self):
        claim = self._make_claim()
        claim.action_submit()
        claim.action_refuse()
        claim.action_reset()
        self.assertEqual(claim.state, "draft")
        self.assertTrue(all(not l.approval_state for l in claim.line_ids))

    # ---------------------------------------------------------------
    # T7: โพสต์บรรทัดจากหัวใบเมื่ออนุมัติครบ
    # ---------------------------------------------------------------
    def test_post_after_approval(self):
        claim = self._make_claim([
            {"name": "A", "total_amount": 100.0},
        ])
        self._approve_claim(claim)
        self.assertEqual(claim.state, "approved")
        claim.action_post()
        self.assertEqual(claim.state, "posted")
        self.assertTrue(all(l.state in ("posted", "paid") for l in claim.line_ids))

    def test_post_before_approval_raises(self):
        claim = self._make_claim()
        with self.assertRaises(UserError):
            claim.action_post()

    # ---------------------------------------------------------------
    # K6: ใบเดียวห้ามผสม payment_mode
    # ---------------------------------------------------------------
    def test_mixed_payment_mode_raises(self):
        with self.assertRaises(ValidationError):
            self.Claim.create({
                "employee_id": self.employee.id,
                "company_id": self.env.company.id,
                "line_ids": [
                    Command.create({
                        "name": "Own", "product_id": self.product.id,
                        "total_amount": 10.0, "employee_id": self.employee.id,
                        "payment_mode": "own_account",
                        "company_id": self.env.company.id,
                    }),
                    Command.create({
                        "name": "Company", "product_id": self.product.id,
                        "total_amount": 20.0, "employee_id": self.employee.id,
                        "payment_mode": "company_account",
                        "company_id": self.env.company.id,
                    }),
                ],
            })
```

- [ ] **Step 2: รันเทสต์ทั้งหมดของ Phase 1**

Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_hr_expense_claim,od19_hr_expense_thai
```
Expected: **PASS** ทุกเทสต์ (T1–T9 + K6)

> หมายเหตุ T7: การโพสต์ต้องมีบัญชี/สินค้าที่ตั้งค่าได้ครบ — เทสต์ใช้ `AccountTestInvoicingCommon` จึงมี `company_data` พร้อม ถ้า `action_post` ต้องรัน accounting chart เพิ่ม ให้ปรับใน Step นี้ก่อนไปต่อ

---

## Task 7: ติดตั้งบน pdev + ตรวจ + commit

**Files:** ไม่มี (ติดตั้ง + commit)

- [ ] **Step 1: อัปเดตโมดูลบน `odoo19_pdev`**

Run (ตามวิธที่โปรเจกต์ใช้):
```powershell
python odoo-bin -c odoo.conf -d odoo19_pdev -u od19_hr_expense_claim,od19_hr_expense_thai --stop-after-init
```
Expected: ไม่มี traceback · โมดูลติดตั้ง/อัปเดตผ่าน · migration `19.0.1.4.0` ของ `od19_hr_expense_thai` ลบ tier เดิมสำเร็จ

- [ ] **Step 2: ตรวจด้วย grep ว่าไม่มีการแก้ core / OCA**

Run:
```powershell
git status -sb
```
Expected: ไฟล์ที่เปลี่ยนอยู่เฉพาะ `custom_addons/od19_hr_expense_claim/**`, `custom_addons/od19_hr_expense_thai/**` และ `docs/**` — **ไม่มี** ไฟล์ใน `addons/`, `odoo/`, `third_party/`

- [ ] **Step 3: commit (Conventional Commits · เจาะจงไฟล์ · ห้าม `git add -A`)**

Run:
```powershell
git add custom_addons/od19_hr_expense_claim custom_addons/od19_hr_expense_thai
git commit -m "feat(expense-claim): add expense claim header with 3-tier approval (Phase 1)"
```
Expected: commit สำเร็จ · **ไม่** push (ตาม pipeline S1 commit ก่อน แล้วรอ +24 ชม.)

- [ ] **Step 4: รายงานผลตาม AGENTS.md**

รายงาน: commit SHA, เทสต์ที่ผ่าน, ผล install/update, ความเสี่ยง/ประเด็นค้าง (K5–K9)

---

## Self-Review Checklist (ก่อนส่ง Plan)

- [ ] ทุก Task มีเทสต์ก่อนโค้ด (TDD) — T1, T2, T3, T4, T5, T6, T7, T8, T9, K6
- [ ] ไม่มีการแก้ Odoo core / `third_party/oca/`
- [ ] คำสั่งรันเทสต์ตรงกับ `run-tests.ps1` ของโปรเจกต์
- [ ] commit ใช้ Conventional Commits + เจาะจงไฟล์ (ไม่ `git add -A`)
- [ ] สอดคล้องกับ Spec rev2 ที่ล็อก K1–K4
- [ ] ประเด็นที่ยังเปิด (K5 manager_id, K7 migration ข้อมูลเดิม, K8 Approval Center source, K9 ลำดับ seq) ถูกยกไปเฟสถัดไป (Phase 2–3) ไม่ทำในเฟสนี้
