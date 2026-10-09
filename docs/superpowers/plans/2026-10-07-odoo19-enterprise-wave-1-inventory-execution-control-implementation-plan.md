# Wave 1 Inventory Execution and Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ส่งมอบ inventory core สำหรับ Wave 1 ที่รองรับ `receipt`, `delivery`, `internal transfer`, `returns`, `lot/serial by need`, และ `full audit counting` โดยไม่แก้ Odoo core

**Architecture:** ใช้ Odoo standard modules `stock`, `purchase_stock`, และ `sale_stock` เป็นฐาน แล้วแยก custom work ออกเป็น 3 addon ตาม bounded context คือ `od19_inventory_execution_control` สำหรับ movement truth, `od19_inventory_audit_count` สำหรับ count governance, และ `od19_inventory_reporting` สำหรับ KPI/owner visibility. ทุก addon ต้อง install/uninstall ได้อย่างปลอดภัยและใช้ reference จาก Sales/Purchase เดิมโดยไม่ย้าย ownership ของ business rules ข้ามโดเมน

**Tech Stack:** Odoo 19 CE, Python, XML, PostgreSQL, Odoo test framework, Git, Markdown

## Discovery Evidence

- Approved child spec: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md`
- Odoo 15 production reference source code: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
- Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Current Odoo 19 standard modules used as implementation baseline: `addons/stock`, `addons/purchase_stock`, `addons/sale_stock`
- Existing Wave 1 custom baselines used for integration context: `custom_addons/od19_purchase_procurement_core`, `custom_addons/od19_sales_project_context`

---

## File Structure

**Create**
- `custom_addons/od19_inventory_execution_control/__init__.py`
- `custom_addons/od19_inventory_execution_control/__manifest__.py`
- `custom_addons/od19_inventory_execution_control/models/__init__.py`
- `custom_addons/od19_inventory_execution_control/models/stock_picking.py`
- `custom_addons/od19_inventory_execution_control/models/stock_move.py`
- `custom_addons/od19_inventory_execution_control/models/product_template.py`
- `custom_addons/od19_inventory_execution_control/views/stock_picking_views.xml`
- `custom_addons/od19_inventory_execution_control/views/product_views.xml`
- `custom_addons/od19_inventory_execution_control/tests/__init__.py`
- `custom_addons/od19_inventory_execution_control/tests/test_inventory_execution.py`
- `custom_addons/od19_inventory_execution_control/tests/test_inventory_returns_tracking.py`
- `custom_addons/od19_inventory_audit_count/__init__.py`
- `custom_addons/od19_inventory_audit_count/__manifest__.py`
- `custom_addons/od19_inventory_audit_count/models/__init__.py`
- `custom_addons/od19_inventory_audit_count/models/stock_count_session.py`
- `custom_addons/od19_inventory_audit_count/security/ir.model.access.csv`
- `custom_addons/od19_inventory_audit_count/views/stock_count_session_views.xml`
- `custom_addons/od19_inventory_audit_count/tests/__init__.py`
- `custom_addons/od19_inventory_audit_count/tests/test_inventory_audit_count.py`
- `custom_addons/od19_inventory_reporting/__init__.py`
- `custom_addons/od19_inventory_reporting/__manifest__.py`
- `custom_addons/od19_inventory_reporting/models/__init__.py`
- `custom_addons/od19_inventory_reporting/models/report_inventory_movement_backlog.py`
- `custom_addons/od19_inventory_reporting/models/report_inventory_accuracy.py`
- `custom_addons/od19_inventory_reporting/views/report_inventory_movement_backlog_views.xml`
- `custom_addons/od19_inventory_reporting/views/report_inventory_accuracy_views.xml`
- `custom_addons/od19_inventory_reporting/tests/__init__.py`
- `custom_addons/od19_inventory_reporting/tests/test_inventory_reporting.py`

**Modify**
- `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

**Reuse Without Code Changes**
- `custom_addons/od19_purchase_procurement_core/`
- `custom_addons/od19_sales_project_context/`
- `addons/stock/`
- `addons/purchase_stock/`
- `addons/sale_stock/`
- `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md`

## Precondition

ก่อนเริ่มทุก task ให้ยึด execution context เดียวตลอดรอบงาน โดยแนะนำ dedicated worktree `C:\odoo-dev\odoo19\.worktrees\wave1-inventory-execution-control`

