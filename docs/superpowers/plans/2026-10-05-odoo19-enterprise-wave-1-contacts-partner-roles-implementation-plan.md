# Wave 1 Contacts Partner Roles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ส่งมอบ addon ฝั่ง Contacts ที่ยกระดับ `res.partner` ด้วย partner roles, validation ขั้นพื้นฐาน, search/view improvements และการเชื่อมต่อกับ `Wave 1 Sales` แบบไม่ทำให้ของเดิม regress

**Architecture:** ใช้แนวทาง `Odoo-native extension` โดยขยาย `res.partner` ผ่าน addon ใหม่ `od19_contacts_partner_roles` และคุม scope ให้อยู่ใน bounded context ของ Contacts เป็นหลัก จากนั้นจึง wire role semantics ไปยัง `od19_sales_project_context` ในระดับ view/domain เท่าที่จำเป็นเพื่อให้ทีมขายเลือก `Commercial Customer`, `Project Owner`, และ `Contractor` ได้สอดคล้องกับบทบาทจริงของคู่ค้า

**Tech Stack:** Odoo 19 CE, Python, XML, PostgreSQL, Odoo test framework, Git, Markdown

## Discovery Evidence

- Approved Wave 1 Contacts spec: `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
- Odoo 15 production reference source code: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
- Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Existing integration context: `custom_addons/od19_sales_project_context/`
- Partner baseline reference: Odoo standard `res.partner` model และ business role semantics จาก Wave 1 Sales

---

## File Structure

**Create**
- `custom_addons/od19_contacts_partner_roles/__init__.py`
- `custom_addons/od19_contacts_partner_roles/__manifest__.py`
- `custom_addons/od19_contacts_partner_roles/models/__init__.py`
- `custom_addons/od19_contacts_partner_roles/models/res_partner.py`
- `custom_addons/od19_contacts_partner_roles/views/res_partner_views.xml`
- `custom_addons/od19_contacts_partner_roles/tests/__init__.py`
- `custom_addons/od19_contacts_partner_roles/tests/test_partner_roles.py`
- `custom_addons/od19_contacts_partner_roles/tests/test_partner_views.py`
- `custom_addons/od19_contacts_partner_roles/tests/test_sales_compatibility.py`

**Modify**
- `custom_addons/od19_sales_project_context/__manifest__.py`
- `custom_addons/od19_sales_project_context/views/project_context_views.xml`
- `custom_addons/od19_sales_project_context/views/sale_order_views.xml`

**Reuse Without Code Changes**
- `custom_addons/od19_sales_project_context/models/project_context.py`
- `custom_addons/od19_sales_project_context/models/sale_order.py`
- `custom_addons/od19_sales_contract_core/`
- `custom_addons/od19_sales_reporting/`
- `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`

## Precondition

ก่อนเริ่มทุก task:

```bash
git submodule update --init --recursive
```

และใช้ `addons-path` นี้ในทุกคำสั่งทดสอบ:

```bash
addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket
```

### Task 1: สร้าง addon `od19_contacts_partner_roles` พร้อม role fields และ validation

**Files:**
- Create: `custom_addons/od19_contacts_partner_roles/__init__.py`
- Create: `custom_addons/od19_contacts_partner_roles/__manifest__.py`
- Create: `custom_addons/od19_contacts_partner_roles/models/__init__.py`
- Create: `custom_addons/od19_contacts_partner_roles/models/res_partner.py`
- Create: `custom_addons/od19_contacts_partner_roles/tests/__init__.py`
- Create: `custom_addons/od19_contacts_partner_roles/tests/test_partner_roles.py`

- [ ] **Step 1: Write the failing test**

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPartnerRoles(TransactionCase):
    def test_partner_can_hold_multiple_roles(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Mega Project Group",
                "company_type": "company",
                "email": "contact@mega.example.com",
                "od19_is_commercial_customer": True,
                "od19_is_project_owner": True,
            }
        )

        self.assertTrue(partner.od19_is_commercial_customer)
        self.assertTrue(partner.od19_is_project_owner)
        self.assertFalse(partner.od19_is_contractor)

    def test_commercial_customer_requires_contact_channel(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "No Channel Customer",
                    "company_type": "company",
                    "od19_is_commercial_customer": True,
                }
            )

    def test_project_owner_requires_company_entity(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Owner Person",
                    "company_type": "person",
                    "email": "owner.person@example.com",
                    "od19_is_project_owner": True,
                }
            )

    def test_contractor_requires_company_entity(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Contractor Person",
                    "company_type": "person",
                    "email": "contractor.person@example.com",
                    "od19_is_contractor": True,
                }
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python odoo-bin -d test_w1_contacts_roles --test-enable -i contacts,od19_contacts_partner_roles --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_contacts_partner_roles
```

