# Wave 1 Accounting Operational Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ส่งมอบ accounting baseline สำหรับ Wave 1 ที่ปิดเส้นทาง `AR + AP + Payment + Reconciliation` ได้จริง โดยเชื่อมกับ Sales, Purchase, และ Inventory อย่างชัดเจนโดยไม่แก้ Odoo core

**Architecture:** ใช้ Odoo standard modules `account`, `sale_management`, `purchase`, และ `purchase_stock` เป็นฐาน แล้วเพิ่ม custom work ออกเป็น 2 addon คือ `od19_accounting_operational_closure` สำหรับ readiness handoff, invoice/bill closure, payment/reconciliation baseline, และ `od19_accounting_reporting` สำหรับ owner-facing closure KPIs. หลักสำคัญคือ Sales/Purchase/Inventory ยังเป็นเจ้าของต้นทางของธุรกรรม ส่วน Accounting เป็นเจ้าของ accounting truth, payment truth, และ reconciliation truth

**Tech Stack:** Odoo 19 CE, Python, XML, PostgreSQL, Odoo test framework, Git, Markdown

## Discovery Evidence

- Approved Wave 1 Accounting spec: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md`
- Odoo 15 production reference source code: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
- Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Current Odoo 19 standard modules used as implementation baseline: `addons/account`, `addons/sale`, `addons/purchase`, `addons/purchase_stock`
- Existing Wave 1 custom baselines used for integration context:
  - `custom_addons/od19_sales_billing_evidence`
  - `custom_addons/od19_purchase_procurement_core`
  - `custom_addons/od19_inventory_execution_control`
  - `custom_addons/od19_inventory_reporting`
  - `custom_addons/od19_sales_reporting`
  - `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md`

---

## File Structure

**Create**
- `custom_addons/od19_accounting_operational_closure/__init__.py`
- `custom_addons/od19_accounting_operational_closure/__manifest__.py`
- `custom_addons/od19_accounting_operational_closure/models/__init__.py`
- `custom_addons/od19_accounting_operational_closure/models/sale_order.py`
- `custom_addons/od19_accounting_operational_closure/models/purchase_order.py`
- `custom_addons/od19_accounting_operational_closure/models/purchase_order_line.py`
- `custom_addons/od19_accounting_operational_closure/models/account_move.py`
- `custom_addons/od19_accounting_operational_closure/views/sale_order_views.xml`
- `custom_addons/od19_accounting_operational_closure/views/purchase_order_views.xml`
- `custom_addons/od19_accounting_operational_closure/views/account_move_views.xml`
- `custom_addons/od19_accounting_operational_closure/tests/__init__.py`
- `custom_addons/od19_accounting_operational_closure/tests/test_ar_closure.py`
- `custom_addons/od19_accounting_operational_closure/tests/test_ap_closure.py`
- `custom_addons/od19_accounting_operational_closure/tests/test_cash_reconciliation.py`
- `custom_addons/od19_accounting_reporting/__init__.py`
- `custom_addons/od19_accounting_reporting/__manifest__.py`
- `custom_addons/od19_accounting_reporting/models/__init__.py`
- `custom_addons/od19_accounting_reporting/models/report_accounting_operational_closure.py`
- `custom_addons/od19_accounting_reporting/security/ir.model.access.csv`
- `custom_addons/od19_accounting_reporting/views/report_accounting_operational_closure_views.xml`
- `custom_addons/od19_accounting_reporting/tests/__init__.py`
- `custom_addons/od19_accounting_reporting/tests/test_accounting_reporting.py`

**Modify**
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

**Reuse Without Code Changes**
- `custom_addons/od19_sales_billing_evidence/`
- `custom_addons/od19_purchase_procurement_core/`
- `custom_addons/od19_inventory_execution_control/`
- `custom_addons/od19_inventory_reporting/`
- `custom_addons/od19_sales_reporting/`
- `addons/account/`
- `addons/sale/`
- `addons/purchase/`
- `addons/purchase_stock/`
- `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md`

## Precondition

ก่อนเริ่มทุก task ให้ทำงานใน dedicated worktree เช่น `C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure`

```bash
git submodule update --init --recursive
```

ใช้คำสั่ง Odoo จาก worktree โดย override `--addons-path` ให้ชี้เข้า worktree นั้นโดยตรง:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux"
```