```bash
git submodule update --init --recursive
```

ถ้ารันจาก root repo หลัง merge ให้ใช้คำสั่ง Odoo แบบนี้:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf
```

ถ้ารันใน worktree ให้ override `--addons-path` ให้ครอบคลุม `addons`, `odoo\addons`, `custom_addons`, และ OCA folders ของ worktree นั้นโดยตรง; ไม่ต้อง `git clone` OCA repos เพิ่มนอก submodule baseline ของ repo

### Task 1: สร้าง addon `od19_inventory_execution_control` สำหรับ movement truth

**Files:**
- Create: `custom_addons/od19_inventory_execution_control/__init__.py`
- Create: `custom_addons/od19_inventory_execution_control/__manifest__.py`
- Create: `custom_addons/od19_inventory_execution_control/models/__init__.py`
- Create: `custom_addons/od19_inventory_execution_control/models/stock_picking.py`
- Create: `custom_addons/od19_inventory_execution_control/models/stock_move.py`
- Create: `custom_addons/od19_inventory_execution_control/tests/__init__.py`
- Create: `custom_addons/od19_inventory_execution_control/tests/test_inventory_execution.py`
- Create: `custom_addons/od19_inventory_execution_control/views/stock_picking_views.xml`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_inventory_execution_control/tests/test_inventory_execution.py`:

```python
from odoo.tests.common import TransactionCase


class TestInventoryExecution(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create({"name": "Receipt Vendor", "company_type": "company"})
        self.customer = self.env["res.partner"].create({"name": "Delivery Customer", "company_type": "company"})
        self.product = self.env["product.product"].create(
            {"name": "Tracked Product", "type": "consu", "is_storable": True}
        )
        self.in_type = self.env.ref("stock.picking_type_in")
        self.out_type = self.env.ref("stock.picking_type_out")
        self.internal_type = self.env.ref("stock.picking_type_internal")

    def test_receipt_flow_class_is_computed_from_operation_type(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.in_type.id,
                "location_id": self.in_type.default_location_src_id.id,
                "location_dest_id": self.in_type.default_location_dest_id.id,
                "partner_id": self.vendor.id,
            }
        )
        self.assertEqual(picking.od19_flow_class, "receipt")
        self.assertEqual(picking.od19_execution_state, "waiting")

    def test_internal_transfer_flow_class_is_computed(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.internal_type.id,
                "location_id": self.internal_type.default_location_src_id.id,
                "location_dest_id": self.internal_type.default_location_dest_id.id,
            }
        )
        self.assertEqual(picking.od19_flow_class, "transfer")

    def test_done_picking_is_reported_as_done_execution_state(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.out_type.id,
                "location_id": self.out_type.default_location_src_id.id,
                "location_dest_id": self.out_type.default_location_dest_id.id,
                "partner_id": self.customer.id,
            }
        )
        picking.write({"state": "done"})
        self.assertEqual(picking.od19_execution_state, "done")

    def test_move_inherits_reference_document_from_origin(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.out_type.id,
                "location_id": self.out_type.default_location_src_id.id,
                "location_dest_id": self.out_type.default_location_dest_id.id,
                "origin": "SO0001",
                "partner_id": self.customer.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "picking_id": picking.id,
            }
        )
        self.assertEqual(move.od19_reference_document, "SO0001")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task1_20261007 --test-enable -i stock,purchase_stock,sale_stock,od19_purchase_procurement_core,od19_sales_project_context,od19_inventory_execution_control --stop-after-init --test-tags /od19_inventory_execution_control/tests/test_inventory_execution.py
```

Expected:

```text
ModuleNotFoundError, unknown field errors, or import errors because the addon does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_inventory_execution_control/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_inventory_execution_control/__manifest__.py`:

```python
{
    "name": "OD19 Inventory Execution Control",
    "version": "19.0.1.0.0",
    "depends": [
        "stock",
        "purchase_stock",
        "sale_stock",
        "od19_purchase_procurement_core",
        "od19_sales_project_context",
    ],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_inventory_execution_control/models/__init__.py`:

```python
from . import stock_move
from . import stock_picking
```

Create `custom_addons/od19_inventory_execution_control/models/stock_picking.py`:

