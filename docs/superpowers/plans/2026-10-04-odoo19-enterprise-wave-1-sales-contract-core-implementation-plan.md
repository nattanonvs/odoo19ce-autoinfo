# Odoo 19 CE Wave 1: Sales Contract Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ส่งมอบชุด addon สำหรับงานขายที่รองรับทั้ง `One-time Sales` และ `Contract-based Sales` พร้อม project context, contract policy, billing evidence, repeat-business reporting และมุมยอดรวมทั้งโครงการ โดยไม่แก้ Odoo core

**Architecture:** ใช้แนวทาง `OCA-first, custom-second` โดยแยก implementation เป็น 5 addon ชัดเจน: project context, contract core, billing evidence, reporting และ OCA workflow bridge เพื่อให้ติดตั้ง/ถอนออกได้อย่างปลอดภัยและไม่เกิด hidden coupling ข้ามโดเมน แกนข้อมูลสำคัญทั้งหมดจะผูกผ่าน `sale.order`, `res.partner`, `project context`, `master contract`, `contract activity` และ `billing evidence` พร้อม test ทีละชั้นตั้งแต่ model จนถึง end-to-end reporting

**Tech Stack:** Odoo 19 CE, Python, XML, CSV security, PostgreSQL, Odoo test framework, pytest-style assertions in Odoo tests, Git, Markdown, OCA `server-backend`, `server-ux`, `server-tools`, `sale-workflow`, and `sale-blanket`

## Discovery Evidence

- Approved Wave 1 Sales spec: `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
- Odoo 15 production reference source code: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
- Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Sales OCA recommendations: `docs/superpowers/programs/odoo19-enterprise/sales/oca-installation-recommendations.md`
- Existing Odoo 19 baseline context: `custom_addons/`, `third_party/oca/`, และ `docs/superpowers/programs/odoo19-enterprise/sales/`

---

## File Structure

**Create**
- `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`
- `docs/superpowers/programs/odoo19-enterprise/sales/addon-boundaries.md`
- `custom_addons/README.md`
- `custom_addons/od19_sales_project_context/__init__.py`
- `custom_addons/od19_sales_project_context/__manifest__.py`
- `custom_addons/od19_sales_project_context/models/__init__.py`
- `custom_addons/od19_sales_project_context/models/project_context.py`
- `custom_addons/od19_sales_project_context/models/sale_order.py`
- `custom_addons/od19_sales_project_context/security/ir.model.access.csv`
- `custom_addons/od19_sales_project_context/views/project_context_views.xml`
- `custom_addons/od19_sales_project_context/views/sale_order_views.xml`
- `custom_addons/od19_sales_project_context/tests/__init__.py`
- `custom_addons/od19_sales_project_context/tests/test_project_context.py`
- `custom_addons/od19_sales_contract_core/__init__.py`
- `custom_addons/od19_sales_contract_core/__manifest__.py`
- `custom_addons/od19_sales_contract_core/models/__init__.py`
- `custom_addons/od19_sales_contract_core/models/sales_contract.py`
- `custom_addons/od19_sales_contract_core/models/sale_order.py`
- `custom_addons/od19_sales_contract_core/security/ir.model.access.csv`
- `custom_addons/od19_sales_contract_core/views/sales_contract_views.xml`
- `custom_addons/od19_sales_contract_core/views/sale_order_views.xml`
- `custom_addons/od19_sales_contract_core/tests/__init__.py`
- `custom_addons/od19_sales_contract_core/tests/test_contract_policy.py`
- `custom_addons/od19_sales_billing_evidence/__init__.py`
- `custom_addons/od19_sales_billing_evidence/__manifest__.py`
- `custom_addons/od19_sales_billing_evidence/models/__init__.py`
- `custom_addons/od19_sales_billing_evidence/models/billing_evidence.py`
- `custom_addons/od19_sales_billing_evidence/models/sale_order.py`
- `custom_addons/od19_sales_billing_evidence/security/ir.model.access.csv`
- `custom_addons/od19_sales_billing_evidence/views/billing_evidence_views.xml`
- `custom_addons/od19_sales_billing_evidence/views/sale_order_views.xml`
- `custom_addons/od19_sales_billing_evidence/tests/__init__.py`
- `custom_addons/od19_sales_billing_evidence/tests/test_billing_readiness.py`
- `custom_addons/od19_sales_reporting/__init__.py`
- `custom_addons/od19_sales_reporting/__manifest__.py`
- `custom_addons/od19_sales_reporting/models/__init__.py`
- `custom_addons/od19_sales_reporting/models/report_sales_project_revenue.py`
- `custom_addons/od19_sales_reporting/models/report_repeat_business.py`
- `custom_addons/od19_sales_reporting/views/report_sales_project_revenue_views.xml`
- `custom_addons/od19_sales_reporting/views/report_repeat_business_views.xml`
- `custom_addons/od19_sales_reporting/security/ir.model.access.csv`
- `custom_addons/od19_sales_reporting/tests/__init__.py`
- `custom_addons/od19_sales_reporting/tests/test_sales_reporting.py`
- `custom_addons/od19_sales_oca_bridge_workflow/__init__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/models/__init__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`
- `custom_addons/od19_sales_oca_bridge_workflow/tests/__init__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`

**Modify**
- `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`

**Reuse Without Code Changes**
- `addons/sale/`
- `Odoo15Backup/odoo15_oca_mapping.xlsx`
- `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
- `docs/superpowers/programs/odoo19-enterprise/sales/oca-installation-recommendations.md`