Expected:

```text
ModuleNotFoundError, import error, or unknown field errors because the addon does not exist yet
```

- [ ] **Step 3: Write minimal implementation**

Create `custom_addons/od19_contacts_partner_roles/__init__.py`:

```python
from . import models
```

Create `custom_addons/od19_contacts_partner_roles/__manifest__.py`:

```python
{
    "name": "OD19 Contacts Partner Roles",
    "version": "19.0.1.0.0",
    "depends": ["contacts"],
    "data": ["views/res_partner_views.xml"],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_contacts_partner_roles/models/__init__.py`:

```python
from . import res_partner
```

Create `custom_addons/od19_contacts_partner_roles/models/res_partner.py`:

```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_is_commercial_customer = fields.Boolean(string="Commercial Customer")
    od19_is_project_owner = fields.Boolean(string="Project Owner")
    od19_is_contractor = fields.Boolean(string="Contractor")

    @api.constrains(
        "od19_is_commercial_customer",
        "od19_is_project_owner",
        "od19_is_contractor",
        "email",
        "phone",
        "mobile",
        "company_type",
    )
    def _check_od19_partner_roles(self):
        for partner in self:
            if partner.od19_is_commercial_customer and not (
                partner.email or partner.phone or partner.mobile
            ):
                raise ValidationError(
                    "Commercial customers must have at least one primary contact channel."
                )
            if partner.od19_is_project_owner and partner.company_type != "company":
                raise ValidationError("Project owners must be company partners.")
            if partner.od19_is_contractor and partner.company_type != "company":
                raise ValidationError("Contractors must be company partners.")
```

Create `custom_addons/od19_contacts_partner_roles/tests/__init__.py`:

```python
from . import test_partner_roles
```

Create `custom_addons/od19_contacts_partner_roles/tests/test_partner_roles.py`:

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPartnerRoles(TransactionCase):
    def test_partner_can_hold_multiple_roles(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Mega Project Group",
                "company_type": "company",
                "email": "contact@mega.example.com",
                "od19_is_commercial_customer": True,
                "od19_is_project_owner": True,
            }
        )

        self.assertTrue(partner.od19_is_commercial_customer)
        self.assertTrue(partner.od19_is_project_owner)
        self.assertFalse(partner.od19_is_contractor)

    def test_commercial_customer_requires_contact_channel(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "No Channel Customer",
                    "company_type": "company",
                    "od19_is_commercial_customer": True,
                }
            )

    def test_project_owner_requires_company_entity(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Owner Person",
                    "company_type": "person",
                    "email": "owner.person@example.com",
                    "od19_is_project_owner": True,
                }
            )

    def test_contractor_requires_company_entity(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Contractor Person",
                    "company_type": "person",
                    "email": "contractor.person@example.com",
                    "od19_is_contractor": True,
                }
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python odoo-bin -d test_w1_contacts_roles --test-enable -i contacts,od19_contacts_partner_roles --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_contacts_partner_roles
```

Expected:

```text
Ran 4 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_contacts_partner_roles
git commit -m "feat(contacts): add partner roles and validation"
```

### Task 2: เพิ่ม partner role views และ search filters

**Files:**
- Modify: `custom_addons/od19_contacts_partner_roles/__manifest__.py`
- Create: `custom_addons/od19_contacts_partner_roles/views/res_partner_views.xml`
- Modify: `custom_addons/od19_contacts_partner_roles/tests/__init__.py`
- Create: `custom_addons/od19_contacts_partner_roles/tests/test_partner_views.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_contacts_partner_roles/tests/test_partner_views.py`:

```python
from odoo.tests.common import TransactionCase


