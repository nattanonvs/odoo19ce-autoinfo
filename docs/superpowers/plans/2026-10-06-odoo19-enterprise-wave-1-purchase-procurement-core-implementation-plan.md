# Wave 1 Purchase Procurement Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ส่งมอบ procurement core สำหรับ Wave 1 ที่รองรับทั้ง `PR -> PO` และ `Direct PO`, บังคับ `approval ทุกใบ`, ผูก `project/sale context` ที่ระดับ `PO line`, แยก `สินค้า/บริการ`, และมี `budget warning` แบบไม่บล็อก

**Architecture:** ใช้ Odoo standard modules `purchase`, `purchase_requisition`, และ `purchase_stock` เป็นฐาน แล้วเพิ่ม custom addon ใหม่ `od19_purchase_procurement_core` เพื่อขยาย `purchase.order`, `purchase.order.line`, และ `purchase.requisition` โดยไม่แก้ core ของ Odoo. โดเมน Purchase จะถือ intent และ approval semantics เอง ส่วน movement detail และ accounting detail จะส่งต่อไปยัง Inventory และ Accounting ตาม boundary ที่สเปกกำหนดไว้

**Tech Stack:** Odoo 19 CE, Python, XML, PostgreSQL, Odoo test framework, Git, Markdown

---

## File Structure

**Create**
- `custom_addons/od19_purchase_procurement_core/__init__.py`
- `custom_addons/od19_purchase_procurement_core/__manifest__.py`
- `custom_addons/od19_purchase_procurement_core/models/__init__.py`
- `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`
- `custom_addons/od19_purchase_procurement_core/models/purchase_order_line.py`
- `custom_addons/od19_purchase_procurement_core/models/purchase_requisition.py`
- `custom_addons/od19_purchase_procurement_core/tests/__init__.py`
- `custom_addons/od19_purchase_procurement_core/tests/test_procurement_line_semantics.py`
- `custom_addons/od19_purchase_procurement_core/tests/test_procurement_approval.py`
- `custom_addons/od19_purchase_procurement_core/tests/test_procurement_integration.py`
- `custom_addons/od19_purchase_procurement_core/views/purchase_order_views.xml`
- `custom_addons/od19_purchase_procurement_core/views/purchase_requisition_views.xml`

**Modify**
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

**Reuse Without Code Changes**
- `custom_addons/od19_contacts_partner_roles/`
- `custom_addons/od19_sales_project_context/`
- `addons/purchase/`
- `addons/purchase_requisition/`
- `addons/sale_purchase/`
- `addons/purchase_stock/`
- `docs/superpowers/specs/2026-10-06-odoo19-enterprise-wave-1-purchase-procurement-core-design.md`

## Precondition

ก่อนเริ่มทุก task จาก worktree นี้:

```bash
git submodule update --init --recursive
```

และใช้คำสั่ง Odoo จาก worktree ดังนี้:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux"
```

เหตุผลที่ต้อง override `--addons-path` คือ `odoo.conf` หลักยังชี้ไปที่ `custom_addons` ของ repo หลัก ไม่ใช่ของ worktree นี้

### Task 1: สร้าง addon `od19_purchase_procurement_core` และ line semantics ระดับ `PO line`

**Files:**
- Create: `custom_addons/od19_purchase_procurement_core/__init__.py`
- Create: `custom_addons/od19_purchase_procurement_core/__manifest__.py`
- Create: `custom_addons/od19_purchase_procurement_core/models/__init__.py`
- Create: `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`
- Create: `custom_addons/od19_purchase_procurement_core/models/purchase_order_line.py`
- Create: `custom_addons/od19_purchase_procurement_core/tests/__init__.py`
- Create: `custom_addons/od19_purchase_procurement_core/tests/test_procurement_line_semantics.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_purchase_procurement_core/tests/test_procurement_line_semantics.py`:

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProcurementLineSemantics(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Procurement Vendor", "company_type": "company"}
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Project Customer",
                "company_type": "company",
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Project Owner",
                "company_type": "company",
                "email": "owner@example.com",
                "od19_is_project_owner": True,
            }
        )
        self.project = self.env["od19.sales.project"].create(
            {
                "name": "Procurement Project",
                "project_owner_id": self.owner.id,
                "contractor_ids": [(6, 0, [self.customer.id])],
            }
        )
        self.sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Purchase Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        self.service = self.env["product.product"].create(
            {
                "name": "Purchase Service",
                "purchase_ok": True,
                "type": "service",
            }
        )

    def test_internal_line_does_not_require_project_context(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom": self.product.uom_po_id.id,
                "od19_procurement_purpose": "internal",
                "od19_item_kind": "product",
            }
        )
        self.assertEqual(line.od19_procurement_purpose, "internal")
        self.assertFalse(line.od19_project_id)

    def test_project_line_requires_project_reference(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        with self.assertRaises(ValidationError):
            self.env["purchase.order.line"].create(
                {
                    "order_id": order.id,
                    "name": self.product.display_name,
                    "product_id": self.product.id,
                    "product_qty": 1,
                    "price_unit": 100,
                    "date_planned": "2026-10-06 00:00:00",
                    "product_uom": self.product.uom_po_id.id,
                    "od19_procurement_purpose": "project",
                    "od19_item_kind": "product",
                }
            )

    def test_project_line_accepts_project_and_sale_reference(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.service.display_name,
                "product_id": self.service.id,
                "product_qty": 1,
                "price_unit": 500,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom": self.service.uom_po_id.id,
                "od19_procurement_purpose": "project",
                "od19_item_kind": "service",
                "od19_project_id": self.project.id,
                "od19_sale_order_id": self.sale_order.id,
            }
        )
        self.assertEqual(line.od19_project_id, self.project)
        self.assertEqual(line.od19_sale_order_id, self.sale_order)
```