เหตุผลที่ต้อง override `--addons-path` คือ `odoo.conf` หลักของ repo ชี้กลับไปยัง `custom_addons` ของ main workspace ไม่ใช่ของ worktree

### Task 1: สร้าง addon `od19_accounting_operational_closure` และ AR closure baseline

**Files:**
- Create: `custom_addons/od19_accounting_operational_closure/__init__.py`
- Create: `custom_addons/od19_accounting_operational_closure/__manifest__.py`
- Create: `custom_addons/od19_accounting_operational_closure/models/__init__.py`
- Create: `custom_addons/od19_accounting_operational_closure/models/sale_order.py`
- Create: `custom_addons/od19_accounting_operational_closure/views/sale_order_views.xml`
- Create: `custom_addons/od19_accounting_operational_closure/tests/__init__.py`
- Create: `custom_addons/od19_accounting_operational_closure/tests/test_ar_closure.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_accounting_operational_closure/tests/test_ar_closure.py`:

```python
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingARClosure(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "AR Closure Customer",
                "company_type": "company",
                "email": "ar@example.com",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "AR Closure Product",
                "type": "consu",
                "is_storable": True,
                "sale_ok": True,
                "list_price": 100.0,
            }
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Signed Delivery",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )

    def _create_ready_sale_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 100.0,
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "DEL-001",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
            }
        )
        order.action_confirm()
        order.invalidate_recordset(
            ["od19_billing_readiness_state", "od19_invoice_closure_state"]
        )
        return order

    def test_ready_sale_order_is_marked_ready_to_invoice(self):
        order = self._create_ready_sale_order()
        self.assertEqual(order.od19_billing_readiness_state, "ready")
        self.assertEqual(order.od19_invoice_closure_state, "ready_to_invoice")

    def test_sale_order_with_posted_invoice_is_marked_invoiced(self):
        order = self._create_ready_sale_order()
        invoice = order._create_invoices()
        invoice.action_post()
        order.invalidate_recordset(["od19_invoice_closure_state"])
        self.assertEqual(order.od19_invoice_closure_state, "invoiced")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_ar --test-enable -i account,sale_management,od19_sales_billing_evidence,od19_accounting_operational_closure --stop-after-init --test-tags /od19_accounting_operational_closure/tests/test_ar_closure.py
```

Expected:

```text
unknown field errors or module import errors because od19_accounting_operational_closure does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_accounting_operational_closure/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_accounting_operational_closure/__manifest__.py`:

```python
{
    "name": "OD19 Accounting Operational Closure",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "depends": [
        "account",
        "sale_management",
        "purchase",
        "purchase_stock",
        "od19_sales_billing_evidence",
        "od19_purchase_procurement_core",
        "od19_inventory_execution_control",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_accounting_operational_closure/models/__init__.py`:

```python
from . import sale_order
```

Create `custom_addons/od19_accounting_operational_closure/models/sale_order.py`:

```python
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_invoice_closure_state = fields.Selection(
        [
            ("waiting_readiness", "Waiting Readiness"),
            ("ready_to_invoice", "Ready to Invoice"),
            ("invoiced", "Invoiced"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Invoice Closure State",
        compute="_compute_od19_invoice_closure_state",
        store=True,
        readonly=True,
    )
    od19_customer_invoice_count = fields.Integer(
        string="Customer Invoice Count",
        compute="_compute_od19_customer_invoice_count",
    )

    @api.depends("invoice_ids")
    def _compute_od19_customer_invoice_count(self):
        for order in self:
            order.od19_customer_invoice_count = len(
                order.invoice_ids.filtered(
                    lambda move: move.move_type in ("out_invoice", "out_refund")
                    and move.state != "cancel"
                )
            )

    @api.depends(
        "od19_billing_readiness_state",
        "invoice_status",
        "invoice_ids.state",
        "invoice_ids.payment_state",
    )
    def _compute_od19_invoice_closure_state(self):
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda move: move.move_type in ("out_invoice", "out_refund")
                and move.state != "cancel"
            )
            if order.od19_billing_readiness_state != "ready":
                order.od19_invoice_closure_state = "waiting_readiness"
            elif not invoices:
                order.od19_invoice_closure_state = "ready_to_invoice"
            elif all(move.payment_state == "paid" for move in invoices):
                order.od19_invoice_closure_state = "paid"
            elif any(move.payment_state in ("partial", "in_payment", "paid") for move in invoices):
                order.od19_invoice_closure_state = "partially_paid"
            else:
                order.od19_invoice_closure_state = "invoiced"
```

Create `custom_addons/od19_accounting_operational_closure/views/sale_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_sale_order_form_od19_accounting_closure" model="ir.ui.view">
        <field name="name">sale.order.form.od19.accounting.closure</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='invoice_status']" position="after">
                <field name="od19_invoice_closure_state" readonly="1"/>
                <field name="od19_customer_invoice_count" readonly="1"/>
            </xpath>
        </field>
    </record>
</odoo>
```

Create `custom_addons/od19_accounting_operational_closure/tests/__init__.py`:

```python
from . import test_ar_closure
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_ar --test-enable -i account,sale_management,od19_sales_billing_evidence,od19_accounting_operational_closure --stop-after-init --test-tags /od19_accounting_operational_closure/tests/test_ar_closure.py
```

Expected:

```text
0 failed, 0 error(s)
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_accounting_operational_closure
git commit -m "feat(accounting): add ar operational closure baseline"
```

### Task 2: เพิ่ม AP closure baseline และ service acceptance handoff

**Files:**
- Modify: `custom_addons/od19_accounting_operational_closure/__manifest__.py`
- Modify: `custom_addons/od19_accounting_operational_closure/models/__init__.py`
- Modify: `custom_addons/od19_accounting_operational_closure/tests/__init__.py`
- Create: `custom_addons/od19_accounting_operational_closure/models/purchase_order.py`
- Create: `custom_addons/od19_accounting_operational_closure/models/purchase_order_line.py`
- Create: `custom_addons/od19_accounting_operational_closure/views/purchase_order_views.xml`
- Create: `custom_addons/od19_accounting_operational_closure/tests/test_ap_closure.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_accounting_operational_closure/tests/test_ap_closure.py`:

```python
from odoo.tests.common import TransactionCase


class TestAccountingAPClosure(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "AP Closure Vendor", "company_type": "company"}
        )
        self.service = self.env["product.product"].create(
            {
                "name": "Accepted Service",
                "type": "service",
                "purchase_ok": True,
            }
        )

    def _create_service_po(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.service.display_name,
                "product_id": self.service.id,
                "product_qty": 1.0,
                "price_unit": 500.0,
                "date_planned": "2026-10-07 00:00:00",
                "product_uom": self.service.uom_po_id.id,
            }
        )
        return order

    def test_service_po_waits_for_acceptance_before_vendor_bill(self):
        order = self._create_service_po()
        order.action_od19_submit_for_approval()
        order.with_user(self.env.ref("base.user_admin")).action_od19_approve()
        order.button_confirm()
        order.invalidate_recordset(["od19_vendor_bill_closure_state"])
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_service_acceptance")

    def test_service_po_moves_to_ready_to_bill_after_acceptance(self):
        order = self._create_service_po()
        order.action_od19_submit_for_approval()
        order.with_user(self.env.ref("base.user_admin")).action_od19_approve()
        order.button_confirm()
        service_line = order.order_line
        service_line.action_od19_accept_service()
        order.invalidate_recordset(["od19_vendor_bill_closure_state"])
        self.assertEqual(order.od19_vendor_bill_closure_state, "ready_to_bill")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_ap --test-enable -i account,purchase,purchase_stock,od19_purchase_procurement_core,od19_accounting_operational_closure --stop-after-init --test-tags /od19_accounting_operational_closure/tests/test_ap_closure.py
```