class TestPartnerViews(TransactionCase):
    def test_partner_form_contains_role_fields(self):
        form_view = self.env.ref("base.view_partner_form")
        self.assertIn("od19_is_commercial_customer", form_view.arch_db)
        self.assertIn("od19_is_project_owner", form_view.arch_db)
        self.assertIn("od19_is_contractor", form_view.arch_db)

    def test_partner_search_contains_role_filters(self):
        search_view = self.env.ref("base.view_res_partner_filter")
        self.assertIn("od19_is_commercial_customer", search_view.arch_db)
        self.assertIn("od19_is_project_owner", search_view.arch_db)
        self.assertIn("od19_is_contractor", search_view.arch_db)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python odoo-bin -d test_w1_contacts_views --test-enable -i contacts,od19_contacts_partner_roles --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_contacts_partner_roles
```

Expected:

```text
AssertionError because role fields and filters are not yet present in partner views
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_contacts_partner_roles/__manifest__.py`:

```python
{
    "name": "OD19 Contacts Partner Roles",
    "version": "19.0.1.0.0",
    "depends": ["contacts"],
    "data": ["views/res_partner_views.xml"],
    "installable": True,
    "license": "LGPL-3",
}
```

Create `custom_addons/od19_contacts_partner_roles/views/res_partner_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_partner_form_od19_roles" model="ir.ui.view">
        <field name="name">res.partner.form.od19.roles</field>
        <field name="model">res.partner</field>
        <field name="inherit_id" ref="base.view_partner_form"/>
        <field name="arch" type="xml">
            <xpath expr="//sheet/group" position="inside">
                <group string="OD19 Business Roles">
                    <field name="od19_is_commercial_customer"/>
                    <field name="od19_is_project_owner"/>
                    <field name="od19_is_contractor"/>
                </group>
            </xpath>
        </field>
    </record>

    <record id="view_partner_search_od19_roles" model="ir.ui.view">
        <field name="name">res.partner.search.od19.roles</field>
        <field name="model">res.partner</field>
        <field name="inherit_id" ref="base.view_res_partner_filter"/>
        <field name="arch" type="xml">
            <xpath expr="//search" position="inside">
                <separator/>
                <filter name="od19_commercial_customers"
                        string="Commercial Customers"
                        domain="[('od19_is_commercial_customer', '=', True)]"/>
                <filter name="od19_project_owners"
                        string="Project Owners"
                        domain="[('od19_is_project_owner', '=', True)]"/>
                <filter name="od19_contractors"
                        string="Contractors"
                        domain="[('od19_is_contractor', '=', True)]"/>
            </xpath>
        </field>
    </record>
</odoo>
```

Update `custom_addons/od19_contacts_partner_roles/tests/__init__.py`:

```python
from . import test_partner_roles
from . import test_partner_views
```

Create `custom_addons/od19_contacts_partner_roles/tests/test_partner_views.py`:

```python
from odoo.tests.common import TransactionCase


class TestPartnerViews(TransactionCase):
    def test_partner_form_contains_role_fields(self):
        form_view = self.env.ref("base.view_partner_form")
        self.assertIn("od19_is_commercial_customer", form_view.arch_db)
        self.assertIn("od19_is_project_owner", form_view.arch_db)
        self.assertIn("od19_is_contractor", form_view.arch_db)

    def test_partner_search_contains_role_filters(self):
        search_view = self.env.ref("base.view_res_partner_filter")
        self.assertIn("od19_is_commercial_customer", search_view.arch_db)
        self.assertIn("od19_is_project_owner", search_view.arch_db)
        self.assertIn("od19_is_contractor", search_view.arch_db)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python odoo-bin -d test_w1_contacts_views --test-enable -i contacts,od19_contacts_partner_roles --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_contacts_partner_roles