- [ ] **Step 2: Run test to verify it fails**

Use the file-based `--test-tags` selector below. This is the stable discovery path confirmed to run correctly in this worktree.

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_line --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_line_semantics.py
```

Expected:

```text
ModuleNotFoundError, unknown field errors, or import errors because the addon does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_purchase_procurement_core/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_purchase_procurement_core/__manifest__.py`:

```python
{
    "name": "OD19 Purchase Procurement Core",
    "version": "19.0.1.0.0",
    "depends": [
        "purchase",
        "purchase_requisition",
        "purchase_stock",
        "sale_purchase",
        "od19_contacts_partner_roles",
        "od19_sales_project_context",
    ],
    "data": [
        "views/purchase_order_views.xml",
        "views/purchase_requisition_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_purchase_procurement_core/models/__init__.py`:

```python
from . import purchase_order
from . import purchase_order_line
from . import purchase_requisition
```

Create `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`:

```python
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        compute="_compute_od19_entry_mode",
        store=True,
        readonly=False,
        precompute=True,
        required=True,
        tracking=True,
    )

    @api.depends("requisition_id")
    def _compute_od19_entry_mode(self):
        for order in self:
            if order.requisition_id:
                order.od19_entry_mode = "requisition"
            else:
                order.od19_entry_mode = "direct"
```

Create `custom_addons/od19_purchase_procurement_core/models/purchase_order_line.py`:

```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_procurement_purpose = fields.Selection(
        [
            ("internal", "Internal"),
            ("project", "Project / Sale-linked"),
        ],
        string="Procurement Purpose",
        default="internal",
        required=True,
    )
    od19_item_kind = fields.Selection(
        [
            ("product", "Product"),
            ("service", "Service"),
        ],
        string="Item Kind",
        compute="_compute_od19_item_kind",
        store=True,
        readonly=False,
        precompute=True,
    )
    od19_project_id = fields.Many2one("od19.sales.project", string="Project")

    @api.depends("product_id")
    def _compute_od19_item_kind(self):
        for line in self:
            if line.product_id.type == "service":
                line.od19_item_kind = "service"
            else:
                line.od19_item_kind = "product"

    @api.constrains("od19_procurement_purpose", "od19_project_id")
    def _check_project_reference(self):
        for line in self:
            if line.display_type:
                continue
            if line.od19_procurement_purpose == "project" and not line.od19_project_id:
                raise ValidationError(
                    "Project-linked procurement lines must reference a project."
                )
```

Create `custom_addons/od19_purchase_procurement_core/models/purchase_requisition.py`:

```python
from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="requisition",
        required=True,
        tracking=True,
    )
```

Create `custom_addons/od19_purchase_procurement_core/tests/__init__.py`:

```python
from . import test_procurement_line_semantics
```

Create `custom_addons/od19_purchase_procurement_core/views/purchase_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="purchase_order_form_od19_procurement_core" model="ir.ui.view">
        <field name="name">purchase.order.form.od19.procurement.core</field>
        <field name="model">purchase.order</field>
        <field name="inherit_id" ref="purchase.purchase_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='partner_id']" position="after">
                <field name="od19_entry_mode"/>
            </xpath>
            <xpath expr="//field[@name='order_line']/list/field[@name='product_qty']" position="after">
                <field name="od19_procurement_purpose"/>
                <field name="od19_item_kind" readonly="1"/>
                <field name="od19_project_id"/>
                <field name="sale_line_id"/>
                <field name="sale_order_id" optional="hide"/>
            </xpath>
        </field>
    </record>
</odoo>
```

Create `custom_addons/od19_purchase_procurement_core/views/purchase_requisition_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="purchase_requisition_form_od19_procurement_core" model="ir.ui.view">
        <field name="name">purchase.requisition.form.od19.procurement.core</field>
        <field name="model">purchase.requisition</field>
        <field name="inherit_id" ref="purchase_requisition.purchase_requisition_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='vendor_id']" position="after">
                <field name="od19_entry_mode"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Use the same file-based selector below for deterministic discovery in this worktree.

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_line --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_line_semantics.py
```

Expected:

```text
Ran 6 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_purchase_procurement_core
git commit -m "feat(purchase): add procurement line semantics"
```

### Task 2: บังคับ approval ทุกใบสำหรับ `purchase.requisition` และ `purchase.order`

**Files:**
- Modify: `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`
- Modify: `custom_addons/od19_purchase_procurement_core/models/purchase_requisition.py`
- Modify: `custom_addons/od19_purchase_procurement_core/tests/__init__.py`
- Create: `custom_addons/od19_purchase_procurement_core/tests/test_procurement_approval.py`
- Modify: `custom_addons/od19_purchase_procurement_core/views/purchase_order_views.xml`
- Modify: `custom_addons/od19_purchase_procurement_core/views/purchase_requisition_views.xml`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_purchase_procurement_core/tests/test_procurement_approval.py`:

```python
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestProcurementApproval(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Approved Vendor", "company_type": "company"}
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Approval Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )

    def _create_order(self):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "od19_entry_mode": "direct",
            }
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom": self.product.uom_po_id.id,
            }
        )
        return order

    def test_direct_po_requires_explicit_approval_before_confirm(self):
        order = self._create_order()
        with self.assertRaises(UserError):
            order.button_confirm()
        order.action_od19_submit_for_approval()
        order.action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.od19_approval_state, "approved")

    def test_requisition_requires_explicit_approval_before_confirm(self):
        requisition = self.env["purchase.requisition"].create(
            {
                "vendor_id": self.vendor.id,
                "requisition_type": "blanket_order",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 2,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": 50,
                        },
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            requisition.action_confirm()
        requisition.action_od19_submit_for_approval()
        requisition.action_od19_approve()
        requisition.action_confirm()
        self.assertEqual(requisition.od19_approval_state, "approved")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_approval --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_approval.py
```

Expected:

```text
AttributeError or assertion failures because approval fields and approval actions do not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`:

```python
from odoo import fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="direct",
        required=True,
        tracking=True,
    )
    od19_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
        ],
        string="Approval State",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    def action_od19_submit_for_approval(self):
        self.write({"od19_approval_state": "submitted"})

    def action_od19_approve(self):
        self.write({"od19_approval_state": "approved"})

    def button_confirm(self):
        for order in self:
            if order.od19_approval_state != "approved":
                raise UserError(_("Every purchase order must be approved before confirmation."))
        return super().button_confirm()