```python
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    od19_flow_class = fields.Selection(
        [
            ("receipt", "Receipt"),
            ("delivery", "Delivery"),
            ("transfer", "Internal Transfer"),
            ("return", "Return"),
        ],
        string="Flow Class",
        compute="_compute_od19_flow_class",
        store=True,
    )
    od19_execution_state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("done", "Done"),
            ("exception", "Exception"),
        ],
        string="Execution State",
        compute="_compute_od19_execution_state",
        store=True,
    )

    @api.depends("picking_type_code", "return_id")
    def _compute_od19_flow_class(self):
        for picking in self:
            if picking.return_id:
                picking.od19_flow_class = "return"
            elif picking.picking_type_code == "incoming":
                picking.od19_flow_class = "receipt"
            elif picking.picking_type_code == "outgoing":
                picking.od19_flow_class = "delivery"
            else:
                picking.od19_flow_class = "transfer"

    @api.depends("state")
    def _compute_od19_execution_state(self):
        for picking in self:
            if picking.state == "done":
                picking.od19_execution_state = "done"
            elif picking.state in {"assigned"}:
                picking.od19_execution_state = "ready"
            elif picking.state in {"cancel"}:
                picking.od19_execution_state = "exception"
            else:
                picking.od19_execution_state = "waiting"
```

Create `custom_addons/od19_inventory_execution_control/models/stock_move.py`:

```python
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    od19_reference_document = fields.Char(
        string="Reference Document",
        compute="_compute_od19_reference_document",
        store=True,
    )

    @api.depends("origin", "picking_id.origin")
    def _compute_od19_reference_document(self):
        for move in self:
            move.od19_reference_document = move.origin or move.picking_id.origin or False
```

Create `custom_addons/od19_inventory_execution_control/tests/__init__.py`:

```python
from . import test_inventory_execution
```

Create `custom_addons/od19_inventory_execution_control/views/stock_picking_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="stock_picking_form_od19_execution" model="ir.ui.view">
        <field name="name">stock.picking.form.od19.execution</field>
        <field name="model">stock.picking</field>
        <field name="inherit_id" ref="stock.view_picking_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='origin']" position="after">
                <field name="od19_flow_class" readonly="1"/>
                <field name="od19_execution_state" readonly="1"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task1_20261007 --test-enable -i stock,purchase_stock,sale_stock,od19_purchase_procurement_core,od19_sales_project_context,od19_inventory_execution_control --stop-after-init --test-tags /od19_inventory_execution_control/tests/test_inventory_execution.py
```

Expected:

```text
Ran 4 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_inventory_execution_control
git commit -m "feat(inventory): add execution control baseline"
```

### Task 2: เพิ่ม `returns` และ `lot/serial by need` policy

**Files:**
- Modify: `custom_addons/od19_inventory_execution_control/models/__init__.py`
- Create: `custom_addons/od19_inventory_execution_control/models/product_template.py`
- Modify: `custom_addons/od19_inventory_execution_control/models/stock_picking.py`
- Create: `custom_addons/od19_inventory_execution_control/tests/test_inventory_returns_tracking.py`
- Modify: `custom_addons/od19_inventory_execution_control/tests/__init__.py`
- Create: `custom_addons/od19_inventory_execution_control/views/product_views.xml`
- Modify: `custom_addons/od19_inventory_execution_control/__manifest__.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_inventory_execution_control/tests/test_inventory_returns_tracking.py`:

```python
from odoo.tests.common import TransactionCase


class TestInventoryReturnsAndTracking(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product_tmpl = self.env["product.template"].create(
            {"name": "Need Tracking", "type": "consu", "is_storable": True}
        )
        self.in_type = self.env.ref("stock.picking_type_in")
        self.out_type = self.env.ref("stock.picking_type_out")

    def test_product_with_tracking_requires_reason(self):
        self.product_tmpl.write({"tracking": "lot"})
        self.assertTrue(self.product_tmpl.od19_tracking_required)
        self.assertFalse(self.product_tmpl.od19_tracking_required_reason)

    def test_return_picking_is_classified_as_return(self):
        original = self.env["stock.picking"].create(
            {
                "picking_type_id": self.out_type.id,
                "location_id": self.out_type.default_location_src_id.id,
                "location_dest_id": self.out_type.default_location_dest_id.id,
            }
        )
        returned = self.env["stock.picking"].create(
            {
                "picking_type_id": self.in_type.id,
                "location_id": self.in_type.default_location_src_id.id,
                "location_dest_id": self.in_type.default_location_dest_id.id,
                "return_id": original.id,
            }
        )
        self.assertEqual(returned.od19_flow_class, "return")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task2_20261007 --test-enable -i stock,purchase_stock,sale_stock,od19_purchase_procurement_core,od19_sales_project_context,od19_inventory_execution_control --stop-after-init --test-tags /od19_inventory_execution_control/tests/test_inventory_returns_tracking.py
```