Expected:

```text
unknown field or missing method errors for od19_vendor_bill_closure_state and action_od19_accept_service
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_accounting_operational_closure/__manifest__.py`:

```python
"data": [
    "views/sale_order_views.xml",
    "views/purchase_order_views.xml",
],
```

Update `custom_addons/od19_accounting_operational_closure/models/__init__.py`:

```python
from . import purchase_order
from . import purchase_order_line
from . import sale_order
```

Update `custom_addons/od19_accounting_operational_closure/tests/__init__.py`:

```python
from . import test_ap_closure
from . import test_ar_closure
```

Create `custom_addons/od19_accounting_operational_closure/models/purchase_order_line.py`:

```python
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_service_acceptance_required = fields.Boolean(
        string="Service Acceptance Required",
        compute="_compute_od19_service_acceptance_required",
        store=True,
        readonly=True,
    )
    od19_service_accepted = fields.Boolean(
        string="Service Accepted",
        default=False,
    )

    @api.depends("product_id.type")
    def _compute_od19_service_acceptance_required(self):
        for line in self:
            line.od19_service_acceptance_required = line.product_id.type == "service"

    def action_od19_accept_service(self):
        self.filtered("od19_service_acceptance_required").write(
            {"od19_service_accepted": True}
        )
```

Create `custom_addons/od19_accounting_operational_closure/models/purchase_order.py`:

```python
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_vendor_bill_closure_state = fields.Selection(
        [
            ("waiting_commitment", "Waiting Commitment"),
            ("waiting_service_acceptance", "Waiting Service Acceptance"),
            ("ready_to_bill", "Ready to Bill"),
            ("billed", "Billed"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Vendor Bill Closure State",
        compute="_compute_od19_vendor_bill_closure_state",
        store=True,
        readonly=True,
    )

    @api.depends(
        "state",
        "invoice_status",
        "invoice_ids.state",
        "invoice_ids.payment_state",
        "order_line.od19_service_acceptance_required",
        "order_line.od19_service_accepted",
    )
    def _compute_od19_vendor_bill_closure_state(self):
        for order in self:
            bills = order.invoice_ids.filtered(
                lambda move: move.move_type in ("in_invoice", "in_refund")
                and move.state != "cancel"
            )
            waiting_service = order.order_line.filtered(
                lambda line: line.od19_service_acceptance_required
                and not line.od19_service_accepted
            )
            if order.state not in ("purchase", "done"):
                order.od19_vendor_bill_closure_state = "waiting_commitment"
            elif waiting_service:
                order.od19_vendor_bill_closure_state = "waiting_service_acceptance"
            elif not bills and order.invoice_status == "to invoice":
                order.od19_vendor_bill_closure_state = "ready_to_bill"
            elif bills and all(move.payment_state == "paid" for move in bills):
                order.od19_vendor_bill_closure_state = "paid"
            elif bills and any(move.payment_state in ("partial", "in_payment", "paid") for move in bills):
                order.od19_vendor_bill_closure_state = "partially_paid"
            elif bills:
                order.od19_vendor_bill_closure_state = "billed"
            else:
                order.od19_vendor_bill_closure_state = "ready_to_bill"
```

