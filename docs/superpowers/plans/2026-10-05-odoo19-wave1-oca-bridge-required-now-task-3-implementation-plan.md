# Odoo 19 Wave 1 OCA Bridge Required-Now Task 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ขยาย `od19_sales_oca_bridge_workflow` ให้รองรับ required-now OCA baseline สำหรับ revision, exception, และ blanket order แบบ TDD โดยไม่ทำให้ deferred integrations เดิมสับสน

**Architecture:** เพิ่ม failing tests ก่อนเพื่อยืนยันสัญญาของ bridge fields ใหม่บน `sale.order` จากนั้นค่อยเพิ่ม hard dependencies เฉพาะ required-now modules และ implement fields/view แบบขั้นต่ำใน addon bridge เดียว โดยคง deferred fields เดิมไว้ได้แต่แยก presentation/help ให้ชัดว่าไม่ใช่ baseline รอบนี้

**Tech Stack:** Odoo 19 CE, Python, XML, Odoo test framework, OCA `server-ux`, `server-tools`, `sale-workflow`, `sale-blanket`

---

## File Structure

**Modify**
- `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`
- `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`

### Task 1: Red tests for required-now bridge fields

**Files:**
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`

- [ ] **Step 1: Write the failing tests**

```python
from odoo.tests.common import TransactionCase


class TestOcaBridge(TransactionCase):
    def test_sale_order_has_deferred_bridge_fields(self):
        order = self.env["sale.order"]
        self.assertIn("od19_requires_tier_validation", order._fields)
        self.assertIn("od19_invoice_plan_mode", order._fields)

    def test_sale_order_has_required_now_bridge_fields(self):
        order = self.env["sale.order"]
        self.assertIn("od19_enable_revision", order._fields)
        self.assertIn("od19_use_exception_rules", order._fields)
        self.assertIn("od19_use_blanket_order", order._fields)
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
c:\odoo-dev\odoo19\venv19\Scripts\python.exe odoo-bin -c c:\odoo-dev\odoo19\odoo.conf -d test_w1_oca_bridge_red --test-enable -i sale,mail,base_user_role,sale_delivery_state,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path="c:/odoo-dev/odoo19/addons,c:/odoo-dev/odoo19/odoo/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/custom_addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-backend,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-ux,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-tools,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-workflow,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-blanket" --test-tags od19_sales_oca_bridge_workflow
```

Expected: FAIL เพราะ fields required-now ยังไม่ถูกเพิ่ม

### Task 2: Minimal bridge implementation

**Files:**
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`

- [ ] **Step 1: Add hard dependencies for required-now modules**

```python
"base_revision",
"sale_order_revision",
"base_exception",
"sale_exception",
"sale_blanket_order",
```

- [ ] **Step 2: Add the minimal bridge fields**

```python
od19_enable_revision = fields.Boolean(
    string="Enable Revision Tracking",
    default=False,
)
od19_use_exception_rules = fields.Boolean(
    string="Use Exception Rules",
    default=False,
)
od19_use_blanket_order = fields.Boolean(
    string="Use Blanket Orders",
    default=False,
)
```

- [ ] **Step 3: Separate required-now vs deferred presentation in the form view**

```xml
<field name="od19_enable_revision"/>
<field name="od19_use_exception_rules"/>
<field name="od19_use_blanket_order"/>
<field name="od19_requires_tier_validation"/>
<field name="od19_invoice_plan_mode"/>
```

### Task 3: Green verification and commit

**Files:**
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`

- [ ] **Step 1: Run the targeted test to verify it passes**

Run:

```bash
c:\odoo-dev\odoo19\venv19\Scripts\python.exe odoo-bin -c c:\odoo-dev\odoo19\odoo.conf -d test_w1_oca_bridge_green --test-enable -i sale,mail,base_user_role,sale_delivery_state,base_revision,sale_order_revision,base_exception,sale_exception,sale_blanket_order,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path="c:/odoo-dev/odoo19/addons,c:/odoo-dev/odoo19/odoo/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/custom_addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-backend,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-ux,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-tools,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-workflow,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-blanket" --test-tags od19_sales_oca_bridge_workflow
```

Expected: PASS

- [ ] **Step 2: Check diff and commit**

```bash
git diff --check
git add custom_addons/od19_sales_oca_bridge_workflow docs/superpowers/plans/2026-10-05-odoo19-wave1-oca-bridge-required-now-task-3-implementation-plan.md
git commit -m "feat(sales): extend OCA bridge with revision exception and blanket support"
```