Expected:

```text
Unknown field or assertion failures because tracking policy fields do not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_inventory_execution_control/models/__init__.py`:

```python
from . import product_template
from . import stock_move
from . import stock_picking
```

Create `custom_addons/od19_inventory_execution_control/models/product_template.py`:

```python
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    od19_tracking_required = fields.Boolean(
        string="Tracking Required",
        compute="_compute_od19_tracking_required",
        store=True,
    )
    od19_tracking_required_reason = fields.Char(string="Tracking Requirement Reason")

    @api.depends("tracking")
    def _compute_od19_tracking_required(self):
        for product in self:
            product.od19_tracking_required = product.tracking != "none"
```

Update `custom_addons/od19_inventory_execution_control/models/stock_picking.py`:

```python
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    od19_flow_class = fields.Selection(
        [
            ("receipt", "Receipt"),
            ("delivery", "Delivery"),
            ("transfer", "Internal Transfer"),
            ("return", "Return"),
        ],
        string="Flow Class",
        compute="_compute_od19_flow_class",
        store=True,
    )
    od19_execution_state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("done", "Done"),
            ("exception", "Exception"),
        ],
        string="Execution State",
        compute="_compute_od19_execution_state",
        store=True,
    )

    @api.depends("picking_type_code", "return_id")
    def _compute_od19_flow_class(self):
        for picking in self:
            if picking.return_id:
                picking.od19_flow_class = "return"
            elif picking.picking_type_code == "incoming":
                picking.od19_flow_class = "receipt"
            elif picking.picking_type_code == "outgoing":
                picking.od19_flow_class = "delivery"
            else:
                picking.od19_flow_class = "transfer"

    @api.depends("state")
    def _compute_od19_execution_state(self):
        for picking in self:
            if picking.state == "done":
                picking.od19_execution_state = "done"
            elif picking.state in {"assigned"}:
                picking.od19_execution_state = "ready"
            elif picking.state in {"cancel"}:
                picking.od19_execution_state = "exception"
            else:
                picking.od19_execution_state = "waiting"
```

Update `custom_addons/od19_inventory_execution_control/tests/__init__.py`:

```python
from . import test_inventory_execution
from . import test_inventory_returns_tracking
```

Update `custom_addons/od19_inventory_execution_control/__manifest__.py` `data` list:

```python
"data": [
    "views/product_views.xml",
    "views/stock_picking_views.xml",
],
```

Create `custom_addons/od19_inventory_execution_control/views/product_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="product_template_only_form_view_od19_tracking" model="ir.ui.view">
        <field name="name">product.template.only.form.od19.tracking</field>
        <field name="model">product.template</field>
        <field name="inherit_id" ref="stock.product_template_form_view_procurement_button"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='tracking']" position="after">
                <field name="od19_tracking_required" readonly="1"/>
                <field name="od19_tracking_required_reason"
                       invisible="not od19_tracking_required"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task2_20261007 --test-enable -i stock,purchase_stock,sale_stock,od19_purchase_procurement_core,od19_sales_project_context,od19_inventory_execution_control --stop-after-init --test-tags /od19_inventory_execution_control/tests/test_inventory_returns_tracking.py
```

Expected:

```text
Ran 2 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_inventory_execution_control
git commit -m "feat(inventory): add return classification and tracking policy"
```

### Task 3: สร้าง addon `od19_inventory_audit_count` สำหรับ `full audit counting`