## Scope Note

Wave 1 สเปกนี้กว้าง แต่ยังอยู่ใน bounded context เดียวคือ `Sales Commercial Core` แผนนี้จะแยก implementation เป็นหลาย addon เพื่อให้ deploy ได้ปลอดภัยและ review ได้ง่าย โดย intentionally ยังไม่ลงลึก `service execution`, `stock execution`, และ `accounting posting` ตาม deferred scope ของสเปก

การเลือก OCA เพิ่มเติมนอก baseline ของแผนนี้ ให้ยึดตาม `docs/superpowers/programs/odoo19-enterprise/sales/oca-installation-recommendations.md` เพื่อคุมไม่ให้ดึงโมดูลที่แตะ accounting/stock/detail เร็วเกิน wave ที่เหมาะ

## Precondition

ก่อนเริ่ม Task 2 ให้เตรียม addon path สำหรับ local dev/test ดังนี้:

```bash
git clone --branch 19.0 https://github.com/OCA/server-backend.git third_party/oca/server-backend
git clone --branch 19.0 https://github.com/OCA/server-ux.git third_party/oca/server-ux
git clone --branch 19.0 https://github.com/OCA/server-tools.git third_party/oca/server-tools
git clone --branch 19.0 https://github.com/OCA/sale-workflow.git third_party/oca/sale-workflow
git clone --branch 19.0 https://github.com/OCA/sale-blanket.git third_party/oca/sale-blanket
```

และใช้ `addons-path` แบบนี้ในทุกคำสั่งทดสอบ:

```bash
addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket
```

### Task 1: ล็อก OCA Fit-Gap และ Addon Boundaries

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/sales/addon-boundaries.md`
- Create: `custom_addons/README.md`

- [ ] **Step 1: เขียนเอกสาร fit-gap ของ OCA ที่ต้องประเมิน**

สร้าง `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md` ด้วยเนื้อหานี้:

```md
# Sales OCA Fit-Gap

## Required Now Baseline
| Module | Source | Adoption Mode | Why |
| --- | --- | --- | --- |
| `base_user_role` | OCA/server-backend | Required now | ใช้แยกบทบาท Sales / Billing / Manager ให้ชัด |
| `sale_order_revision` | OCA/sale-workflow + OCA/server-ux | Required now | เก็บ revision history ของ quotation / order โดยต้องมี `base_revision` |
| `sale_delivery_state` | OCA/sale-workflow | Required now | ใช้สถานะส่งมอบระหว่างทางก่อนถึง billing readiness |
| `sale_exception` | OCA/sale-workflow + OCA/server-tools | Required now via bridge | ใช้ exception / approval rule โดยต้องมี `base_exception` |
| `sale_blanket_order` | OCA/sale-blanket | Required now via bridge | ใช้เป็นฐานเอกสารเชิงพาณิชย์ของ contract-based sale โดยให้ custom contract model คุม policy |