```

Update `custom_addons/od19_purchase_procurement_core/models/purchase_requisition.py`:

```python
from odoo import fields, models, _
from odoo.exceptions import UserError


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="requisition",
        required=True,
        tracking=True,
    )
    od19_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
        ],
        string="Approval State",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    def action_od19_submit_for_approval(self):
        self.write({"od19_approval_state": "submitted"})

    def action_od19_approve(self):
        self.write({"od19_approval_state": "approved"})

    def action_confirm(self):
        self.ensure_one()
        if self.od19_approval_state != "approved":
            raise UserError(_("Every purchase requisition must be approved before confirmation."))
        return super().action_confirm()
```

Update `custom_addons/od19_purchase_procurement_core/tests/__init__.py`:

```python
from . import test_procurement_line_semantics
from . import test_procurement_approval
```

Update `custom_addons/od19_purchase_procurement_core/views/purchase_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="purchase_order_form_od19_procurement_core" model="ir.ui.view">
        <field name="name">purchase.order.form.od19.procurement.core</field>
        <field name="model">purchase.order</field>
        <field name="inherit_id" ref="purchase.purchase_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='partner_id']" position="after">
                <field name="od19_entry_mode"/>
                <field name="od19_approval_state" readonly="1"/>
            </xpath>
            <xpath expr="//header" position="inside">
                <button name="action_od19_submit_for_approval"
                        type="object"
                        string="Submit for Approval"
                        invisible="od19_approval_state != 'draft'"/>
                <button name="action_od19_approve"
                        type="object"
                        string="Approve"
                        invisible="od19_approval_state != 'submitted'"/>
            </xpath>
            <xpath expr="//field[@name='order_line']/list/field[@name='product_qty']" position="after">
                <field name="od19_procurement_purpose"/>
                <field name="od19_item_kind"/>
                <field name="od19_project_id"/>
                <field name="od19_sale_order_id"/>
            </xpath>
        </field>
    </record>