**Files:**
- Create: `custom_addons/od19_inventory_audit_count/__init__.py`
- Create: `custom_addons/od19_inventory_audit_count/__manifest__.py`
- Create: `custom_addons/od19_inventory_audit_count/models/__init__.py`
- Create: `custom_addons/od19_inventory_audit_count/models/stock_count_session.py`
- Create: `custom_addons/od19_inventory_audit_count/security/ir.model.access.csv`
- Create: `custom_addons/od19_inventory_audit_count/views/stock_count_session_views.xml`
- Create: `custom_addons/od19_inventory_audit_count/tests/__init__.py`
- Create: `custom_addons/od19_inventory_audit_count/tests/test_inventory_audit_count.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_inventory_audit_count/tests/test_inventory_audit_count.py`:

```python
from odoo.tests.common import TransactionCase


class TestInventoryAuditCount(TransactionCase):
    def setUp(self):
        super().setUp()
        self.location = self.env.ref("stock.stock_location_stock")
        self.product = self.env["product.product"].create(
            {"name": "Counted Product", "type": "consu", "is_storable": True}
        )
        self.quant = self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
                "inventory_quantity": 10.0,
            }
        )

    def test_count_session_starts_in_scheduled_state(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Main Count", "location_id": self.location.id}
        )
        self.assertEqual(session.state, "scheduled")

    def test_session_line_computes_variance(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Variance Count", "location_id": self.location.id}
        )
        line = self.env["od19.stock.count.line"].create(
            {
                "session_id": session.id,
                "quant_id": self.quant.id,
                "counted_qty": 8.0,
            }
        )
        self.assertEqual(line.system_qty, 10.0)
        self.assertEqual(line.variance_qty, -2.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task3_20261007 --test-enable -i stock,od19_inventory_execution_control,od19_inventory_audit_count --stop-after-init --test-tags /od19_inventory_audit_count/tests/test_inventory_audit_count.py
```

Expected:

```text
ModuleNotFoundError or missing model errors because the audit addon does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_inventory_audit_count/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_inventory_audit_count/__manifest__.py`:

```python
{
    "name": "OD19 Inventory Audit Count",
    "version": "19.0.1.0.0",
    "depends": [
        "stock",
        "od19_inventory_execution_control",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_count_session_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_inventory_audit_count/models/__init__.py`:

```python
from . import stock_count_session
```

Create `custom_addons/od19_inventory_audit_count/models/stock_count_session.py`:

```python
from odoo import api, fields, models


class StockCountSession(models.Model):
    _name = "od19.stock.count.session"
    _description = "OD19 Stock Count Session"

    name = fields.Char(required=True)
    location_id = fields.Many2one("stock.location", required=True)
    state = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("counted", "Counted"),
            ("variance", "Variance Found"),
            ("adjusted", "Adjusted"),
            ("reviewed", "Reviewed"),
        ],
        default="scheduled",
        required=True,
    )
    line_ids = fields.One2many("od19.stock.count.line", "session_id")


class StockCountLine(models.Model):
    _name = "od19.stock.count.line"
    _description = "OD19 Stock Count Line"

    session_id = fields.Many2one("od19.stock.count.session", required=True, ondelete="cascade")
    quant_id = fields.Many2one("stock.quant", required=True)
    product_id = fields.Many2one(related="quant_id.product_id", store=True)
    system_qty = fields.Float(compute="_compute_system_qty", store=True)
    counted_qty = fields.Float(required=True)
    variance_qty = fields.Float(compute="_compute_variance_qty", store=True)

    @api.depends("quant_id.quantity")
    def _compute_system_qty(self):
        for line in self:
            line.system_qty = line.quant_id.quantity

    @api.depends("system_qty", "counted_qty")
    def _compute_variance_qty(self):
        for line in self:
            line.variance_qty = line.counted_qty - line.system_qty
```

Create `custom_addons/od19_inventory_audit_count/security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_stock_count_session_user,access.od19.stock.count.session.user,model_od19_stock_count_session,stock.group_stock_user,1,1,1,1
access_od19_stock_count_line_user,access.od19.stock.count.line.user,model_od19_stock_count_line,stock.group_stock_user,1,1,1,1
```

Create `custom_addons/od19_inventory_audit_count/views/stock_count_session_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_stock_count_session_tree" model="ir.ui.view">
        <field name="name">od19.stock.count.session.tree</field>
        <field name="model">od19.stock.count.session</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="location_id"/>
                <field name="state"/>
            </tree>
        </field>
    </record>
</odoo>
```