## Deferred Pending Confirmation
| Module | Source | Current Decision | Why Deferred |
| --- | --- | --- | --- |
| `sale_tier_validation` | OCA/sale-workflow + OCA/server-ux | Deferred pending 19.0 confirmation | รอ confirm 19.0 baseline และ `base_tier_validation` |
| `sale_invoice_plan` | OCA/sale-workflow | Deferred pending 19.0 confirmation | รอ confirm 19.0 baseline |

## Custom Layers Still Needed
- `od19_sales_project_context` สำหรับผู้รับเหมา เจ้าของโครงการ และโครงการ
- `od19_sales_contract_core` สำหรับ master contract, amendment, activity, policy
- `od19_sales_billing_evidence` สำหรับ evidence, attachment rules, billing readiness
- `od19_sales_reporting` สำหรับ repeat-business และ project revenue views
- `od19_sales_oca_bridge_workflow` สำหรับ wiring กับ OCA modules ในกลุ่ม required-now และ integration point ของกลุ่ม deferred

## Rejected for Wave 1
- custom approval engine ใหม่ทั้งหมด
- custom revision engine ใหม่ทั้งหมด
- custom delivery status ใหม่ทั้งหมด
```

- [ ] **Step 2: เขียนเอกสารแบ่ง bounded context ของ addon**

สร้าง `docs/superpowers/programs/odoo19-enterprise/sales/addon-boundaries.md` ด้วยเนื้อหานี้:

```md
# Sales Addon Boundaries

## `od19_sales_project_context`
- เก็บ `Commercial Customer`, `Project Owner`, `Project`
- ผูก context นี้เข้ากับ `sale.order`

## `od19_sales_contract_core`
- เก็บ `Master Contract`, `Contract Amendment`, `Contract Activity`
- เก็บ contract policy เช่น limit mode, over-limit mode, billing cycle

## `od19_sales_billing_evidence`
- เก็บ evidence types, evidence records, required attachment rules
- คำนวณ `billing_readiness_state`

## `od19_sales_reporting`
- ให้ report SQL views สำหรับ repeat business และ project revenue

## `od19_sales_oca_bridge_workflow`
- wire กับ `sale_order_revision`
- wire กับ `sale_delivery_state`
- wire กับ `sale_exception` family ที่พึ่ง `base_exception`
- wire กับ `sale_blanket_order`
- เตรียม optional integration point สำหรับ `sale_tier_validation` หลังยืนยัน 19.0 baseline และ `base_tier_validation`
- เตรียม optional integration point สำหรับ `sale_invoice_plan` หลังยืนยัน 19.0 baseline
```

- [ ] **Step 3: เพิ่ม README ของ custom addon namespace**

สร้าง `custom_addons/README.md` ด้วยเนื้อหานี้:

```md
# Custom Addons

โฟลเดอร์นี้เก็บ company-specific addons ของโครงการ Odoo 19 CE เท่านั้น