</odoo>
```

Update `custom_addons/od19_purchase_procurement_core/views/purchase_requisition_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="purchase_requisition_form_od19_procurement_core" model="ir.ui.view">
        <field name="name">purchase.requisition.form.od19.procurement.core</field>
        <field name="model">purchase.requisition</field>
        <field name="inherit_id" ref="purchase_requisition.purchase_requisition_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='vendor_id']" position="after">
                <field name="od19_entry_mode"/>
                <field name="od19_approval_state" readonly="1"/>
            </xpath>
            <xpath expr="//header" position="inside">
                <button name="action_od19_submit_for_approval"
                        type="object"
                        string="Submit for Approval"
                        invisible="od19_approval_state != 'draft'"/>
                <button name="action_od19_approve"
                        type="object"
                        string="Approve"
                        invisible="od19_approval_state != 'submitted'"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_approval --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_approval.py
```

Expected:

```text
Ran 5 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_purchase_procurement_core
git commit -m "feat(purchase): require approval for requisitions and orders"
```

### Task 3: แยก `สินค้า/บริการ` และเพิ่ม budget warning แบบไม่บล็อก

**Files:**
- Modify: `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`
- Modify: `custom_addons/od19_purchase_procurement_core/models/purchase_order_line.py`
- Modify: `custom_addons/od19_purchase_procurement_core/tests/__init__.py`
- Create: `custom_addons/od19_purchase_procurement_core/tests/test_procurement_integration.py`
- Modify: `custom_addons/od19_purchase_procurement_core/views/purchase_order_views.xml`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_purchase_procurement_core/tests/test_procurement_integration.py`:

```python
from odoo.tests.common import TransactionCase


class TestProcurementIntegration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Integrated Vendor", "company_type": "company"}
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Integrated Customer",
                "company_type": "company",
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Integrated Owner",
                "company_type": "company",
                "email": "owner@example.com",
                "od19_is_project_owner": True,
            }
        )
        self.project = self.env["od19.sales.project"].create(
            {
                "name": "Integrated Project",
                "project_owner_id": self.owner.id,
                "contractor_ids": [(6, 0, [self.customer.id])],
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Integrated Product",
                "purchase_ok": True,
                "type": "product",
            }
        )
        self.service = self.env["product.product"].create(
            {
                "name": "Integrated Service",
                "purchase_ok": True,
                "type": "service",
            }
        )

    def test_service_line_sets_service_acceptance_flag(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.service.display_name,
                "product_id": self.service.id,
                "product_qty": 1,
                "price_unit": 500,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom": self.service.uom_po_id.id,
                "od19_item_kind": "service",
                "od19_procurement_purpose": "project",
                "od19_project_id": self.project.id,
            }
        )
        self.assertTrue(line.od19_requires_service_acceptance)

    def test_project_line_without_budget_reference_raises_warning_flag(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 2,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom": self.product.uom_po_id.id,
                "od19_item_kind": "product",
                "od19_procurement_purpose": "project",
                "od19_project_id": self.project.id,
            }
        )
        self.assertTrue(line.od19_budget_warning)
        self.assertIn("budget reference", line.od19_budget_warning_message.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_integration --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_integration.py
```