Create `custom_addons/od19_inventory_audit_count/tests/__init__.py`:

```python
from . import test_inventory_audit_count
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task3_20261007 --test-enable -i stock,od19_inventory_execution_control,od19_inventory_audit_count --stop-after-init --test-tags /od19_inventory_audit_count/tests/test_inventory_audit_count.py
```

Expected:

```text
Ran 2 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_inventory_audit_count
git commit -m "feat(inventory): add audit count session baseline"
```

### Task 4: สร้าง reporting baseline และอัปเดต control documents

**Files:**
- Create: `custom_addons/od19_inventory_reporting/__init__.py`
- Create: `custom_addons/od19_inventory_reporting/__manifest__.py`
- Create: `custom_addons/od19_inventory_reporting/models/__init__.py`
- Create: `custom_addons/od19_inventory_reporting/models/report_inventory_movement_backlog.py`
- Create: `custom_addons/od19_inventory_reporting/models/report_inventory_accuracy.py`
- Create: `custom_addons/od19_inventory_reporting/views/report_inventory_movement_backlog_views.xml`
- Create: `custom_addons/od19_inventory_reporting/views/report_inventory_accuracy_views.xml`
- Create: `custom_addons/od19_inventory_reporting/tests/__init__.py`
- Create: `custom_addons/od19_inventory_reporting/tests/test_inventory_reporting.py`
- Modify: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_inventory_reporting/tests/test_inventory_reporting.py`:

```python
from odoo.tests.common import TransactionCase


class TestInventoryReporting(TransactionCase):
    def test_movement_backlog_report_model_exists(self):
        model = self.env["od19.report.inventory.movement.backlog"]
        self.assertEqual(model._name, "od19.report.inventory.movement.backlog")

    def test_accuracy_report_model_exists(self):
        model = self.env["od19.report.inventory.accuracy"]
        self.assertEqual(model._name, "od19.report.inventory.accuracy")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_task4_20261007 --test-enable -i stock,od19_inventory_execution_control,od19_inventory_audit_count,od19_inventory_reporting --stop-after-init --test-tags /od19_inventory_reporting/tests/test_inventory_reporting.py