หลักการ:
- ไม่แก้ Odoo core
- ใช้ OCA ก่อนเสมอ
- 1 addon = 1 bounded context
- ทุก addon ต้อง install, upgrade, uninstall ได้
```

- [ ] **Step 4: ตรวจ whitespace**

Run:

```bash
git diff --check
```

Expected:

```text
ไม่มี error เรื่อง trailing whitespace หรือ malformed diff
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md docs/superpowers/programs/odoo19-enterprise/sales/addon-boundaries.md custom_addons/README.md
git commit -m "docs(sales): lock Wave 1 OCA fit-gap and addon boundaries"
```

### Task 2: สร้าง `od19_sales_project_context`

**Files:**
- Create: `custom_addons/od19_sales_project_context/__init__.py`
- Create: `custom_addons/od19_sales_project_context/__manifest__.py`
- Create: `custom_addons/od19_sales_project_context/models/__init__.py`
- Create: `custom_addons/od19_sales_project_context/models/project_context.py`
- Create: `custom_addons/od19_sales_project_context/models/sale_order.py`
- Create: `custom_addons/od19_sales_project_context/security/ir.model.access.csv`
- Create: `custom_addons/od19_sales_project_context/views/project_context_views.xml`
- Create: `custom_addons/od19_sales_project_context/views/sale_order_views.xml`
- Create: `custom_addons/od19_sales_project_context/tests/__init__.py`
- Create: `custom_addons/od19_sales_project_context/tests/test_project_context.py`

- [ ] **Step 1: เขียน failing test สำหรับ project context**

สร้าง `custom_addons/od19_sales_project_context/tests/test_project_context.py` ด้วยโครงนี้:

```python
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestProjectContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create({"name": "Main Contractor"})
        self.owner = self.env["res.partner"].create({"name": "Project Owner"})

    def test_sale_order_requires_project_context_consistency(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Airport Expansion",
                "project_owner_id": self.owner.id,
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.contractor.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

        self.assertEqual(order.od19_project_id.project_owner_id, order.od19_project_owner_id)

    def test_project_owner_mismatch_is_blocked(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Hospital Retrofit",
                "project_owner_id": self.owner.id,
            }
        )
        another_owner = self.env["res.partner"].create({"name": "Another Owner"})

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": self.contractor.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": another_owner.id,
                }
            )