Expected:

```text
Unknown field or assertion failures because service-acceptance and budget-warning fields do not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_purchase_procurement_core/models/purchase_order_line.py`:

```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_procurement_purpose = fields.Selection(
        [
            ("internal", "Internal"),
            ("project", "Project / Sale-linked"),
        ],
        string="Procurement Purpose",
        default="internal",
        required=True,
    )
    od19_item_kind = fields.Selection(
        [
            ("product", "Product"),
            ("service", "Service"),
        ],
        string="Item Kind",
        compute="_compute_od19_item_kind",
        store=True,
        readonly=False,
        precompute=True,
    )
    od19_project_id = fields.Many2one("od19.sales.project", string="Project")
    od19_sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    od19_budget_reference = fields.Char(string="Budget Reference")
    od19_budget_warning = fields.Boolean(
        string="Budget Warning",
        compute="_compute_od19_budget_warning",
        store=True,
    )
    od19_budget_warning_message = fields.Char(
        string="Budget Warning Message",
        compute="_compute_od19_budget_warning",
        store=True,
    )
    od19_requires_service_acceptance = fields.Boolean(
        string="Requires Service Acceptance",
        compute="_compute_od19_requires_service_acceptance",
        store=True,
    )

    @api.depends("product_id")
    def _compute_od19_item_kind(self):
        for line in self:
            if line.product_id.type == "service":
                line.od19_item_kind = "service"
            else:
                line.od19_item_kind = "product"

    @api.depends("od19_item_kind", "display_type")
    def _compute_od19_requires_service_acceptance(self):
        for line in self:
            line.od19_requires_service_acceptance = (
                not line.display_type and line.od19_item_kind == "service"
            )

    @api.depends("od19_procurement_purpose", "od19_budget_reference", "display_type")
    def _compute_od19_budget_warning(self):
        for line in self:
            if line.display_type:
                line.od19_budget_warning = False
                line.od19_budget_warning_message = False
            elif (
                line.od19_procurement_purpose == "project"
                and not line.od19_budget_reference
            ):
                line.od19_budget_warning = True
                line.od19_budget_warning_message = (
                    "Project-linked procurement lines should carry a budget reference."
                )
            else:
                line.od19_budget_warning = False
                line.od19_budget_warning_message = False

    @api.constrains("od19_procurement_purpose", "od19_project_id")
    def _check_project_reference(self):
        for line in self:
            if line.display_type:
                continue
            if line.od19_procurement_purpose == "project" and not line.od19_project_id:
                raise ValidationError(
                    "Project-linked procurement lines must reference a project."
                )
```

Update `custom_addons/od19_purchase_procurement_core/models/purchase_order.py`:

```python
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="direct",
        required=True,
        tracking=True,
    )
    od19_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
        ],
        string="Approval State",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    od19_budget_warning_count = fields.Integer(
        compute="_compute_od19_budget_warning_count",
        string="Budget Warning Count",
    )

    @api.depends("order_line.od19_budget_warning")
    def _compute_od19_budget_warning_count(self):
        for order in self:
            order.od19_budget_warning_count = len(
                order.order_line.filtered("od19_budget_warning")
            )

    def action_od19_submit_for_approval(self):
        self.write({"od19_approval_state": "submitted"})

    def action_od19_approve(self):
        self.write({"od19_approval_state": "approved"})

    def button_confirm(self):
        for order in self:
            if order.od19_approval_state != "approved":
                raise UserError(_("Every purchase order must be approved before confirmation."))
        return super().button_confirm()
```

Update `custom_addons/od19_purchase_procurement_core/tests/__init__.py`:

```python
from . import test_procurement_line_semantics
from . import test_procurement_approval
from . import test_procurement_integration
```