```

Expected:

```text
Ran 6 tests ... OK
```

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_contacts_partner_roles
git commit -m "feat(contacts): add partner role views and filters"
```

### Task 3: เชื่อม role semantics เข้ากับ `Wave 1 Sales` แบบไม่ regress

**Files:**
- Modify: `custom_addons/od19_sales_project_context/__manifest__.py`
- Modify: `custom_addons/od19_sales_project_context/views/project_context_views.xml`
- Modify: `custom_addons/od19_sales_project_context/views/sale_order_views.xml`
- Modify: `custom_addons/od19_contacts_partner_roles/tests/__init__.py`
- Create: `custom_addons/od19_contacts_partner_roles/tests/test_sales_compatibility.py`

- [ ] **Step 1: Write the failing test**

Create `custom_addons/od19_contacts_partner_roles/tests/test_sales_compatibility.py`:

```python
from odoo.tests.common import TransactionCase


class TestSalesCompatibility(TransactionCase):
    def test_project_context_views_reference_partner_roles(self):
        project_view = self.env.ref(
            "od19_sales_project_context.view_od19_sales_project_form"
        )
        order_view = self.env.ref(
            "od19_sales_project_context.view_sale_order_form_od19_project_context"
        )

        self.assertIn("od19_is_project_owner", project_view.arch_db)
        self.assertIn("od19_is_contractor", project_view.arch_db)
        self.assertIn("od19_is_project_owner", order_view.arch_db)

    def test_sales_flow_accepts_role_ready_partners(self):
        contractor = self.env["res.partner"].create(
            {
                "name": "Ready Contractor",
                "company_type": "company",
                "email": "contractor@example.com",
                "od19_is_commercial_customer": True,
                "od19_is_contractor": True,
            }
        )
        owner = self.env["res.partner"].create(
            {
                "name": "Ready Owner",
                "company_type": "company",
                "email": "owner@example.com",
                "od19_is_project_owner": True,
            }
        )

        project = self.env["od19.sales.project"].create(
            {
                "name": "Role-ready Project",
                "project_owner_id": owner.id,
                "contractor_ids": [(6, 0, [contractor.id])],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": contractor.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": owner.id,
            }
        )

        self.assertEqual(order.partner_id, contractor)
        self.assertEqual(order.od19_project_owner_id, owner)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python odoo-bin -d test_w1_contacts_sales --test-enable -i contacts,od19_contacts_partner_roles,od19_sales_project_context --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_contacts_partner_roles
```

Expected:

```text
AssertionError because Sales project context views do not yet constrain selection by partner roles
```

- [ ] **Step 3: Write minimal implementation**

Update `custom_addons/od19_sales_project_context/__manifest__.py`:

```python
{
    "name": "OD19 Sales Project Context",
    "version": "19.0.1.0.0",
    "depends": ["sale_management", "mail", "od19_contacts_partner_roles"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_context_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
```

Update `custom_addons/od19_sales_project_context/views/project_context_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_sales_project_form" model="ir.ui.view">
        <field name="name">od19.sales.project.form</field>
        <field name="model">od19.sales.project</field>
        <field name="arch" type="xml">
            <form string="Sales Project">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="project_owner_id" domain="[('od19_is_project_owner', '=', True)]"/>
                        <field name="contractor_ids"
                               widget="many2many_tags"
                               domain="[('od19_is_contractor', '=', True)]"/>
                        <field name="active"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>
    <record id="view_od19_sales_project_tree" model="ir.ui.view">
        <field name="name">od19.sales.project.tree</field>
        <field name="model">od19.sales.project</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="project_owner_id"/>
                <field name="active"/>
            </tree>
        </field>
    </record>
</odoo>
```