```

- [ ] **Step 2: รัน test ให้ล้มก่อน**

Run:

```bash
python odoo-bin -d test_w1_sales_context --test-enable -i sale,od19_sales_project_context --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_project_context
```

Expected:

```text
ModuleNotFoundError หรือ import error เพราะ addon ยังไม่ถูกสร้างครบ
```

- [ ] **Step 3: สร้าง addon และ model ของ project context**

สร้าง `custom_addons/od19_sales_project_context/__manifest__.py`:

```python
{
    "name": "OD19 Sales Project Context",
    "version": "19.0.1.0.0",
    "depends": ["sale_management", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_context_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

สร้าง `custom_addons/od19_sales_project_context/models/project_context.py`:

```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Od19SalesProject(models.Model):
    _name = "od19.sales.project"
    _description = "Sales Project Context"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    project_owner_id = fields.Many2one("res.partner", required=True, tracking=True)
    contractor_ids = fields.Many2many("res.partner", string="Known Contractors")
    active = fields.Boolean(default=True)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_sale_mode = fields.Selection(
        [("one_time", "One-time"), ("contract", "Contract-based")],
        default="one_time",
        required=True,
        tracking=True,
    )
    od19_project_id = fields.Many2one("od19.sales.project", tracking=True)
    od19_project_owner_id = fields.Many2one("res.partner", tracking=True)

    @api.constrains("od19_project_id", "od19_project_owner_id")
    def _check_project_owner_consistency(self):
        for order in self:
            if (
                order.od19_project_id
                and order.od19_project_owner_id
                and order.od19_project_id.project_owner_id != order.od19_project_owner_id
            ):
                raise ValidationError(
                    "Project owner on sale order must match project owner on selected project."
                )
```

สร้าง `custom_addons/od19_sales_project_context/security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_sales_project_user,access.od19.sales.project.user,model_od19_sales_project,base.group_user,1,1,1,0
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run:

```bash
python odoo-bin -d test_w1_sales_context --test-enable -i sale,od19_sales_project_context --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_project_context
```

Expected:

```text
Ran 2 tests ... OK
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add custom_addons/od19_sales_project_context
git commit -m "feat(sales): add project context for sale orders"
```

### Task 3: สร้าง `od19_sales_contract_core`

**Files:**
- Create: `custom_addons/od19_sales_contract_core/__init__.py`
- Create: `custom_addons/od19_sales_contract_core/__manifest__.py`
- Create: `custom_addons/od19_sales_contract_core/models/__init__.py`
- Create: `custom_addons/od19_sales_contract_core/models/sales_contract.py`
- Create: `custom_addons/od19_sales_contract_core/models/sale_order.py`
- Create: `custom_addons/od19_sales_contract_core/security/ir.model.access.csv`
- Create: `custom_addons/od19_sales_contract_core/views/sales_contract_views.xml`
- Create: `custom_addons/od19_sales_contract_core/views/sale_order_views.xml`
- Create: `custom_addons/od19_sales_contract_core/tests/__init__.py`
- Create: `custom_addons/od19_sales_contract_core/tests/test_contract_policy.py`

- [ ] **Step 1: เขียน failing test สำหรับ over-limit policy และ activity order**

สร้าง `custom_addons/od19_sales_contract_core/tests/test_contract_policy.py`:

```python
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestContractPolicy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create({"name": "Contractor A"})
        self.owner = self.env["res.partner"].create({"name": "Owner A"})
        self.project = self.env["od19.sales.project"].create(
            {"name": "Metro Line", "project_owner_id": self.owner.id}
        )

    def test_activity_must_respect_block_policy(self):
        contract = self.env["od19.sales.contract"].create(
            {
                "name": "MC-0001",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": 1000.0,
                "over_limit_policy": "block",
            }
        )

        self.env["od19.sales.contract.activity"].create(
            {
                "name": "ACT-001",
                "contract_id": contract.id,
                "amount_to_consume": 900.0,
            }
        )

        with self.assertRaises(ValidationError):
            self.env["od19.sales.contract.activity"].create(
                {
                    "name": "ACT-002",
                    "contract_id": contract.id,
                    "amount_to_consume": 200.0,
                }
            )
```

- [ ] **Step 2: รัน test ให้ล้มก่อน**

Run:

```bash
python odoo-bin -d test_w1_sales_contract --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_contract_core
```

Expected:

```text
ImportError หรือ test fail เพราะ model contract ยังไม่มี
```

- [ ] **Step 3: สร้าง model contract, amendment, activity**

สร้าง `custom_addons/od19_sales_contract_core/__manifest__.py`:

```python
{
    "name": "OD19 Sales Contract Core",
    "version": "19.0.1.0.0",
    "depends": ["sale_management", "mail", "od19_sales_project_context"],
    "data": [
        "security/ir.model.access.csv",
        "views/sales_contract_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

สร้าง `custom_addons/od19_sales_contract_core/models/sales_contract.py`:

```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Od19SalesContract(models.Model):
    _name = "od19.sales.contract"
    _description = "Sales Master Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    od19_project_id = fields.Many2one("od19.sales.project", required=True, tracking=True)
    limit_amount = fields.Float(required=True)
    consumed_amount = fields.Float(compute="_compute_consumed_amount", store=True)
    over_limit_policy = fields.Selection(
        [("warn", "Warn"), ("approval", "Approval"), ("block", "Block")],
        default="warn",
        required=True,
    )
    activity_ids = fields.One2many("od19.sales.contract.activity", "contract_id")

    @api.depends("activity_ids.amount_to_consume")
    def _compute_consumed_amount(self):
        for contract in self:
            contract.consumed_amount = sum(contract.activity_ids.mapped("amount_to_consume"))


class Od19SalesContractActivity(models.Model):
    _name = "od19.sales.contract.activity"
    _description = "Sales Contract Activity"

    name = fields.Char(required=True)
    contract_id = fields.Many2one("od19.sales.contract", required=True, ondelete="cascade")
    amount_to_consume = fields.Float(required=True)

    @api.constrains("amount_to_consume", "contract_id")
    def _check_contract_limit(self):
        for activity in self:
            projected = activity.contract_id.consumed_amount + activity.amount_to_consume
            if (
                activity.contract_id.over_limit_policy == "block"
                and projected > activity.contract_id.limit_amount
            ):
                raise ValidationError("Contract activity exceeds blocked contract limit.")


class Od19SalesContractAmendment(models.Model):
    _name = "od19.sales.contract.amendment"
    _description = "Sales Contract Amendment"

    name = fields.Char(required=True)
    contract_id = fields.Many2one("od19.sales.contract", required=True, ondelete="cascade")
    added_limit_amount = fields.Float()
    note = fields.Text()
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run:

```bash
python odoo-bin -d test_w1_sales_contract --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_contract_core
```

Expected:

```text
Ran 1 test ... OK
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add custom_addons/od19_sales_contract_core
git commit -m "feat(sales): add master contract core"
```

### Task 4: สร้าง `od19_sales_billing_evidence`

**Files:**
- Create: `custom_addons/od19_sales_billing_evidence/__init__.py`
- Create: `custom_addons/od19_sales_billing_evidence/__manifest__.py`
- Create: `custom_addons/od19_sales_billing_evidence/models/__init__.py`
- Create: `custom_addons/od19_sales_billing_evidence/models/billing_evidence.py`
- Create: `custom_addons/od19_sales_billing_evidence/models/sale_order.py`
- Create: `custom_addons/od19_sales_billing_evidence/security/ir.model.access.csv`
- Create: `custom_addons/od19_sales_billing_evidence/views/billing_evidence_views.xml`
- Create: `custom_addons/od19_sales_billing_evidence/views/sale_order_views.xml`
- Create: `custom_addons/od19_sales_billing_evidence/tests/__init__.py`
- Create: `custom_addons/od19_sales_billing_evidence/tests/test_billing_readiness.py`

- [ ] **Step 1: เขียน failing test สำหรับ billing readiness**

สร้าง `custom_addons/od19_sales_billing_evidence/tests/test_billing_readiness.py`:

```python
from odoo.tests.common import TransactionCase


class TestBillingReadiness(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create({"name": "Contractor B"})
        self.owner = self.env["res.partner"].create({"name": "Owner B"})
        self.project = self.env["od19.sales.project"].create(
            {"name": "Convention Center", "project_owner_id": self.owner.id}
        )
        self.order = self.env["sale.order"].create(
            {
                "partner_id": self.contractor.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

    def test_delivery_evidence_marks_order_ready(self):
        evidence_type = self.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Note",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "DN-001",
                "sale_order_id": self.order.id,
                "evidence_type_id": evidence_type.id,
                "is_verified": True,
            }
        )
        self.order._compute_od19_billing_readiness_state()
        self.assertEqual(self.order.od19_billing_readiness_state, "ready")
```

- [ ] **Step 2: รัน test ให้ล้มก่อน**

Run:

```bash
python odoo-bin -d test_w1_sales_billing --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_billing_evidence
```

Expected:

```text
ImportError หรือ undefined model สำหรับ billing evidence
```

- [ ] **Step 3: สร้าง evidence types และ readiness state**

สร้าง `custom_addons/od19_sales_billing_evidence/models/billing_evidence.py`:

```python
from odoo import api, fields, models


class Od19BillingEvidenceType(models.Model):
    _name = "od19.billing.evidence.type"
    _description = "Billing Evidence Type"

    name = fields.Char(required=True)
    trigger_kind = fields.Selection(
        [("delivery", "Delivery"), ("service", "Service"), ("other", "Other")],
        required=True,
    )
    required_for_billing = fields.Boolean(default=True)


class Od19BillingEvidence(models.Model):
    _name = "od19.billing.evidence"
    _description = "Billing Evidence"

    name = fields.Char(required=True)
    sale_order_id = fields.Many2one("sale.order", ondelete="cascade")
    contract_activity_id = fields.Many2one("od19.sales.contract.activity", ondelete="cascade")
    evidence_type_id = fields.Many2one("od19.billing.evidence.type", required=True)
    is_verified = fields.Boolean(default=False)
    attachment_count = fields.Integer(default=0)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_billing_readiness_state = fields.Selection(
        [("draft", "Draft"), ("waiting", "Waiting Evidence"), ("ready", "Ready"), ("billed", "Billed")],
        compute="_compute_od19_billing_readiness_state",
        store=True,
    )
    od19_evidence_ids = fields.One2many("od19.billing.evidence", "sale_order_id")

    @api.depends("od19_evidence_ids.is_verified", "od19_evidence_ids.evidence_type_id.required_for_billing")
    def _compute_od19_billing_readiness_state(self):
        for order in self:
            required_verified = order.od19_evidence_ids.filtered(
                lambda rec: rec.evidence_type_id.required_for_billing and rec.is_verified
            )
            order.od19_billing_readiness_state = "ready" if required_verified else "waiting"
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run:

```bash
python odoo-bin -d test_w1_sales_billing --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_billing_evidence
```

Expected:

```text
Ran 1 test ... OK
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add custom_addons/od19_sales_billing_evidence
git commit -m "feat(sales): add billing evidence and readiness state"
```

### Task 5: สร้าง `od19_sales_reporting`

**Files:**
- Create: `custom_addons/od19_sales_reporting/__init__.py`
- Create: `custom_addons/od19_sales_reporting/__manifest__.py`
- Create: `custom_addons/od19_sales_reporting/models/__init__.py`
- Create: `custom_addons/od19_sales_reporting/models/report_sales_project_revenue.py`
- Create: `custom_addons/od19_sales_reporting/models/report_repeat_business.py`
- Create: `custom_addons/od19_sales_reporting/views/report_sales_project_revenue_views.xml`
- Create: `custom_addons/od19_sales_reporting/views/report_repeat_business_views.xml`
- Create: `custom_addons/od19_sales_reporting/security/ir.model.access.csv`
- Create: `custom_addons/od19_sales_reporting/tests/__init__.py`
- Create: `custom_addons/od19_sales_reporting/tests/test_sales_reporting.py`

- [ ] **Step 1: เขียน failing test สำหรับ repeat business และ project revenue**

สร้าง `custom_addons/od19_sales_reporting/tests/test_sales_reporting.py`:

```python
from odoo.tests.common import TransactionCase


class TestSalesReporting(TransactionCase):
    def test_project_revenue_view_contains_project(self):
        report_model = self.env["od19.sales.project.revenue.report"]
        self.assertIn("project_id", report_model._fields)

    def test_repeat_business_view_contains_owner_and_contractor(self):
        report_model = self.env["od19.sales.repeat.business.report"]
        self.assertIn("commercial_customer_id", report_model._fields)
        self.assertIn("project_owner_id", report_model._fields)
```

- [ ] **Step 2: รัน test ให้ล้มก่อน**

Run:

```bash
python odoo-bin -d test_w1_sales_reporting --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_reporting
```

Expected:

```text
KeyError หรือ model not found สำหรับ report models
```

- [ ] **Step 3: สร้าง SQL view reports**

สร้าง `custom_addons/od19_sales_reporting/models/report_sales_project_revenue.py`:

```python
from odoo import fields, models, tools


class ReportSalesProjectRevenue(models.Model):
    _name = "od19.sales.project.revenue.report"
    _description = "Sales Project Revenue Report"
    _auto = False

    project_id = fields.Many2one("od19.sales.project", readonly=True)
    commercial_customer_id = fields.Many2one("res.partner", readonly=True)
    project_owner_id = fields.Many2one("res.partner", readonly=True)
    order_count = fields.Integer(readonly=True)
    amount_untaxed = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(so.id) AS id,
                    so.od19_project_id AS project_id,
                    so.partner_id AS commercial_customer_id,
                    so.od19_project_owner_id AS project_owner_id,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(so.amount_untaxed), 0.0) AS amount_untaxed
                FROM sale_order so
                WHERE so.od19_project_id IS NOT NULL
                GROUP BY so.od19_project_id, so.partner_id, so.od19_project_owner_id
            )
            """
        )
```

สร้าง `custom_addons/od19_sales_reporting/models/report_repeat_business.py`:

```python
from odoo import fields, models, tools


class ReportSalesRepeatBusiness(models.Model):
    _name = "od19.sales.repeat.business.report"
    _description = "Sales Repeat Business Report"
    _auto = False

    commercial_customer_id = fields.Many2one("res.partner", readonly=True)
    project_owner_id = fields.Many2one("res.partner", readonly=True)
    project_count = fields.Integer(readonly=True)
    sale_order_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(so.id) AS id,
                    so.partner_id AS commercial_customer_id,
                    so.od19_project_owner_id AS project_owner_id,
                    COUNT(DISTINCT so.od19_project_id) AS project_count,
                    COUNT(*) AS sale_order_count
                FROM sale_order so
                WHERE so.od19_project_id IS NOT NULL
                GROUP BY so.partner_id, so.od19_project_owner_id
            )
            """
        )
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run:

```bash
python odoo-bin -d test_w1_sales_reporting --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_reporting
```

Expected:

```text
Ran 2 tests ... OK
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add custom_addons/od19_sales_reporting
git commit -m "feat(sales): add repeat-business and project revenue reports"
```

### Task 6: สร้าง `od19_sales_oca_bridge_workflow` และปิดงานแบบ end-to-end

**Files:**
- Create: `custom_addons/od19_sales_oca_bridge_workflow/__init__.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/models/__init__.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/tests/__init__.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`
- Modify: `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`

- [ ] **Step 1: เขียน failing integration test สำหรับ approved OCA bridge**

สร้าง `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`:

```python
from odoo.tests.common import TransactionCase


class TestOcaBridge(TransactionCase):
    def test_sale_order_has_approved_bridge_fields(self):
        order = self.env["sale.order"]
        self.assertIn("od19_exception_blocked", order._fields)
        self.assertIn("od19_delivery_state_snapshot", order._fields)
```

- [ ] **Step 2: รัน test ให้ล้มก่อน**

Run:

```bash
python odoo-bin -d test_w1_sales_bridge --test-enable -i sale,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_sales_oca_bridge_workflow
```

Expected:

```text
KeyError หรือ field not found บน sale.order
```

- [ ] **Step 3: สร้าง bridge addon ที่ผูกเฉพาะ approved baseline และเว้น deferred integration ไว้ก่อน**

สร้าง `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`:

```python
{
    "name": "OD19 Sales OCA Workflow Bridge",
    "version": "19.0.1.0.0",
    "depends": [
        "od19_sales_project_context",
        "od19_sales_contract_core",
        "od19_sales_billing_evidence",
        "od19_sales_reporting",
        "base_user_role",
        "base_revision",
        "sale_order_revision",
        "sale_delivery_state",
        "base_exception",
        "sale_exception",
        "sale_blanket_order",
    ],
    "data": ["views/sale_order_bridge_views.xml"],
    "installable": True,
    "license": "LGPL-3",
}
```

สร้าง `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`:

```python
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_exception_blocked = fields.Boolean(
        string="Blocked by OCA Exception",
        readonly=True,
    )
    od19_delivery_state_snapshot = fields.Char(
        string="Delivery State Snapshot",
        readonly=True,
    )
```

- [ ] **Step 4: อัปเดตสถานะสเปกเป็น approved baseline**

แก้ `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md` บรรทัดต้นให้เป็น:

```md
วันที่: 2026-10-04
สถานะ: User-approved Wave 1 baseline
```

เพิ่มหัวข้อ `Approval Traceability` ถัดจากอ้างอิงหลัก:

```md
## Approval Traceability

- Draft baseline was completed on 2026-10-04.
- User approved the Wave 1 Sales Contract Core scope on 2026-10-04 before implementation planning.
- This implementation plan is the first execution artifact derived from that approved baseline.
```

- [ ] **Step 5: รัน full install/test matrix**

Run:

```bash
python odoo-bin -d test_w1_sales_full --test-enable -i sale,mail,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket
python odoo-bin -d test_w1_sales_bridge --test-enable -i sale,mail,base_user_role,base_revision,sale_order_revision,sale_delivery_state,base_exception,sale_exception,sale_blanket_order,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket
git diff --check
```

Expected:

```text
ทั้ง core stack และ bridge stack ติดตั้งผ่าน
test ผ่าน
git diff --check ไม่พบ error
```

- [ ] **Step 6: Commit งานนี้**

```bash
git add custom_addons/od19_sales_oca_bridge_workflow docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md
git commit -m "feat(sales): bridge Wave 1 sales core with OCA workflow modules"
```

## Self-Review

- `Spec coverage`: แผนนี้ครอบคลุม one-time sales, contract-based sales, customer role model, project context, attachment evidence, billing readiness, repeat business, project revenue และ OCA-first integration
- `Placeholder scan`: ไม่มี `TODO`, `TBD`, หรือคำสั่งกว้าง ๆ ที่ไม่บอกไฟล์/คำสั่ง
- `Type consistency`: ใช้ prefix `od19_` เดียวกันใน field และ model ใหม่ทั้งหมด เพื่อลดความเสี่ยงชื่อชนกัน

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-implementation-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