```

Expected:

```text
ModuleNotFoundError or missing model errors because the reporting addon does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_inventory_reporting/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_inventory_reporting/__manifest__.py`:

```python
{
    "name": "OD19 Inventory Reporting",
    "version": "19.0.1.0.0",
    "depends": [
        "stock",
        "od19_inventory_execution_control",
        "od19_inventory_audit_count",
    ],
    "data": [
        "views/report_inventory_movement_backlog_views.xml",
        "views/report_inventory_accuracy_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_inventory_reporting/models/__init__.py`:

```python
from . import report_inventory_accuracy
from . import report_inventory_movement_backlog
```

Create `custom_addons/od19_inventory_reporting/models/report_inventory_movement_backlog.py`:

```python
from odoo import fields, models


class ReportInventoryMovementBacklog(models.Model):
    _name = "od19.report.inventory.movement.backlog"
    _description = "OD19 Inventory Movement Backlog"

    picking_id = fields.Many2one("stock.picking")
    flow_class = fields.Selection(
        [
            ("receipt", "Receipt"),
            ("delivery", "Delivery"),
            ("transfer", "Internal Transfer"),
            ("return", "Return"),
        ]
    )
    execution_state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("done", "Done"),
            ("exception", "Exception"),
        ]
    )
```

Create `custom_addons/od19_inventory_reporting/models/report_inventory_accuracy.py`:

```python
from odoo import fields, models


class ReportInventoryAccuracy(models.Model):
    _name = "od19.report.inventory.accuracy"
    _description = "OD19 Inventory Accuracy"

    session_id = fields.Many2one("od19.stock.count.session")
    location_id = fields.Many2one("stock.location")
    state = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("counted", "Counted"),
            ("variance", "Variance Found"),
            ("adjusted", "Adjusted"),
            ("reviewed", "Reviewed"),
        ]
    )
```

Create `custom_addons/od19_inventory_reporting/views/report_inventory_movement_backlog_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_inventory_movement_backlog_tree" model="ir.ui.view">
        <field name="name">od19.report.inventory.movement.backlog.tree</field>
        <field name="model">od19.report.inventory.movement.backlog</field>
        <field name="arch" type="xml">
            <tree>
                <field name="picking_id"/>
                <field name="flow_class"/>
                <field name="execution_state"/>
            </tree>
        </field>
    </record>
</odoo>
```

Create `custom_addons/od19_inventory_reporting/views/report_inventory_accuracy_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_inventory_accuracy_tree" model="ir.ui.view">
        <field name="name">od19.report.inventory.accuracy.tree</field>
        <field name="model">od19.report.inventory.accuracy</field>
        <field name="arch" type="xml">
            <tree>
                <field name="session_id"/>
                <field name="location_id"/>
                <field name="state"/>
            </tree>
        </field>
    </record>
</odoo>
```

Create `custom_addons/od19_inventory_reporting/tests/__init__.py`:

```python
from . import test_inventory_reporting
```

Update `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md` header:

```markdown
## Control Metadata
- Child spec ID: W1-INVENTORY-EXECUTION-CONTROL
- Wave: Wave 1
- Status: Ready for plan
```

Update `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` Wave 1 readiness cue:

```markdown
| Wave 1 | Contacts; Sales; Purchase; Inventory; Accounting | W1-COMMERCIAL-CORE | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In discovery | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 complete; Wave 1 Sales baseline approved; Wave 1 Contacts baseline approved; Wave 1 Purchase baseline approved; Wave 1 Inventory baseline approved; accounting evidence still required | Ready when Accounting child spec is approved against the established Sales, Contacts, Purchase, and Inventory baseline |
```

Update `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` Wave 1 discovery evidence and gate note:

```markdown
| Wave 1 | W1-COMMERCIAL-CORE | Commercial and financial core | `docs/superpowers/specs/YYYY-MM-DD-odoo19-enterprise-wave-1-commercial-financial-core.md` | In discovery | Commercial domain lead | Technical supervisor | Business owner; Technical supervisor | Wave 0 approved; Wave 1 Sales, Contacts, Purchase, and Inventory baselines approved | Discovery evidence exists for sales, contacts, purchase, and inventory; accounting evidence still incomplete | Ready when the remaining Wave 1 child spec aligns with the approved operational baseline and migration assumptions |
```

- [ ] **Step 4: Run focused matrix and docs checks**

Run:

```bash
.\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d test_w1_inventory_matrix_20261007 --test-enable -i stock,purchase_stock,sale_stock,od19_purchase_procurement_core,od19_sales_project_context,od19_inventory_execution_control,od19_inventory_audit_count,od19_inventory_reporting --stop-after-init --test-tags /od19_inventory_execution_control/tests/test_inventory_execution.py,/od19_inventory_execution_control/tests/test_inventory_returns_tracking.py,/od19_inventory_audit_count/tests/test_inventory_audit_count.py,/od19_inventory_reporting/tests/test_inventory_reporting.py
git diff --check
```

Expected:

```text
0 failed, 0 error(s) in the focused inventory matrix
No whitespace or malformed diff errors
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_inventory_execution_control custom_addons/od19_inventory_audit_count custom_addons/od19_inventory_reporting docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
git commit -m "feat(inventory): add wave 1 execution and audit baseline"
```

## Self-Review

- `Spec coverage`: แผนครอบคลุม movement core, returns, lot/serial by need, audit counting, reporting baseline, control docs, และ boundary กับ Purchase/Sales/Accounting
- `Placeholder scan`: ไม่มี `TODO`, `TBD`, หรือ step ที่สั่งกว้างโดยไม่ระบุไฟล์ โค้ด หรือคำสั่งรัน
- `Type consistency`: ใช้ชื่อ `od19_flow_class`, `od19_execution_state`, `od19_reference_document`, `od19_tracking_required`, `od19_tracking_required_reason`, `od19.stock.count.session`, `od19.stock.count.line`, `system_qty`, และ `variance_qty` คงที่ตลอดแผน

## Execution Status

- Archived closeout: project history records the Wave 1 Inventory baseline as merged into `19.0`
- Reference snapshot: `project_memory.md` records merge commit `0e40ba5b2`, follow-up security file closeout `3f29289fa`, and 21 focused tests
- Treat unchecked boxes as historical planning artifacts unless Inventory scope is explicitly reopened

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-implementation-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