Update `custom_addons/od19_sales_project_context/views/sale_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_sale_order_form_od19_project_context" model="ir.ui.view">
        <field name="name">sale.order.form.od19.project.context</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='partner_id']" position="attributes">
                <attribute name="domain">[('od19_is_commercial_customer', '=', True)]</attribute>
            </xpath>
            <xpath expr="//field[@name='partner_id']" position="after">
                <field name="od19_sale_mode"/>
                <field name="od19_project_id"/>
                <field name="od19_project_owner_id" domain="[('od19_is_project_owner', '=', True)]"/>
            </xpath>
        </field>
    </record>
</odoo>
```

Update `custom_addons/od19_contacts_partner_roles/tests/__init__.py`:

```python
from . import test_partner_roles
from . import test_partner_views
from . import test_sales_compatibility
```

Create `custom_addons/od19_contacts_partner_roles/tests/test_sales_compatibility.py`:

```python
from odoo.tests.common import TransactionCase


class TestSalesCompatibility(TransactionCase):
    def test_project_context_views_reference_partner_roles(self):
        project_view = self.env.ref(
            "od19_sales_project_context.view_od19_sales_project_form"
        )
        order_view = self.env.ref(
            "od19_sales_project_context.view_sale_order_form_od19_project_context"
        )

        self.assertIn("od19_is_project_owner", project_view.arch_db)
        self.assertIn("od19_is_contractor", project_view.arch_db)
        self.assertIn("od19_is_project_owner", order_view.arch_db)

    def test_sales_flow_accepts_role_ready_partners(self):
        contractor = self.env["res.partner"].create(
            {
                "name": "Ready Contractor",
                "company_type": "company",
                "email": "contractor@example.com",
                "od19_is_commercial_customer": True,
                "od19_is_contractor": True,
            }
        )
        owner = self.env["res.partner"].create(
            {
                "name": "Ready Owner",
                "company_type": "company",
                "email": "owner@example.com",
                "od19_is_project_owner": True,
            }
        )

        project = self.env["od19.sales.project"].create(
            {
                "name": "Role-ready Project",
                "project_owner_id": owner.id,
                "contractor_ids": [(6, 0, [contractor.id])],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": contractor.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": owner.id,
            }
        )

        self.assertEqual(order.partner_id, contractor)
        self.assertEqual(order.od19_project_owner_id, owner)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python odoo-bin -d test_w1_contacts_sales --test-enable -i contacts,od19_contacts_partner_roles,od19_sales_project_context --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket --test-tags od19_contacts_partner_roles
```

Expected:

```text
Ran 8 tests ... OK
```

- [ ] **Step 5: Run wider compatibility suite**

Run:

```bash
python odoo-bin -d test_w1_contacts_full --test-enable -i contacts,od19_contacts_partner_roles,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow,base_user_role,base_revision,sale_order_revision,sale_delivery_state,base_exception,sale_exception,sale_blanket_order --stop-after-init --addons-path=addons,odoo/addons,custom_addons,third_party/oca/server-backend,third_party/oca/server-ux,third_party/oca/server-tools,third_party/oca/sale-workflow,third_party/oca/sale-blanket
git diff --check
```

Expected:

```text
Contacts addon installs successfully with the Wave 1 Sales stack
test suite passes
git diff --check returns no whitespace or malformed diff errors
```

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_contacts_partner_roles custom_addons/od19_sales_project_context
git commit -m "feat(contacts): align partner roles with Wave 1 sales context"
```

## Self-Review

- `Spec coverage`: แผนนี้ครอบคลุม canonical `res.partner`, partner roles, validation ขั้นพื้นฐาน, views/search filters และ compatibility กับ Wave 1 Sales
- `Placeholder scan`: ไม่มี `TODO`, `TBD`, หรือคำสั่งกว้าง ๆ ที่ไม่บอกไฟล์/คำสั่ง
- `Type consistency`: ใช้ชื่อ field `od19_is_commercial_customer`, `od19_is_project_owner`, และ `od19_is_contractor` คงที่ตลอดทั้งแผน

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-implementation-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