Create `custom_addons/od19_accounting_operational_closure/views/purchase_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_purchase_order_form_od19_accounting_closure" model="ir.ui.view">
        <field name="name">purchase.order.form.od19.accounting.closure</field>
        <field name="model">purchase.order</field>
        <field name="inherit_id" ref="purchase.purchase_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='invoice_status']" position="after">
                <field name="od19_vendor_bill_closure_state" readonly="1"/>
            </xpath>
            <xpath expr="//field[@name='order_line']/tree/field[@name='date_planned']" position="after">
                <field name="od19_service_acceptance_required" readonly="1" optional="show"/>
                <field name="od19_service_accepted" optional="show"/>
                <button
                    name="action_od19_accept_service"
                    type="object"
                    string="Accept Service"
                    invisible="not od19_service_acceptance_required or od19_service_accepted"
                />
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_ap --test-enable -i account,purchase,purchase_stock,od19_purchase_procurement_core,od19_accounting_operational_closure --stop-after-init --test-tags /od19_accounting_operational_closure/tests/test_ap_closure.py
```

Expected:

```text
0 failed, 0 error(s)
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_accounting_operational_closure
git commit -m "feat(accounting): add ap closure baseline"
```

### Task 3: เพิ่ม account move closure state และ payment/reconciliation baseline

**Files:**
- Modify: `custom_addons/od19_accounting_operational_closure/__manifest__.py`
- Modify: `custom_addons/od19_accounting_operational_closure/models/__init__.py`
- Modify: `custom_addons/od19_accounting_operational_closure/tests/__init__.py`
- Create: `custom_addons/od19_accounting_operational_closure/models/account_move.py`
- Create: `custom_addons/od19_accounting_operational_closure/views/account_move_views.xml`
- Create: `custom_addons/od19_accounting_operational_closure/tests/test_cash_reconciliation.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_accounting_operational_closure/tests/test_cash_reconciliation.py`:

```python
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingCashReconciliation(AccountTestInvoicingCommon):
    def test_customer_invoice_moves_from_posted_to_paid(self):
        invoice = self._create_invoice(
            move_type="out_invoice",
            partner=self.partner_a,
            post=True,
            invoice_line_ids=[
                (0, 0, {"product_id": self.product_a.id, "quantity": 1.0, "price_unit": 100.0}),
            ],
        )
        invoice.invalidate_recordset(["od19_operational_closure_state"])
        self.assertEqual(invoice.od19_operational_closure_state, "posted")

        self._register_payment(invoice, amount=invoice.amount_total)
        invoice.invalidate_recordset(["payment_state", "od19_operational_closure_state"])
        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.od19_operational_closure_state, "paid")

    def test_vendor_bill_can_be_partially_paid(self):
        bill = self._create_invoice(
            move_type="in_invoice",
            partner=self.partner_a,
            post=True,
            invoice_line_ids=[
                (0, 0, {"product_id": self.product_a.id, "quantity": 1.0, "price_unit": 200.0}),
            ],
        )
        self._register_payment(bill, amount=100.0)
        bill.invalidate_recordset(["payment_state", "od19_operational_closure_state"])
        self.assertEqual(bill.payment_state, "partial")
        self.assertEqual(bill.od19_operational_closure_state, "partially_paid")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_cash --test-enable -i account,od19_accounting_operational_closure --stop-after-init --test-tags /od19_accounting_operational_closure/tests/test_cash_reconciliation.py
```

Expected:

```text
unknown field errors for od19_operational_closure_state
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_accounting_operational_closure/__manifest__.py`:

```python
"data": [
    "views/sale_order_views.xml",
    "views/purchase_order_views.xml",
    "views/account_move_views.xml",
],
```

Update `custom_addons/od19_accounting_operational_closure/models/__init__.py`:

```python
from . import account_move
from . import purchase_order
from . import purchase_order_line
from . import sale_order
```

Update `custom_addons/od19_accounting_operational_closure/tests/__init__.py`:

```python
from . import test_ap_closure
from . import test_ar_closure
from . import test_cash_reconciliation
```

Create `custom_addons/od19_accounting_operational_closure/models/account_move.py`:

```python
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_operational_flow = fields.Selection(
        [
            ("customer", "Customer"),
            ("vendor", "Vendor"),
            ("other", "Other"),
        ],
        string="Operational Flow",
        compute="_compute_od19_operational_flow",
        store=True,
        readonly=True,
    )
    od19_operational_closure_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Operational Closure State",
        compute="_compute_od19_operational_closure_state",
        store=True,
        readonly=True,
    )
    od19_source_document = fields.Char(
        string="Source Document",
        compute="_compute_od19_source_document",
        store=True,
        readonly=True,
    )

    @api.depends("move_type")
    def _compute_od19_operational_flow(self):
        for move in self:
            if move.move_type in ("out_invoice", "out_refund"):
                move.od19_operational_flow = "customer"
            elif move.move_type in ("in_invoice", "in_refund"):
                move.od19_operational_flow = "vendor"
            else:
                move.od19_operational_flow = "other"

    @api.depends("invoice_origin", "ref", "name")
    def _compute_od19_source_document(self):
        for move in self:
            move.od19_source_document = move.invoice_origin or move.ref or move.name

    @api.depends("state", "payment_state")
    def _compute_od19_operational_closure_state(self):
        for move in self:
            if move.state != "posted":
                move.od19_operational_closure_state = "draft"
            elif move.payment_state == "paid":
                move.od19_operational_closure_state = "paid"
            elif move.payment_state in ("partial", "in_payment"):
                move.od19_operational_closure_state = "partially_paid"
            else:
                move.od19_operational_closure_state = "posted"
```

Create `custom_addons/od19_accounting_operational_closure/views/account_move_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_move_form_od19_operational_closure" model="ir.ui.view">
        <field name="name">account.move.form.od19.operational.closure</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='payment_state']" position="after">
                <field name="od19_operational_flow" readonly="1"/>
                <field name="od19_operational_closure_state" readonly="1"/>
                <field name="od19_source_document" readonly="1"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_cash --test-enable -i account,od19_accounting_operational_closure --stop-after-init --test-tags /od19_accounting_operational_closure/tests/test_cash_reconciliation.py
```

Expected:

```text
0 failed, 0 error(s)
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_accounting_operational_closure
git commit -m "feat(accounting): add payment and reconciliation baseline"
```

### Task 4: สร้าง reporting addon และอัปเดต control docs