Update `custom_addons/od19_purchase_procurement_core/views/purchase_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="purchase_order_form_od19_procurement_core" model="ir.ui.view">
        <field name="name">purchase.order.form.od19.procurement.core</field>
        <field name="model">purchase.order</field>
        <field name="inherit_id" ref="purchase.purchase_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='partner_id']" position="after">
                <field name="od19_entry_mode"/>
                <field name="od19_approval_state" readonly="1"/>
                <field name="od19_budget_warning_count" readonly="1"/>
            </xpath>
            <xpath expr="//header" position="inside">
                <button name="action_od19_submit_for_approval"
                        type="object"
                        string="Submit for Approval"
                        invisible="od19_approval_state != 'draft'"/>
                <button name="action_od19_approve"
                        type="object"
                        string="Approve"
                        invisible="od19_approval_state != 'submitted'"/>
            </xpath>
            <xpath expr="//field[@name='order_line']/list/field[@name='product_qty']" position="after">
                <field name="od19_procurement_purpose"/>
                <field name="od19_item_kind"/>
                <field name="od19_project_id"/>
                <field name="od19_sale_order_id"/>
                <field name="od19_budget_reference"/>
                <field name="od19_budget_warning" readonly="1"/>
                <field name="od19_requires_service_acceptance" readonly="1"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_integration --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_integration.py
```

Expected:

```text
Ran 7 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_purchase_procurement_core
git commit -m "feat(purchase): add receiving split and budget warnings"
```

### Task 4: ปิดงานด้วย integration matrix และอัปเดตสถานะ Wave 1

**Files:**
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`
- Test: `custom_addons/od19_purchase_procurement_core/tests/test_procurement_integration.py`

- [ ] **Step 1: Update Wave 1 control documents**

Update `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` row for Wave 1:

```markdown
| Wave 1 | Contacts; Sales; Purchase; Inventory; Accounting | W1-COMMERCIAL-CORE | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In discovery | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 complete; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Purchase baseline approved; current-state inventory evidence for inventory and accounting still required | Ready when Inventory and Accounting child specs are approved against the established Sales, Contacts, and Purchase baseline |
```

Update `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` row for Wave 1:

```markdown
| Wave 1 | W1-COMMERCIAL-CORE | Commercial and financial core | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In discovery | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 approved; Wave 1 Sales, Contacts, and Purchase baselines approved | Discovery evidence exists for sales, contacts, and purchase; inventory and accounting evidence still incomplete | Ready when the remaining Wave 1 child specs align with the approved Sales, Contacts, and Purchase baseline, reporting KPIs, and migration assumptions |
```

- [ ] **Step 2: Run focused purchase test matrix**

Use explicit file-based selectors so the matrix does not depend on module-level auto-discovery.

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_matrix --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_purchase_procurement_core --stop-after-init --test-tags /od19_purchase_procurement_core/tests/test_procurement_line_semantics.py,/od19_purchase_procurement_core/tests/test_procurement_approval.py,/od19_purchase_procurement_core/tests/test_procurement_integration.py
```

Expected:

```text
All od19_purchase_procurement_core tests pass and the addon installs with purchase, requisition, stock, contacts, and sales context modules
```

- [ ] **Step 3: Run wider Wave 1 compatibility suite**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-contacts-closeout\third_party\oca\server-ux" -d test_w1_purchase_full --test-enable -i purchase,purchase_requisition,purchase_stock,od19_contacts_partner_roles,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow,od19_purchase_procurement_core,base_user_role,base_revision,sale_order_revision,sale_delivery_state,base_exception,sale_exception,sale_blanket_order --stop-after-init
```

Expected:

```text
Purchase addon installs successfully with the existing Wave 1 Sales and Contacts stack and no regression failures appear in the targeted matrix
```

- [ ] **Step 4: Run diff hygiene check**

Run:

```bash
git diff --check
```

Expected:

```text
No whitespace or malformed diff errors
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_purchase_procurement_core docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
git commit -m "feat(purchase): add wave 1 procurement core"
```

## Self-Review

- `Spec coverage`: แผนครอบคลุม procurement core, entry documents, approval ทุกใบ, line-level project link, product/service split, budget warning, และ compatibility กับ Sales/Contacts
- `Placeholder scan`: ไม่มี `TODO`, `TBD`, หรือคำสั่งกว้าง ๆ ที่ไม่ระบุไฟล์, โค้ด, หรือคำสั่งรัน
- `Type consistency`: ใช้ชื่อ `od19_entry_mode`, `od19_approval_state`, `od19_procurement_purpose`, `od19_item_kind`, `od19_project_id`, `od19_sale_order_id`, `od19_budget_reference`, `od19_budget_warning`, และ `od19_requires_service_acceptance` คงที่ตลอดแผน

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-06-odoo19-enterprise-wave-1-purchase-procurement-core-implementation-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