**Files:**
- Create: `custom_addons/od19_accounting_reporting/__init__.py`
- Create: `custom_addons/od19_accounting_reporting/__manifest__.py`
- Create: `custom_addons/od19_accounting_reporting/models/__init__.py`
- Create: `custom_addons/od19_accounting_reporting/models/report_accounting_operational_closure.py`
- Create: `custom_addons/od19_accounting_reporting/security/ir.model.access.csv`
- Create: `custom_addons/od19_accounting_reporting/views/report_accounting_operational_closure_views.xml`
- Create: `custom_addons/od19_accounting_reporting/tests/__init__.py`
- Create: `custom_addons/od19_accounting_reporting/tests/test_accounting_reporting.py`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_accounting_reporting/tests/test_accounting_reporting.py`:

```python
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingReporting(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Reporting Customer", "company_type": "company"}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Reporting Product",
                "type": "consu",
                "is_storable": True,
                "sale_ok": True,
                "list_price": 120.0,
            }
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Proof",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )

    def test_report_contains_billable_backlog_and_open_items(self):
        order = self.env["sale.order"].create({"partner_id": self.customer.id})
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 120.0,
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "BILL-READY",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
            }
        )
        order.action_confirm()

        invoice = self._create_invoice(
            move_type="out_invoice",
            partner=self.customer,
            post=True,
            invoice_line_ids=[
                (0, 0, {"product_id": self.product.id, "quantity": 1.0, "price_unit": 120.0}),
            ],
        )
        bill = self._create_invoice(
            move_type="in_invoice",
            partner=self.partner_a,
            post=True,
            invoice_line_ids=[
                (0, 0, {"product_id": self.product_a.id, "quantity": 1.0, "price_unit": 80.0}),
            ],
        )

        report_rows = self.env["od19.report.accounting.operational.closure"].search([])
        metric_keys = set(report_rows.mapped("metric_key"))
        self.assertIn("billable_backlog", metric_keys)
        self.assertIn("open_receivable", metric_keys)
        self.assertIn("open_payable", metric_keys)
        self.assertTrue(invoice.amount_residual > 0)
        self.assertTrue(bill.amount_residual > 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_reporting --test-enable -i account,sale_management,purchase,od19_sales_billing_evidence,od19_accounting_operational_closure,od19_accounting_reporting --stop-after-init --test-tags /od19_accounting_reporting/tests/test_accounting_reporting.py
```

Expected:

```text
model not found or missing view/access errors because od19_accounting_reporting does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_accounting_reporting/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_accounting_reporting/__manifest__.py`:

```python
{
    "name": "OD19 Accounting Reporting",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "depends": [
        "account",
        "od19_accounting_operational_closure",
        "od19_sales_billing_evidence",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_accounting_operational_closure_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_accounting_reporting/models/__init__.py`:

```python
from . import report_accounting_operational_closure
```

Create `custom_addons/od19_accounting_reporting/models/report_accounting_operational_closure.py`:

```python
from odoo import fields, models, tools


class ReportAccountingOperationalClosure(models.Model):
    _name = "od19.report.accounting.operational.closure"
    _description = "OD19 Accounting Operational Closure"
    _auto = False
    _rec_name = "metric_label"

    metric_key = fields.Char(readonly=True)
    metric_label = fields.Char(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    record_count = fields.Integer(readonly=True)
    total_amount = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env["sale.order"].flush_model(
            ["od19_billing_readiness_state", "invoice_status", "company_id"]
        )
        self.env["account.move"].flush_model(
            ["move_type", "state", "payment_state", "amount_residual", "company_id"]
        )
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    metrics.metric_key,
                    metrics.metric_label,
                    metrics.company_id,
                    metrics.record_count,
                    metrics.total_amount
                FROM (
                    SELECT
                        'billable_backlog' AS metric_key,
                        'Billable Backlog' AS metric_label,
                        so.company_id,
                        COUNT(*)::int AS record_count,
                        0.0::float AS total_amount
                    FROM sale_order so
                    WHERE so.od19_billing_readiness_state = 'ready'
                      AND COALESCE(so.invoice_status, '') != 'invoiced'
                    GROUP BY so.company_id

                    UNION ALL

                    SELECT
                        'open_receivable' AS metric_key,
                        'Open Receivable' AS metric_label,
                        am.company_id,
                        COUNT(*)::int AS record_count,
                        COALESCE(SUM(am.amount_residual), 0.0)::float AS total_amount
                    FROM account_move am
                    WHERE am.move_type = 'out_invoice'
                      AND am.state = 'posted'
                      AND am.payment_state != 'paid'
                    GROUP BY am.company_id

                    UNION ALL

                    SELECT
                        'open_payable' AS metric_key,
                        'Open Payable' AS metric_label,
                        am.company_id,
                        COUNT(*)::int AS record_count,
                        COALESCE(SUM(am.amount_residual), 0.0)::float AS total_amount
                    FROM account_move am
                    WHERE am.move_type = 'in_invoice'
                      AND am.state = 'posted'
                      AND am.payment_state != 'paid'
                    GROUP BY am.company_id
                ) metrics
            )
            """
        )
```

Create `custom_addons/od19_accounting_reporting/security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_report_accounting_operational_closure_user,access.od19.report.accounting.operational.closure.user,model_od19_report_accounting_operational_closure,account.group_account_user,1,0,0,0
```

Create `custom_addons/od19_accounting_reporting/views/report_accounting_operational_closure_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_accounting_operational_closure_tree" model="ir.ui.view">
        <field name="name">od19.report.accounting.operational.closure.tree</field>
        <field name="model">od19.report.accounting.operational.closure</field>
        <field name="arch" type="xml">
            <tree create="0" edit="0" delete="0">
                <field name="metric_label"/>
                <field name="company_id"/>
                <field name="record_count"/>
                <field name="total_amount"/>
            </tree>
        </field>
    </record>

    <record id="action_od19_accounting_operational_closure_report" model="ir.actions.act_window">
        <field name="name">Accounting Operational Closure</field>
        <field name="res_model">od19.report.accounting.operational.closure</field>
        <field name="view_mode">tree</field>
    </record>
    
    <menuitem
        id="menu_od19_accounting_operational_closure_report"
        name="Accounting Operational Closure"
        parent="account.menu_finance_reports"
        action="action_od19_accounting_operational_closure_report"
        groups="account.group_account_user"
    />
</odoo>
```

Create `custom_addons/od19_accounting_reporting/tests/__init__.py`:

```python
from . import test_accounting_reporting
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\custom_addons,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-backend,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-tools,C:\odoo-dev\odoo19\.worktrees\wave1-accounting-operational-closure\third_party\oca\server-ux" -d test_w1_accounting_reporting --test-enable -i account,sale_management,purchase,purchase_stock,od19_sales_billing_evidence,od19_purchase_procurement_core,od19_inventory_execution_control,od19_accounting_operational_closure,od19_accounting_reporting --stop-after-init --test-tags /od19_accounting_reporting/tests/test_accounting_reporting.py,/od19_accounting_operational_closure/tests/test_ar_closure.py,/od19_accounting_operational_closure/tests/test_ap_closure.py,/od19_accounting_operational_closure/tests/test_cash_reconciliation.py
```

Expected:

```text
0 failed, 0 error(s)
```

- [ ] **Step 5: Run diff check and update control docs**

Run:

```bash
git diff --check
```

Update `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` so Wave 1 focus mentions that Accounting is now implemented as the operational-closure baseline and only final verification remains before Wave 1 closure.

Update `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` so the Accounting row changes from `In review` to `Approved and implemented` only if the code and focused matrix above pass in the worktree.

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_accounting_operational_closure custom_addons/od19_accounting_reporting docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
git commit -m "feat(accounting): add operational closure reporting baseline"
```

## Review Checklist

- `Spec coverage`: แผนครอบคลุม AR closure, AP closure, payment/reconciliation baseline, posting/tax baseline ในระดับจำเป็น, owner-facing reporting, และ boundary กับ Wave 2
- `No placeholders`: ไม่มี `TODO`, `TBD`, หรือ step ที่บอกเพียงกว้าง ๆ โดยไม่มีไฟล์/โค้ด/คำสั่งจริง
- `Type consistency`: ชื่อ field และ model ใช้ชุดเดียวกันตลอดแผน เช่น `od19_invoice_closure_state`, `od19_vendor_bill_closure_state`, และ `od19_operational_closure_state`
- `Boundary discipline`: แผนนี้ยังไม่รวม credit limits, overdue hold, cheque controls เชิงลึก, หรือ approval tiers ซึ่งเป็นขอบเขตของ Wave 2

## Execution Status

- Working closeout snapshot: project history records Task 1 (AR closure baseline) และ Task 2 (AP closure baseline) ว่าถูก implement และ review แล้วใน accounting worktree
- Remaining tasks in this plan stay open because there is no merged proof here yet for the full reporting/final verification closeout
- Preserve this document as the current accounting working baseline; do not reset it back to a blank unchecked state when carrying forward the remaining work

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
