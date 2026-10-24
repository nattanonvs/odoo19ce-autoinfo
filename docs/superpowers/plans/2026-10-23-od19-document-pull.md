# OD19 Document Pull (กลไกกลางดึงเอกสารต้นทาง) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโมดูล `od19_document_pull` ที่ให้ทุกฟอร์ม "เลือกเอกสารต้นทาง → ดึงรายการเข้าฟอร์ม → ยืนยันก่อนลบ" ทำงานด้วยกลไกเดียวกัน โดยลบตาม lineage และไม่แตะ Odoo core

**Architecture:** mixin กลาง (`od19.document.pull.mixin`) ประกาศสัญญา 5 เมธอด; ปลายทางแต่ละโมเดล (`account.move`, `purchase.order`) ประกาศ "source specs" (registry เป็น dict ต่อโมเดล) แล้ว implement การดึง/ลบของตัวเองโดยใช้ lineage ที่ core/OCA มีอยู่แล้ว (`purchase_line_id`, `sale_line_ids`, `purchase_request_lines`) + ฟิลด์ใหม่ 2 ตัว (`od19_source_move_line_id`, `od19_source_picking_id`) wizard 2 ตัว (pull / remove-with-confirm) ทำหน้าที่ UI + ยืนยันฝั่ง server

**Tech Stack:** Odoo 19 Enterprise, Python 3.12, OWL/QWeb XML views, OCA `purchase_request` (สำหรับ flow 4), Odoo `TransactionCase` tests

**Spec:** [2026-10-23-od19-document-pull-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-10-23-od19-document-pull-design.md)

**Decisions ที่ยืนยันแล้ว:** D1 flow 4 ใช้ปุ่มชุดเดียวกัน · D2 มีรายงาน GRNI ในเฟสนี้ · D3 label สองภาษาไทย/อังกฤษ · D4 คอลัมน์ "เอกสารต้นทาง" แบบ optional

---

## Test / Run Convention

- Python venv: `c:\odoo-dev\odoo19\venv19\Scripts\python.exe`
- Odoo binary: `c:\odoo-dev\odoo19\odoo-bin`
- Config: `c:\odoo-dev\odoo19\odoo.conf` · DB: `odoo19_pdev` (เดียวเท่านั้น)
- รันเทสต์ของโมดูลเดียว (ใช้ terminal แยกสำหรับงานนี้ ตามนิสัยการทำงานของโปรเจกต์):

```powershell
cd c:\odoo-dev\odoo19
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev `
  -u od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

- ติดตั้งโมดูลพร้อม dependency (ครั้งแรก):

```powershell
cd c:\odoo-dev\odoo19
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev `
  -i od19_document_pull --stop-after-init --no-http
```

**หมายเหตุ convention:** โฟลเดอร์ wizard ของโปรเจกต์ใช้ `wizards/` (ไม่ใช่ `wizard/`) จึงใช้ `wizards/` ในแผนนี้แม้สเปกเขียนว่า `wizard/`

---

## File Structure

**สร้างใหม่ — `custom_addons/od19_document_pull/`**

| ไฟล์ | หน้าที่ |
|---|---|
| `__manifest__.py` | metadata, depends, data list |
| `__init__.py` | import models, wizards |
| `models/__init__.py` | import ลำดับ model |
| `models/od19_document_pull_mixin.py` | ตรรกะกลาง + สัญญา 5 เมธอด + ปุ่ม action |
| `models/account_move.py` | implement flow 1,2,3 (+5,6 เฟส 2) |
| `models/account_move_line.py` | ฟิลด์ lineage ใหม่ + คอลัมน์ optional |
| `models/purchase_order.py` | implement flow 4 |
| `models/purchase_order_line.py` | คอลัมน์ optional "เอกสารต้นทาง" |
| `wizards/__init__.py` | import wizard ทั้งหมด |
| `wizards/od19_document_pull_wizard_line.py` | บรรทัดชั่วคราว (checkbox) |
| `wizards/od19_document_pull_wizard.py` | wizard ดึงรายการ (2 โหมด) |
| `wizards/od19_document_pull_remove_line.py` | preview บรรทัดที่จะถูกลบ |
| `wizards/od19_document_pull_remove_wizard.py` | ยืนยันก่อนลบ (state choose → confirm) |
| `wizards/od19_document_pull_wizard_views.xml` | form view ของ wizard ทั้ง 2 |
| `views/account_move_views.xml` | ปุ่ม + คอลัมน์ optional + label |
| `views/purchase_order_views.xml` | ปุ่ม + คอลัมน์ optional + label |
| `report/grni_report_views.xml` | list/pivot + action + menu รายงาน GRNI (เฟส 2) |
| `security/ir.model.access.csv` | สิทธิ์ 4 transient models |
| `tests/__init__.py` | import test modules |
| `tests/common.py` | helper สร้าง PO/SO/PR สำหรับเทสต์ |
| `tests/test_document_pull_purchase.py` | flow 1,2 + wizard |
| `tests/test_document_pull_sale.py` | flow 3 + กันซ้ำ + ลบ |
| `tests/test_document_pull_purchase_request.py` | flow 4 |
| `tests/test_document_pull_guards.py` | post แล้ว, partner ไม่ตรง, lineage หาย |
| `tests/test_document_pull_picking.py` | flow 5,6 (เฟส 2) |
| `tests/test_grni_report.py` | รายงาน GRNI (เฟส 2) |
| `i18n/th.po` | คำแปลไทย |

**แก้ไข — โมดูลเดิม**

| ไฟล์ | การแก้ |
|---|---|
| `custom_addons/od19_purchase_wizards/wizards/purchase_create_vendor_bill.py` | กรอง `qty_to_invoice > 0` (flow 5 ในตารางสเปก = wizard เดิมของเรา) |
| `custom_addons/od19_sale_wizards/models/account_move.py` | `action_open_get_sale_lines` เรียกกลไกกลาง + เพิ่มปุ่มลบ |
| `custom_addons/od19_sale_wizards/views/account_move_views.xml` | เปลี่ยนปุ่มเดิมให้ชี้ action ใหม่ |

---

## สัญญากลาง (Freeze ก่อนเริ่มทุก task)

ปลายทางแต่ละโมเดลต้อง implement:

```python
_od19_pull_editable_states()          -> tuple[str]           # เช่น ("draft",)
_od19_pull_source_specs()             -> list[dict]           # [{"model","label","domain"}]
_od19_pull_candidate_lines(source)    -> recordset           # บรรทัดที่ยังดึงได้
_od19_pull_line_info(source, line)    -> dict                # ข้อมูลบรรทัดให้ wizard
_od19_pull_apply(source, lines)       -> int                 # จำนวนบรรทัดที่สร้าง
_od19_pull_remove(source)             -> int                 # จำนวนบรรทัดที่ลบ
_od19_pull_bound_sources()            -> list[(record, int)] # เอกสารต้นทางที่ผูกอยู่
```

---

# เฟส 1 — กลไกกลาง + flow 1,2,3,4

## Task 1: Module scaffolding + ติดตั้งผ่าน

**Files:**
- Create: `custom_addons/od19_document_pull/__manifest__.py`
- Create: `custom_addons/od19_document_pull/__init__.py`
- Create: `custom_addons/od19_document_pull/models/__init__.py`
- Create: `custom_addons/od19_document_pull/wizards/__init__.py`
- Create: `custom_addons/od19_document_pull/security/ir.model.access.csv`
- Create: `custom_addons/od19_document_pull/tests/__init__.py`
- Test: `custom_addons/od19_document_pull/tests/test_module_install.py`

- [ ] **Step 1: เขียน failing test**

`tests/test_module_install.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestModuleInstall(TransactionCase):
    def test_mixin_is_registered(self):
        self.assertIn("od19.document.pull.mixin", self.env)

    def test_account_move_inherits_mixin(self):
        move = self.env["account.move"].new({})
        self.assertTrue(
            hasattr(move, "_od19_pull_source_specs"),
            "account.move must inherit od19.document.pull.mixin",
        )
```

`tests/__init__.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import test_module_install
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

```powershell
cd c:\odoo-dev\odoo19
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: FAIL — `Module od19_document_pull not found` (ยังไม่มีโฟลเดอร์)

- [ ] **Step 3: สร้าง manifest + โครงโฟลเดอร์**

`__manifest__.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Document Pull",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Accounting",
    "summary": "Central mechanism to pull source document lines into a "
    "destination form, with lineage-based removal and confirmation.",
    "license": "LGPL-3",
    "depends": [
        "account",
        "sale_management",
        "purchase",
        "purchase_stock",
        "purchase_request",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
        "wizards/od19_document_pull_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
```

`__init__.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import models
from . import wizards
```

`models/__init__.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import od19_document_pull_mixin
from . import account_move_line
from . import account_move
from . import purchase_order_line
from . import purchase_order
```

`wizards/__init__.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import od19_document_pull_wizard_line
from . import od19_document_pull_wizard
from . import od19_document_pull_remove_line
from . import od19_document_pull_remove_wizard
```

`security/ir.model.access.csv` (เขียนไว้ล่วงหน้าสำหรับ Task 5-6; ต้องมี model ก่อนจึงจะผ่าน — จึงใส่เฉพาะ mixin ที่ไม่มีตารางจริงไม่ได้):

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```

> ขั้นนี้ปล่อย CSV ว่างไว้ก่อน แล้วเติมใน Task 5 Step 3

สร้างไฟล์โมดูลขั้นต่ำที่ทำให้ import ผ่าน: `models/od19_document_pull_mixin.py` มีเฉพาะ class เปล่า + เมธอด `_od19_pull_source_specs` คืน `[]`; ไฟล์อื่นใน `models/` และ `wizards/` สร้างเป็นไฟล์เปล่า (มีเฉพาะ header comment) และยัง**ไม่**ใส่ใน `models/__init__.py` / `wizards/__init__.py` จนกว่าจะถึง task ของมัน — เพื่อไม่ให้ import fail

- [ ] **Step 4: รันเทสต์ให้เห็นว่าผ่าน**

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -i od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: PASS 2/2, ไม่มี warning ใน log

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_document_pull docs/superpowers/specs/2026-10-23-od19-document-pull-design.md docs/superpowers/plans/2026-10-23-od19-document-pull.md
git commit -m "feat(od19_document_pull): scaffold module with central pull mixin contract"
```

---

## Task 2: Mixin กลาง — เมธอดช่วยเหลือ + ปุ่ม action

**Files:**
- Modify: `custom_addons/od19_document_pull/models/od19_document_pull_mixin.py`
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_guards.py` (สร้าง, เพิ่มใน `tests/__init__.py`)

- [ ] **Step 1: เขียน failing test**

`tests/test_document_pull_guards.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullGuards(AccountTestInvoicingCommon):
    def test_editable_states_default_is_draft_only(self):
        move = self.env["account.move"].new({"move_type": "in_invoice"})
        self.assertEqual(move._od19_pull_editable_states(), ("draft",))

    def test_check_editable_raises_when_posted(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, post=True, amounts=[100.0]
        )
        with self.assertRaises(UserError):
            bill._od19_pull_check_editable()

    def test_open_pull_wizard_returns_act_window(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, invoice_date="2026-01-01"
        )
        action = bill._od19_pull_action_open_pull_wizard()
        self.assertEqual(action["res_model"], "od19.document.pull.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_res_id"], bill.id)
        self.assertEqual(action["context"]["default_res_model"], "account.move")

    def test_open_remove_wizard_returns_act_window(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, invoice_date="2026-01-01"
        )
        action = bill._od19_pull_action_open_remove_wizard()
        self.assertEqual(action["res_model"], "od19.document.pull.remove.wizard")
        self.assertEqual(action["context"]["default_res_id"], bill.id)
```

เพิ่ม `from . import test_document_pull_guards` ใน `tests/__init__.py`

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: FAIL — `AttributeError: 'account.move' object has no attribute '_od19_pull_editable_states'`

- [ ] **Step 3: implement mixin**

`models/od19_document_pull_mixin.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Central contract for the "pull source document lines" mechanism.

Destination documents (account.move, purchase.order, ...) inherit this
abstract model and implement the contract methods below. The shared
helpers here only deal with guards and with opening the wizards, so the
mechanism stays in one place (Lean & Maintainable).
"""

from odoo import _, models
from odoo.exceptions import UserError


class Od19DocumentPullMixin(models.AbstractModel):
    _name = "od19.document.pull.mixin"
    _description = "OD19 Document Pull Mixin"

    # ------------------------------------------------------------------
    # Contract — override in the destination model
    # ------------------------------------------------------------------

    def _od19_pull_editable_states(self):
        """Return the states in which the document may be modified."""
        return ("draft",)

    def _od19_pull_source_specs(self):
        """Return the allowed source documents for this record.

        Each spec is a dict:
            {
                "model": str,     # e.g. "purchase.order"
                "label": str,     # bilingual label shown in the wizard
                "domain": list,   # extra domain (already scoped to self)
            }
        """
        self.ensure_one()
        return []

    def _od19_pull_spec(self, model_name):
        """Return the spec for a given source model, or None."""
        self.ensure_one()
        for spec in self._od19_pull_source_specs():
            if spec["model"] == model_name:
                return spec
        return None

    def _od19_pull_candidate_lines(self, source):
        """Return the source lines that can still be pulled from source."""
        raise NotImplementedError

    def _od19_pull_line_info(self, source, line):
        """Return a dict feeding one od19.document.pull.wizard.line."""
        raise NotImplementedError

    def _od19_pull_apply(self, source, lines):
        """Create destination lines from lines of source. Return count."""
        raise NotImplementedError

    def _od19_pull_remove(self, source):
        """Delete destination lines linked to source. Return count removed."""
        raise NotImplementedError

    def _od19_pull_bound_sources(self):
        """Return [(source_record, line_count)] currently bound to self."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _od19_pull_check_editable(self):
        """Raise when the document may not be modified anymore."""
        self.ensure_one()
        if self.state not in self._od19_pull_editable_states():
            raise UserError(
                _(
                    "Source document lines can only be managed on a draft "
                    "document (current state: %(state)s).",
                    state=self.state,
                )
            )
        return True

    def _od19_pull_check_source(self, source):
        """Validate that source is one of the allowed source documents."""
        self.ensure_one()
        if not source:
            raise UserError(_("Please select a source document."))
        spec = self._od19_pull_spec(source._name)
        if not spec:
            raise UserError(
                _(
                    "%(source)s is not a valid source document for this "
                    "document.",
                    source=source._name,
                )
            )
        if (
            self.env[source._name].search_count(
                spec["domain"] + [("id", "=", source.id)]
            )
            == 0
        ):
            raise UserError(
                _(
                    "The selected source document does not match this "
                    "document (check the partner or the state)."
                )
            )
        return True

    def _od19_pull_action_open_pull_wizard(self):
        """Open the pull wizard for the current document."""
        self.ensure_one()
        self._od19_pull_check_editable()
        return {
            "name": _("Pull Lines from Source / ดึงรายการจากเอกสารต้นทาง"),
            "type": "ir.actions.act_window",
            "res_model": "od19.document.pull.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "active_model": self._name,
                "active_id": self.id,
                "active_ids": self.ids,
            },
        }

    def _od19_pull_action_open_remove_wizard(self):
        """Open the remove-with-confirmation wizard for the document."""
        self.ensure_one()
        self._od19_pull_check_editable()
        return {
            "name": _("Manage/Remove Source / จัดการ/ลบเอกสารต้นทาง"),
            "type": "ir.actions.act_window",
            "res_model": "od19.document.pull.remove.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "active_model": self._name,
                "active_id": self.id,
                "active_ids": self.ids,
            },
        }
```

- [ ] **Step 4: ให้ `account.move` สืบทอด mixin (ขั้นต่ำ)**

`models/account_move.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "od19.document.pull.mixin"]
```

- [ ] **Step 5: รันเทสต์ให้เห็นว่าผ่าน**

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: PASS ทั้งหมด (6/6) — หมายเหตุ `test_open_pull_wizard_returns_act_window` จะผ่านเพราะยังไม่ต้องมี model wizard จริง (แค่ dict)

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_document_pull/models custom_addons/od19_document_pull/tests
git commit -m "feat(od19_document_pull): add central mixin contract and wizard actions"
```

---

## Task 3: ฟิลด์ lineage ใหม่ + คอลัมน์ optional บนบรรทัด

**Files:**
- Create: `custom_addons/od19_document_pull/models/account_move_line.py`
- Create: `custom_addons/od19_document_pull/models/purchase_order_line.py`
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_guards.py` (เพิ่มเคส)

- [ ] **Step 1: เขียน failing test**

เพิ่มใน `TestDocumentPullGuards`:

```python
    def test_source_lineage_fields_exist(self):
        aml = self.env["account.move.line"]
        self.assertIn("od19_source_move_line_id", aml._fields)
        self.assertIn("od19_source_picking_id", aml._fields)
        self.assertEqual(
            aml._fields["od19_source_move_line_id"].comodel_name, "account.move.line"
        )
        self.assertEqual(
            aml._fields["od19_source_picking_id"].comodel_name, "stock.picking"
        )

    def test_source_label_field_on_account_move(self):
        self.assertIn("od19_pull_source_label", self.env["account.move"]._fields)

    def test_source_label_field_on_purchase_order(self):
        self.assertIn("od19_pull_source_label", self.env["purchase.order"]._fields)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — `assertIn("od19_source_move_line_id", ...)`

- [ ] **Step 3: implement ฟิลด์**

`models/account_move_line.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    od19_source_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Source Bill Line / บรรทัดใบวางบิลต้นทาง",
        ondelete="set null",
        copy=False,
        index="btree_not_null",
        help="Previous vendor bill line this line was pulled from (flow 2).",
    )
    od19_source_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Source Picking / ใบรับ-ส่งต้นทาง",
        ondelete="set null",
        copy=False,
        index="btree_not_null",
        help="Receipt / delivery the quantity of this line was pulled from "
        "(style B: bill by receipt / delivery).",
    )
```

`models/purchase_order_line.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_pull_source_label = fields.Char(
        string="Source Document / เอกสารต้นทาง",
        compute="_compute_od19_pull_source_label",
    )

    def _compute_od19_pull_source_label(self):
        for line in self:
            requests = line.purchase_request_lines.mapped("request_id")
            line.od19_pull_source_label = (
                ", ".join(sorted(set(requests.mapped("name")))) if requests else "-"
            )
```

- [ ] **Step 4: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_document_pull/models custom_addons/od19_document_pull/tests
git commit -m "feat(od19_document_pull): add lineage fields and source label columns"
```

---

## Task 4: Pull Wizard models

**Files:**
- Create: `custom_addons/od19_document_pull/wizards/od19_document_pull_wizard_line.py`
- Create: `custom_addons/od19_document_pull/wizards/od19_document_pull_wizard.py`
- Modify: `custom_addons/od19_document_pull/wizards/__init__.py`
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_wizard.py` (สร้าง, import ใน `tests/__init__.py`)

- [ ] **Step 1: เขียน failing test**

`tests/test_document_pull_wizard.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullWizard(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 5.0,
                            "price_unit": 100.0,
                            "name": cls.product.name,
                            "date_planned": "2026-01-01",
                        },
                    )
                ],
            }
        )
        cls.po.button_confirm()

    def _new_bill(self):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )

    def _open_wizard(self, bill, **overrides):
        vals = {
            "res_model": "account.move",
            "res_id": bill.id,
        }
        vals.update(overrides)
        return self.env["od19.document.pull.wizard"].create(vals)

    def test_source_ref_selection_lists_bill_sources(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        selection = self.env["od19.document.pull.wizard"]._selection_source_ref()
        self.assertIn(("purchase.order", "Purchase Order / ใบสั่งซื้อ"), selection)

    def test_onchange_source_ref_builds_lines_with_all_order_mode(self):
        bill = self._new_bill()
        wizard = self._open_wizard(
            bill, source_ref="purchase.order,%s" % self.po.id
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertEqual(line.res_model, "purchase.order.line")
        self.assertEqual(line.res_id, self.po.order_line.id)
        self.assertAlmostEqual(line.qty_to_invoice, 5.0)

    def test_action_pull_all_order_creates_lines(self):
        bill = self._new_bill()
        wizard = self._open_wizard(
            bill, source_ref="purchase.order,%s" % self.po.id
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, self.po.order_line)
        self.assertAlmostEqual(bill.invoice_line_ids.quantity, 5.0)
        self.assertAlmostEqual(bill.invoice_line_ids.price_unit, 100.0)

    def test_action_pull_select_mode_only_selected(self):
        self.po.order_line.copy({"product_qty": 2.0})
        bill = self._new_bill()
        wizard = self._open_wizard(
            bill, mode="select", source_ref="purchase.order,%s" % self.po.id
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 2)
        first = wizard.line_ids[0]
        wizard.line_ids.write({"selected": False})
        first.selected = True
        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.res_id if False else bill.invoice_line_ids.purchase_line_id, first._od19_get_source_line())

    def test_action_pull_raises_without_source(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        with self.assertRaises(UserError):
            wizard.action_pull()

    def test_action_pull_raises_when_nothing_selected(self):
        bill = self._new_bill()
        wizard = self._open_wizard(
            bill, mode="select", source_ref="purchase.order,%s" % self.po.id
        )
        wizard._onchange_source_ref()
        wizard.line_ids.write({"selected": False})
        with self.assertRaises(UserError):
            wizard.action_pull()

    def test_pull_twice_does_not_duplicate(self):
        bill = self._new_bill()
        source_ref = "purchase.order,%s" % self.po.id
        wizard = self._open_wizard(bill, source_ref=source_ref)
        wizard._onchange_source_ref()
        wizard.action_pull()
        wizard2 = self._open_wizard(bill, source_ref=source_ref)
        wizard2._onchange_source_ref()
        self.assertEqual(len(wizard2.line_ids), 0)
```

เพิ่ม `from . import test_document_pull_wizard` ใน `tests/__init__.py`

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — `KeyError` / model `od19.document.pull.wizard` ไม่มี

- [ ] **Step 3: implement wizard line**

`wizards/od19_document_pull_wizard_line.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class Od19DocumentPullWizardLine(models.TransientModel):
    _name = "od19.document.pull.wizard.line"
    _description = "OD19 Document Pull Wizard Line"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(
        string="Select / เลือก",
        default=True,
    )
    res_model = fields.Char(
        string="Source Model",
        readonly=True,
    )
    res_id = fields.Integer(
        string="Source Line ID",
        readonly=True,
    )
    source_name = fields.Char(
        string="Source / เอกสารต้นทาง",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product / สินค้า",
        readonly=True,
    )
    name = fields.Char(
        string="Description / รายละเอียด",
        readonly=True,
    )
    qty_to_pull = fields.Float(
        string="Billable Qty / จำนวนที่วางบิลได้",
        digits="Product Unit of Measure",
        readonly=True,
    )
    price_unit = fields.Float(
        string="Unit Price / ราคาต่อหน่วย",
        digits="Product Price",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM / หน่วย",
        readonly=True,
    )

    def _od19_get_source_line(self):
        """Return the source line record this row refers to."""
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)
```

- [ ] **Step 4: implement pull wizard**

`wizards/od19_document_pull_wizard.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Od19DocumentPullWizard(models.TransientModel):
    _name = "od19.document.pull.wizard"
    _description = "OD19 Document Pull Wizard"

    res_model = fields.Char(string="Destination Model", required=True)
    res_id = fields.Integer(string="Destination ID", required=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner / คู่ค้า",
        compute="_compute_partner_id",
    )
    source_ref = fields.Reference(
        selection="_selection_source_ref",
        string="Source Document / เอกสารต้นทาง",
    )
    mode = fields.Selection(
        selection=[
            ("all_order", "All lines (document order) / ทั้งหมดตามลำดับเอกสาร"),
            ("select", "Select lines / เลือกรายบรรทัด"),
        ],
        string="Pull Mode / โหมดการดึง",
        default="all_order",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="od19.document.pull.wizard.line",
        inverse_name="wizard_id",
        string="Lines / รายการ",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _od19_get_target(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.depends("res_model", "res_id")
    def _compute_partner_id(self):
        for wizard in self:
            wizard.partner_id = (
                wizard._od19_get_target().partner_id
                if wizard.res_model and wizard.res_id
                else False
            )

    @api.model
    def _selection_source_ref(self):
        """Expose the source models declared by the destination record."""
        if not self:
            return []
        wizard = self[:1]
        if not wizard.res_model or not wizard.res_id:
            return []
        target = wizard._od19_get_target().exists()
        if not target:
            return []
        return [
            (spec["model"], spec["label"]) for spec in target._od19_pull_source_specs()
        ]

    @api.onchange("source_ref")
    def _onchange_source_ref(self):
        """Rebuild the candidate rows whenever the source document changes."""
        self.line_ids = [(5, 0, 0)]
        self._od19_build_lines()

    def _od19_build_lines(self):
        self.ensure_one()
        if not self.source_ref or not self.res_model or not self.res_id:
            return
        target = self._od19_get_target()
        source = self.source_ref
        commands = []
        for line in target._od19_pull_candidate_lines(source):
            info = target._od19_pull_line_info(source, line)
            commands.append((0, 0, info))
        self.line_ids = commands

    def _od19_selected_source_lines(self):
        """Return the recordset of selected source lines."""
        self.ensure_one()
        selected = self.line_ids.filtered("selected")
        if not selected:
            return False
        models = set(selected.mapped("res_model"))
        if len(models) != 1:
            raise UserError(
                _("Selected lines must come from a single source document.")
            )
        model_name = models.pop()
        ids = selected.filtered(
            lambda l: l.res_model == model_name
        ).mapped("res_id")
        return self.env[model_name].browse(ids)

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_pull(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_("No destination document provided."))
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        source = self.source_ref
        target._od19_pull_check_source(source)

        if self.mode == "all_order":
            lines = target._od19_pull_candidate_lines(source)
        else:
            lines = self._od19_selected_source_lines()

        if not lines:
            raise UserError(_("There is no line to pull from this document."))

        count = target._od19_pull_apply(source, lines)
        if not count:
            raise UserError(_("There is no line to pull from this document."))
        return {"type": "ir.actions.act_window_close"}
```

- [ ] **Step 5: implement flow 1 (in_invoice ← PO) ใน `account.move`**

แก้ `models/account_move.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.fields import Command


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "od19.document.pull.mixin"]

    od19_pull_source_label = fields.Char(
        string="Source Documents / เอกสารต้นทาง",
        compute="_compute_od19_pull_source_label",
    )

    @api.depends(
        "invoice_line_ids.purchase_line_id",
        "invoice_line_ids.sale_line_ids",
        "invoice_line_ids.od19_source_move_line_id",
    )
    def _compute_od19_pull_source_label(self):
        for move in self:
            parts = [
                "%s (%s)" % (source.display_name, count)
                for source, count in move._od19_pull_bound_sources()
            ]
            move.od19_pull_source_label = ", ".join(parts) or False

    # ------------------------------------------------------------------
    # Contract
    # ------------------------------------------------------------------

    def _od19_pull_source_specs(self):
        self.ensure_one()
        if self.move_type == "in_invoice":
            return [
                {
                    "model": "purchase.order",
                    "label": _("Purchase Order / ใบสั่งซื้อ"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("state", "in", ("purchase", "done")),
                    ],
                },
                {
                    "model": "account.move",
                    "label": _("Previous Vendor Bill / ใบวางบิลเดิม"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("move_type", "=", "in_invoice"),
                        ("state", "=", "posted"),
                        ("id", "!=", self.id),
                    ],
                },
            ]
        if self.move_type == "out_invoice":
            return [
                {
                    "model": "sale.order",
                    "label": _("Sale Order / ใบสั่งขาย"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("state", "in", ("sale", "done")),
                    ],
                },
            ]
        return []

    def _od19_pull_candidate_lines(self, source):
        self.ensure_one()
        if source._name == "purchase.order":
            taken = self.invoice_line_ids.purchase_line_id.ids
            return source.order_line.filtered(
                lambda l: not l.display_type
                and l.qty_to_invoice > 0
                and l.id not in taken
            )
        if source._name == "sale.order":
            taken = self.invoice_line_ids.sale_line_ids.ids
            return source.order_line.filtered(
                lambda l: not l.display_type
                and l.qty_to_invoice > 0
                and l.id not in taken
            )
        if source._name == "account.move":
            taken = self.invoice_line_ids.od19_source_move_line_id.ids
            return source.invoice_line_ids.filtered(
                lambda l: l.display_type == "product" and l.id not in taken
            )
        return self.env["account.move.line"].browse()

    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        if source._name in ("purchase.order", "sale.order"):
            return {
                "res_model": line._name,
                "res_id": line.id,
                "source_name": source.display_name,
                "product_id": line.product_id.id,
                "name": line.name,
                "qty_to_pull": line.qty_to_invoice,
                "price_unit": line.price_unit,
                "product_uom_id": line.product_uom_id.id,
            }
        return {
            "res_model": line._name,
            "res_id": line.id,
            "source_name": source.display_name,
            "product_id": line.product_id.id,
            "name": line.name,
            "qty_to_pull": line.quantity,
            "price_unit": line.price_unit,
            "product_uom_id": line.product_uom_id.id,
        }

    def _od19_pull_next_sequence(self):
        self.ensure_one()
        return (max(self.invoice_line_ids.mapped("sequence") or [0])) + 10

    def _od19_pull_apply(self, source, lines):
        self.ensure_one()
        self._od19_pull_check_editable()
        commands = []
        sequence = self._od19_pull_next_sequence()
        if source._name == "purchase.order":
            for po_line in lines.sorted("sequence"):
                vals = po_line._prepare_account_move_line(self)
                vals["sequence"] = sequence
                commands.append(Command.create(vals))
                sequence += 10
        elif source._name == "sale.order":
            for so_line in lines.sorted("sequence"):
                vals = so_line._prepare_invoice_line()
                vals["move_id"] = self.id
                vals["sequence"] = sequence
                commands.append(Command.create(vals))
                sequence += 10
        elif source._name == "account.move":
            for src_line in lines.sorted("sequence"):
                vals = src_line.copy_data(
                    {
                        "move_id": self.id,
                        "od19_source_move_line_id": src_line.id,
                        "sequence": sequence,
                    }
                )[0]
                vals.pop("move_id", None)
                commands.append(Command.create(vals))
                sequence += 10
        else:
            return 0
        if not commands:
            return 0
        self.write({"invoice_line_ids": commands})
        return len(commands)

    def _od19_pull_remove(self, source):
        self.ensure_one()
        self._od19_pull_check_editable()
        if source._name == "purchase.order":
            lines = self.invoice_line_ids.filtered(
                lambda l: l.purchase_line_id.order_id == source
            )
        elif source._name == "sale.order":
            lines = self.invoice_line_ids.filtered(
                lambda l: source in l.sale_line_ids.order_id
            )
        elif source._name == "account.move":
            lines = self.invoice_line_ids.filtered(
                lambda l: l.od19_source_move_line_id.move_id == source
            )
        else:
            return 0
        count = len(lines)
        lines.unlink()
        return count

    def _od19_pull_bound_sources(self):
        self.ensure_one()
        found = []
        for source in self.invoice_line_ids.purchase_line_id.order_id:
            count = len(
                self.invoice_line_ids.filtered(
                    lambda l: l.purchase_line_id.order_id == source
                )
            )
            found.append((source, count))
        for source in self.invoice_line_ids.od19_source_move_line_id.move_id:
            count = len(
                self.invoice_line_ids.filtered(
                    lambda l: l.od19_source_move_line_id.move_id == source
                )
            )
            found.append((source, count))
        for source in self.invoice_line_ids.sale_line_ids.order_id:
            count = len(
                self.invoice_line_ids.filtered(
                    lambda l: source in l.sale_line_ids.order_id
                )
            )
            found.append((source, count))
        return found
```

> **หมายเหตุ `copy_data`:** `account.move.line.copy_data` จะคัดลอกฟิลด์ที่ `copy=True` เท่านั้น (ไม่รวม `move_id`) จึงต้องส่ง `move_id` ผ่าน override และลบ key ที่ซ้ำออกก่อน `Command.create` — ดูตัวอย่างจริงที่มีในโค้ดเบสต์แล้วที่ [document.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_document_sign/models/document.py)

- [ ] **Step 6: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS (Task 2 + Task 4 ทั้งหมด)

- [ ] **Step 7: Commit**

```bash
git add custom_addons/od19_document_pull
git commit -m "feat(od19_document_pull): pull wizard with all-order and select modes (flow 1,2,3)"
```

---

## Task 5: Remove Wizard (ยืนยันก่อนลบ)

**Files:**
- Create: `custom_addons/od19_document_pull/wizards/od19_document_pull_remove_line.py`
- Create: `custom_addons/od19_document_pull/wizards/od19_document_pull_remove_wizard.py`
- Modify: `custom_addons/od19_document_pull/security/ir.model.access.csv`
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_remove.py` (สร้าง, import)

- [ ] **Step 1: เขียน failing test**

`tests/test_document_pull_remove.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullRemove(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 5.0,
                            "price_unit": 100.0,
                            "name": cls.product.name,
                            "date_planned": "2026-01-01",
                        },
                    )
                ],
            }
        )
        cls.po.button_confirm()

    def _bill_with_pulled_line(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": bill.id,
                "source_ref": "purchase.order,%s" % self.po.id,
            }
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        return bill

    def test_bound_sources_lists_purchase_order(self):
        bill = self._bill_with_pulled_line()
        bound = bill._od19_pull_bound_sources()
        self.assertEqual(len(bound), 1)
        self.assertEqual(bound[0][0], self.po)
        self.assertEqual(bound[0][1], 1)
        self.assertEqual(bill.od19_pull_source_label, "%s (1)" % self.po.display_name)

    def test_remove_wizard_two_states_and_confirm_removes_lines(self):
        bill = self._bill_with_pulled_line()
        wizard = self.env["od19.document.pull.remove.wizard"].create(
            {"res_model": "account.move", "res_id": bill.id}
        )
        self.assertEqual(wizard.state, "choose")
        self.assertEqual(len(wizard.source_ids), 1)
        wizard.source_id = "purchase.order,%s" % self.po.id
        wizard.action_select_source()
        self.assertEqual(wizard.state, "confirm")
        self.assertEqual(len(wizard.source_line_ids), 1)
        wizard.action_remove()
        self.assertFalse(bill.invoice_line_ids)
        self.assertEqual(bill.od19_pull_source_label, False)

    def test_removing_keeps_manually_added_lines(self):
        bill = self._bill_with_pulled_line()
        bill.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Manual line",
                            "quantity": 1.0,
                            "price_unit": 10.0,
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                        },
                    )
                ]
            }
        )
        wizard = self.env["od19.document.pull.remove.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": bill.id,
                "source_id": "purchase.order,%s" % self.po.id,
            }
        )
        wizard.action_select_source()
        wizard.action_remove()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.name, "Manual line")

    def test_remove_raises_when_posted(self):
        bill = self._bill_with_pulled_line()
        bill.action_post()
        wizard = self.env["od19.document.pull.remove.wizard"].create(
            {"res_model": "account.move", "res_id": bill.id}
        )
        with self.assertRaises(UserError):
            wizard.action_select_source()
```

> หมายเหตุ: `source_id` เป็น Reference field (เก็บค่าเป็น string `"model,id"`) จึงกำหนดค่าในเทสต์ด้วย `"purchase.order,%s" % self.po.id` โดยตรง ส่วน `source_ids` เป็น One2many แสดงรายการเอกสารต้นทางที่ผูกอยู่ (informational) และ `source_line_ids` เป็น One2many ของบรรทัดที่จะลบ

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — model `od19.document.pull.remove.wizard` ไม่มี

- [ ] **Step 3: implement remove wizard**

`wizards/od19_document_pull_remove_line.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class Od19DocumentPullRemoveSource(models.TransientModel):
    """Informational row: one source document currently bound to the target."""

    _name = "od19.document.pull.remove.source"
    _description = "OD19 Document Pull Remove Source"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.remove.wizard",
        string="Wizard / วิซาร์ด",
        required=True,
        ondelete="cascade",
    )
    source_ref = fields.Char(
        string="Source Reference / อ้างอิงเอกสารต้นทาง", readonly=True
    )
    name = fields.Char(string="Source Document / เอกสารต้นทาง", readonly=True)


class Od19DocumentPullRemoveLine(models.TransientModel):
    _name = "od19.document.pull.remove.line"
    _description = "OD19 Document Pull Remove Line"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.remove.wizard",
        string="Wizard / วิซาร์ด",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Line / รายการ", readonly=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product / สินค้า",
        readonly=True,
    )
    quantity = fields.Float(
        string="Quantity / จำนวน",
        digits="Product Unit of Measure",
        readonly=True,
    )
```

`wizards/od19_document_pull_remove_wizard.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Confirmation wizard: the user always confirms before lines are removed."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class Od19DocumentPullRemoveWizard(models.TransientModel):
    _name = "od19.document.pull.remove.wizard"
    _description = "OD19 Document Pull Remove Wizard"

    res_model = fields.Char(
        string="Destination Model / โมเดลปลายทาง", required=True
    )
    res_id = fields.Integer(
        string="Destination ID / รหัสเอกสารปลายทาง", required=True
    )
    state = fields.Selection(
        selection=[
            ("choose", "Choose the source / เลือกเอกสารต้นทาง"),
            ("confirm", "Confirm the removal / ยืนยันการลบ"),
        ],
        string="Step / ขั้นตอน",
        default="choose",
        required=True,
    )
    source_ids = fields.One2many(
        comodel_name="od19.document.pull.remove.source",
        inverse_name="wizard_id",
        string="Source Documents / เอกสารต้นทาง",
    )
    source_id = fields.Reference(
        selection="_selection_source_id",
        string="Source Document / เอกสารต้นทาง",
    )
    source_line_ids = fields.One2many(
        comodel_name="od19.document.pull.remove.line",
        inverse_name="wizard_id",
        string="Lines to remove / รายการที่จะลบ",
    )
    remove_summary = fields.Char(
        string="Summary / สรุป",
        compute="_compute_remove_summary",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _od19_get_target(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.model
    def _selection_source_id(self):
        # Static and context-independent: the ORM evaluates a Reference
        # selection on an empty recordset both when rendering the widget and
        # when validating the stored value.
        return [
            ("purchase.order", _("Purchase Order / ใบสั่งซื้อ")),
            ("sale.order", _("Sale Order / ใบสั่งขาย")),
            ("account.move", _("Invoice/Bill / ใบแจ้งหนี้/ใบวางบิล")),
            ("purchase.request", _("Purchase Request / ใบขอซื้อ")),
            ("stock.picking", _("Transfer / ใบรับ-ส่งสินค้า")),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._od19_build_bound_sources()
        return wizards

    @api.onchange("res_model", "res_id")
    def _onchange_target(self):
        self._od19_build_bound_sources()

    def _od19_build_bound_sources(self):
        self.ensure_one()
        commands = []
        if self.res_model and self.res_id:
            target = self._od19_get_target().exists()
            if target:
                commands = [
                    Command.create(
                        {
                            "source_ref": "%s,%s" % (source._name, source.id),
                            "name": "%s (%s)" % (source.display_name, count),
                        }
                    )
                    for source, count in target._od19_pull_bound_sources()
                ]
        self.source_ids = [Command.clear()] + commands

    @api.depends("source_line_ids", "source_id")
    def _compute_remove_summary(self):
        for wizard in self:
            count = len(wizard.source_line_ids)
            if wizard.source_id and count:
                wizard.remove_summary = _(
                    "Document %(name)s will have %(count)s line(s) removed.",
                    name=wizard.source_id.display_name,
                    count=count,
                )
            else:
                wizard.remove_summary = False

    def _od19_push_preview_lines(self, target, source):
        self.ensure_one()
        commands = [
            Command.create(dict(vals, wizard_id=self.id))
            for vals in target._od19_pull_preview_lines(source)
        ]
        self.source_line_ids = [Command.clear()] + commands
        return self.source_line_ids

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_select_source(self):
        """Move to the confirmation step and preview the lines to remove."""
        self.ensure_one()
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        if not self.source_id:
            raise UserError(_("Please select the source document to remove."))
        source = self.source_id
        target._od19_pull_check_source(source)
        lines = self._od19_push_preview_lines(target, source)
        if not lines:
            raise UserError(
                _(
                    "There is no line linked to %(name)s in this document.",
                    name=source.display_name,
                )
            )
        self.state = "confirm"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_back(self):
        self.ensure_one()
        self.state = "choose"
        self.source_line_ids = [Command.clear()]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_remove(self):
        """Remove the lines after the user confirmed."""
        self.ensure_one()
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        if not self.source_id:
            raise UserError(_("No source document selected."))
        target._od19_pull_remove(self.source_id)
        return {"type": "ir.actions.act_window_close"}
```

> **หมายเหตุสำคัญ (Odoo 19)**: การ clear One2many ต้องห่อ command ด้วย list เสมอ — ใช้ `self.source_line_ids = [Command.clear()]` ไม่ใช่ `self.source_line_ids = Command.clear()` เพราะ `Command.clear()` คืน tuple `(5, 0, 0)` ซึ่ง `convert_to_cache()` จะ iterate เป็น 3 command แยก (ดู `fields_relational.py`)
>
> **`_od19_push_preview_lines`** เป็น helper ของ remove wizard เอง (ไม่ใช่ของ mixin) เพราะอ่าน lineage เฉพาะของแต่ละปลายทางผ่าน `_od19_pull_preview_lines(source)`

`security/ir.model.access.csv` เติม:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_document_pull_remove_wizard_user,od19.document.pull.remove.wizard user,model_od19_document_pull_remove_wizard,base.group_user,1,1,1,1
access_od19_document_pull_remove_source_user,od19.document.pull.remove.source user,model_od19_document_pull_remove_source,base.group_user,1,1,1,1
access_od19_document_pull_remove_line_user,od19.document.pull.remove.line user,model_od19_document_pull_remove_line,base.group_user,1,1,1,1
```

> ต้องเพิ่ม `tests/__init__.py`: `from . import test_document_pull_remove` และเพิ่ม import ของ 2 ไฟล์โมดูลใหม่ใน `wizards/__init__.py`
>
> `wizards/__init__.py` เติม:
>
> ```python
> from . import od19_document_pull_remove_line
> from . import od19_document_pull_remove_wizard
> ```

- [ ] **Step 4: implement preview helper + remove implementation**

เพิ่มใน mixin (`models/od19_document_pull_mixin.py`):

```python
    def _od19_pull_preview_lines(self, source):  # pragma: no cover
        """Return the destination lines linked to source (list of dicts).

        Implement in the destination model. The dicts feed
        od19.document.pull.remove.line:
            {"name": str, "product_id": int, "quantity": float}
        """
        raise NotImplementedError
```

เพิ่มใน `models/account_move.py`:

```python
    def _od19_pull_preview_lines(self, source):
        self.ensure_one()
        if source._name == "purchase.order":
            lines = self.invoice_line_ids.filtered(
                lambda l: l.purchase_line_id.order_id == source
            )
        elif source._name == "sale.order":
            lines = self.invoice_line_ids.filtered(
                lambda l: source in l.sale_line_ids.order_id
            )
        elif source._name == "account.move":
            lines = self.invoice_line_ids.filtered(
                lambda l: l.od19_source_move_line_id.move_id == source
            )
        else:
            lines = self.env["account.move.line"].browse()
        return [
            {
                "name": line.name,
                "product_id": line.product_id.id,
                "quantity": line.quantity,
            }
            for line in lines
        ]
```

> `_od19_push_preview_lines` อยู่ใน remove wizard แล้วใน Step 3 — ไม่ต้องเพิ่มซ้ำ

- [ ] **Step 5: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_document_pull
git commit -m "feat(od19_document_pull): add remove wizard with mandatory confirmation"
```

---

## Task 6: Wizard views + ปุ่มและคอลัมน์บนฟอร์ม

**Files:**
- Create: `custom_addons/od19_document_pull/wizards/od19_document_pull_wizard_views.xml`
- Create: `custom_addons/od19_document_pull/views/account_move_views.xml`
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_views.py` (สร้าง, import)

> `views/purchase_order_views.xml` ย้ายไป Task 7 เพราะปุ่มต้องเรียกเมธอดบน `purchase.order` ซึ่งจะ inherit mixin ใน Task 7 เท่านั้น

> ปุ่มใน view ต้องเรียกเมธอด **public** (`od19_action_open_*`) เพราะ Odoo 19 ห้ามปุ่มเรียกเมธอดที่ขึ้นต้นด้วย `_`

- [ ] **Step 1: เขียน failing test**

`tests/test_document_pull_views.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDocumentPullViews(TransactionCase):
    def _view_arch(self, xmlid):
        view = self.env.ref(xmlid, raise_if_not_found=False)
        self.assertTrue(view, "missing view %s" % xmlid)
        return view.arch_db

    def test_invoice_form_has_pull_buttons(self):
        arch = self._view_arch("od19_document_pull.view_move_form_od19_document_pull")
        self.assertIn("od19_action_open_pull_wizard", arch)
        self.assertIn("od19_action_open_remove_wizard", arch)

    def test_invoice_line_source_column_is_optional(self):
        arch = self._view_arch("od19_document_pull.view_move_form_od19_document_pull")
        self.assertIn('optional="show"', arch)
        self.assertIn("od19_source_pull_label", arch)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — `missing view od19_document_pull.view_move_form_od19_document_pull`

- [ ] **Step 3: เขียน wizard views**

`wizards/od19_document_pull_wizard_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_pull_wizard_form" model="ir.ui.view">
        <field name="name">od19.document.pull.wizard.form</field>
        <field name="model">od19.document.pull.wizard</field>
        <field name="arch" type="xml">
            <form string="Pull Lines from Source / ดึงรายการจากเอกสารต้นทาง">
                <group>
                    <group>
                        <field name="res_model" invisible="1"/>
                        <field name="res_id" invisible="1"/>
                        <field name="partner_id"/>
                    </group>
                    <group>
                        <field name="source_ref"
                               options="{'no_create': True}"/>
                        <field name="mode" widget="radio"/>
                    </group>
                </group>
                <field name="line_ids" invisible="mode != 'select'">
                    <list create="false" delete="false" editable="bottom">
                        <field name="selected"/>
                        <field name="source_name"/>
                        <field name="product_id"/>
                        <field name="name"/>
                        <field name="qty_to_pull"/>
                        <field name="product_uom_id" optional="show"/>
                        <field name="price_unit"/>
                        <field name="res_model" column_invisible="1"/>
                        <field name="res_id" column_invisible="1"/>
                    </list>
                </field>
                <div class="alert alert-info" role="alert" invisible="not source_ref">
                    All lines are pulled in document order. Choose
                    "Select lines" to pick individual lines.
                </div>
                <footer>
                    <button name="action_pull" type="object" string="Pull Lines"
                            class="btn-primary"/>
                    <button string="Cancel" special="cancel" class="btn-secondary"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="view_od19_document_pull_remove_wizard_form" model="ir.ui.view">
        <field name="name">od19.document.pull.remove.wizard.form</field>
        <field name="model">od19.document.pull.remove.wizard</field>
        <field name="arch" type="xml">
            <form string="Manage/Remove Source / จัดการ/ลบเอกสารต้นทาง">
                <field name="res_model" invisible="1"/>
                <field name="res_id" invisible="1"/>
                <field name="state" invisible="1"/>
                <field name="source_ids" invisible="1"/>
                <group invisible="state != 'choose'">
                    <field name="source_id" options="{'no_create': True}"/>
                </group>
                <div invisible="state != 'confirm'">
                    <div class="alert alert-warning" role="alert">
                        <field name="remove_summary" nolabel="1"/>
                    </div>
                    <field name="source_line_ids" nolabel="1">
                        <list create="false" delete="false">
                            <field name="product_id"/>
                            <field name="name"/>
                            <field name="quantity"/>
                        </list>
                    </field>
                </div>
                <footer>
                    <button name="action_select_source" type="object"
                            string="Continue" class="btn-primary"
                            invisible="state != 'choose'"/>
                    <button name="action_remove" type="object"
                            string="Confirm Removal / ยืนยันการลบ" class="btn-danger"
                            invisible="state != 'confirm'"/>
                    <button name="action_back" type="object"
                            string="Back / ย้อนกลับ" class="btn-secondary"
                            invisible="state != 'confirm'"/>
                    <button string="Cancel" special="cancel" class="btn-secondary"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: เขียน form views ของปลายทาง (account.move เท่านั้น)**

`views/account_move_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_move_form_od19_document_pull" model="ir.ui.view">
        <field name="name">account.move.form.od19.document.pull</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="od19_action_open_pull_wizard"
                        type="object"
                        string="Pull Lines from Source / ดึงรายการจากเอกสารต้นทาง"
                        class="btn-secondary"
                        invisible="state != 'draft' or move_type not in ('in_invoice', 'out_invoice')"/>
                <button name="od19_action_open_remove_wizard"
                        type="object"
                        string="Manage/Remove Source / จัดการ/ลบเอกสารต้นทาง"
                        class="btn-secondary"
                        invisible="state != 'draft' or move_type not in ('in_invoice', 'out_invoice')"/>
            </xpath>
            <xpath expr="//field[@name='invoice_line_ids']/list/field[@name='name']" position="before">
                <field name="od19_source_pull_label"
                       string="Source Document / เอกสารต้นทาง"
                       optional="show"/>
            </xpath>
        </field>
    </record>
</odoo>
```

> ต้องมีฟิลด์ `account.move.line.od19_source_pull_label` (computed) เพิ่มใน Task 6 Step 5 เพื่อป้อนคอลัมน์นี้

> `views/purchase_order_views.xml` (ปุ่ม pull/remove + คอลัมน์ `od19_pull_source_label` บน `order_line`) สร้างใน Task 7 หลัง `purchase.order` inherit mixin แล้ว

- [ ] **Step 4b: อัปเดต `__manifest__.py` ให้โหลด views ใหม่**

`data` ต้องมี (ลำดับ: security ก่อน views):

```python
    "data": [
        "security/ir.model.access.csv",
        "wizards/od19_document_pull_wizard_views.xml",
        "views/account_move_views.xml",
    ],
```

เพิ่ม `tests/__init__.py`: `from . import test_document_pull_views`

- [ ] **Step 5: เพิ่ม computed label ระดับบรรทัดของ invoice**

เพิ่มใน `models/account_move_line.py`:

```python
    od19_source_pull_label = fields.Char(
        string="Source Document / เอกสารต้นทาง",
        compute="_compute_od19_source_pull_label",
    )

    def _compute_od19_source_pull_label(self):
        for line in self:
            source = (
                line.purchase_line_id.order_id
                or line.sale_line_ids.order_id[:1]
                or line.od19_source_move_line_id.move_id
                or line.od19_source_picking_id
            )
            line.od19_source_pull_label = source.display_name if source else "-"
```

- [ ] **Step 6: รันเทสต์ให้เห็นว่าผ่าน**

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: PASS ทั้งหมด ไม่มี warning

- [ ] **Step 7: Commit**

```bash
git add custom_addons/od19_document_pull
git commit -m "feat(od19_document_pull): wizard and form views with bilingual buttons"
```

---

## Task 7: Flow 4 — `purchase.order` ← `purchase.request`

**Files:**
- Create: `custom_addons/od19_document_pull/models/purchase_order.py`
- Create: `custom_addons/od19_document_pull/views/purchase_order_views.xml`
- Modify: `custom_addons/od19_document_pull/models/__init__.py` (import `purchase_order`)
- Modify: `custom_addons/od19_document_pull/__manifest__.py` (เพิ่ม `views/purchase_order_views.xml`)
- Modify: `custom_addons/od19_document_pull/tests/test_document_pull_views.py` (เพิ่ม test ปุ่มบน PO form)
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_purchase_request.py` (สร้าง, import)

- [ ] **Step 1: เขียน failing test**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDocumentPullPurchaseRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "PR Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "PR Product", "purchase_ok": True, "type": "consu"}
        )

    def _make_request(self, qty=3.0):
        request = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "product_uom_id": self.product.uom_id.id,
                        },
                    )
                ],
            }
        )
        request.button_approved()
        return request

    def test_source_specs_include_purchase_request(self):
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        specs = po._od19_pull_source_specs()
        self.assertEqual([s["model"] for s in specs], ["purchase.request"])

    def test_pull_creates_order_line_and_allocation(self):
        request = self._make_request()
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "purchase.order",
                "res_id": po.id,
                "source_ref": "purchase.request,%s" % request.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line.product_id, self.product)
        self.assertAlmostEqual(po.order_line.product_qty, 3.0)
        self.assertEqual(po.order_line.purchase_request_lines, request.line_ids)

    def test_candidate_lines_exclude_already_pulled(self):
        request = self._make_request()
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "purchase.order",
                "res_id": po.id,
                "source_ref": "purchase.request,%s" % request.id,
            }
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        wizard2 = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "purchase.order",
                "res_id": po.id,
                "source_ref": "purchase.request,%s" % request.id,
            }
        )
        wizard2._onchange_source_ref()
        self.assertEqual(len(wizard2.line_ids), 0)

    def test_remove_frees_the_request_line(self):
        request = self._make_request()
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "purchase.order",
                "res_id": po.id,
                "source_ref": "purchase.request,%s" % request.id,
            }
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        self.assertTrue(request.line_ids.purchase_lines)
        po._od19_pull_remove(request)
        self.assertFalse(po.order_line)
        self.assertFalse(request.line_ids.purchase_lines)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — `_od19_pull_source_specs` คืน `[]` (purchase.order ยังไม่ inherit mixin)

- [ ] **Step 3: implement `models/purchase_order.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "od19.document.pull.mixin"]

    od19_pull_source_label = fields.Char(
        string="Source Documents / เอกสารต้นทาง",
        compute="_compute_od19_pull_source_label",
    )

    @api.depends("order_line.purchase_request_lines")
    def _compute_od19_pull_source_label(self):
        for order in self:
            parts = [
                "%s (%s)" % (source.display_name, count)
                for source, count in order._od19_pull_bound_sources()
            ]
            order.od19_pull_source_label = ", ".join(parts) or False

    def _od19_pull_editable_states(self):
        return ("draft", "sent")

    def _od19_pull_source_specs(self):
        self.ensure_one()
        return [
            {
                "model": "purchase.request",
                "label": _("Purchase Request / ใบขอซื้อ"),
                "domain": [
                    ("state", "in", ("approved", "purchase_order")),
                ],
            },
        ]

    def _od19_pull_candidate_lines(self, source):
        self.ensure_one()
        if source._name != "purchase.request":
            return self.env["purchase.request.line"].browse()
        taken_requests = self.order_line.purchase_request_lines
        return source.line_ids.filtered(lambda l: l not in taken_requests)

    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        return {
            "res_model": line._name,
            "res_id": line.id,
            "source_name": source.display_name,
            "product_id": line.product_id.id,
            "name": line.name or line.product_id.display_name,
            "qty_to_pull": line.product_qty,
            "price_unit": line.od19_price_unit or 0.0,
            "product_uom_id": line.product_uom_id.id,
        }

    def _od19_pull_apply(self, source, lines):
        """Delegate creation to the OCA wizard so allocations stay correct."""
        self.ensure_one()
        self._od19_pull_check_editable()
        if source._name != "purchase.request" or not lines:
            return 0
        item_commands = []
        for pr_line in lines:
            item_commands.append(
                (
                    0,
                    0,
                    {
                        "line_id": pr_line.id,
                        "request_id": pr_line.request_id.id,
                        "product_id": pr_line.product_id.id,
                        "name": pr_line.name or pr_line.product_id.display_name,
                        "product_qty": pr_line.product_qty,
                        "product_uom_id": pr_line.product_uom_id.id,
                    },
                )
            )
        wizard = self.env["purchase.request.line.make.purchase.order"].create(
            {
                "purchase_order_id": self.id,
                "supplier_id": self.partner_id.id,
                "item_ids": item_commands,
            }
        )
        wizard.make_purchase_order()
        return len(item_commands)

    def _od19_pull_preview_lines(self, source):
        self.ensure_one()
        if source._name != "purchase.request":
            return []
        lines = self.order_line.filtered(
            lambda l: any(rl.request_id == source for rl in l.purchase_request_lines)
        )
        return [
            {
                "name": line.name,
                "product_id": line.product_id.id,
                "quantity": line.product_qty,
            }
            for line in lines
        ]

    def _od19_pull_remove(self, source):
        """Remove PO lines coming from source and free the PR lines."""
        self.ensure_one()
        self._od19_pull_check_editable()
        if source._name != "purchase.request":
            return 0
        lines = self.order_line.filtered(
            lambda l: any(rl.request_id == source for rl in l.purchase_request_lines)
        )
        if not lines:
            return 0
        self.env["purchase.request.allocation"].search(
            [("purchase_line_id", "in", lines.ids)]
        ).unlink()
        count = len(lines)
        lines.unlink()
        return count

    def _od19_pull_bound_sources(self):
        self.ensure_one()
        found = []
        for source in self.order_line.purchase_request_lines.request_id:
            count = len(
                self.order_line.filtered(
                    lambda l: any(
                        rl.request_id == source for rl in l.purchase_request_lines
                    )
                )
            )
            found.append((source, count))
        return found
```

> `remove.line` preview model มีฟิลด์ `name` เป็น Char — `_od19_pull_preview_lines` ของ PO คืน `name` (description) จึงเข้ากันได้

- [ ] **Step 4: เขียน form view ของ `purchase.order` (ย้ายมาจาก Task 6)**

`views/purchase_order_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_order_form_od19_document_pull" model="ir.ui.view">
        <field name="name">purchase.order.form.od19.document.pull</field>
        <field name="model">purchase.order</field>
        <field name="inherit_id" ref="purchase.purchase_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="od19_action_open_pull_wizard"
                        type="object"
                        string="Pull Lines from Source / ดึงรายการจากเอกสารต้นทาง"
                        class="btn-secondary"
                        invisible="state not in ('draft', 'sent')"/>
                <button name="od19_action_open_remove_wizard"
                        type="object"
                        string="Manage/Remove Source / จัดการ/ลบเอกสารต้นทาง"
                        class="btn-secondary"
                        invisible="state not in ('draft', 'sent')"/>
            </xpath>
            <xpath expr="//field[@name='order_line']/list/field[@name='product_id']" position="before">
                <field name="od19_pull_source_label"
                       string="Source Document / เอกสารต้นทาง"
                       optional="show"/>
            </xpath>
        </field>
    </record>
</odoo>
```

อัปเดต `__manifest__.py` ให้เพิ่ม `"views/purchase_order_views.xml"` ต่อท้าย `views/account_move_views.xml`

เพิ่มใน `tests/test_document_pull_views.py`:

```python
    def test_purchase_order_form_has_pull_buttons(self):
        arch = self._view_arch(
            "od19_document_pull.view_order_form_od19_document_pull"
        )
        self.assertIn("od19_action_open_pull_wizard", arch)
        self.assertIn("od19_action_open_remove_wizard", arch)
```

- [ ] **Step 5: ให้ `purchase_order_line.py` มี label column (ทำแล้วใน Task 3) และตรวจ import**

แก้ `models/__init__.py` ให้ import `purchase_order_line` ก่อน `purchase_order`

- [ ] **Step 6: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add custom_addons/od19_document_pull
git commit -m "feat(od19_document_pull): wire flow 4 (purchase order from purchase request)"
```

---

## Task 8: Flow 3 เดิม — ให้ `od19_sale_wizards` เรียกกลไกกลาง (เลิกระบบซ้อน)

**Files:**
- Modify: `custom_addons/od19_sale_wizards/models/account_move.py:37-60`
- Modify: `custom_addons/od19_sale_wizards/views/account_move_views.xml:10-16`
- Modify: `custom_addons/od19_sale_wizards/__manifest__.py` (depends)
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_sale.py` (สร้าง, import)

- [ ] **Step 1: เขียน failing test**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullSale(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.partner_a
        cls.product = cls.product_a

    def _confirmed_so(self, qty=4.0):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": 250.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        return so

    def test_pull_sale_lines_two_modes(self):
        so = self._confirmed_so()
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": "2026-02-01",
            }
        )
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": invoice.id,
                "source_ref": "sale.order,%s" % so.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.sale_line_ids, so.order_line)
        self.assertAlmostEqual(invoice.invoice_line_ids.price_unit, 250.0)

    def test_legacy_get_sale_lines_button_uses_central_mechanism(self):
        so = self._confirmed_so()
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": "2026-02-01",
            }
        )
        action = invoice.action_open_get_sale_lines()
        self.assertEqual(action["res_model"], "od19.document.pull.wizard")
        self.assertEqual(action["context"]["default_res_id"], invoice.id)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — `action_open_get_sale_lines` ยังชี้ `od19.account.invoice.get.sale.lines`

- [ ] **Step 3: แก้ `od19_sale_wizards`**

`models/account_move.py` — เปลี่ยนเมธอด `action_open_get_sale_lines` ให้เรียกกลไกกลาง (ลบ body เดิมทั้งหมด):

```python
    def action_open_get_sale_lines(self):
        """Open the central document pull wizard (flow 3).

        Kept for backward compatibility: the old dedicated wizard is
        replaced by the shared od19_document_pull mechanism.
        """
        self.ensure_one()
        return self._od19_pull_action_open_pull_wizard()
```

`views/account_move_views.xml` — เปลี่ยนปุ่มเดิมให้ใช้ action ของกลไกกลาง (แก้ block `view_move_form_od19_get_sale_lines`):

```xml
    <record id="view_move_form_od19_get_sale_lines" model="ir.ui.view">
        <field name="name">account.move.form.od19.get.sale.lines</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="_od19_pull_action_open_pull_wizard"
                        type="object"
                        string="Get Sale Order Lines / ดึงรายการจากใบสั่งขาย"
                        class="btn-secondary"
                        invisible="state != 'draft' or move_type != 'out_invoice'"/>
            </xpath>
        </field>
    </record>
```

`__manifest__.py` — เพิ่ม dependency และลบ wizard เดิม:

```python
    "depends": [
        "sale_management",
        "account",
        "sale_purchase",
        "od19_document_pull",
    ],
```

`wizards/__init__.py` — ลบบรรทัด `from . import account_invoice_get_sale_lines`
`__manifest__.py` data — ลบบรรทัด `"wizards/account_invoice_get_sale_lines_views.xml",`
เพิ่มไฟล์ `views/account_move_views.xml` ให้ชี้ปุ่มใหม่ (ดูด้านบน)

ลบไฟล์ที่เลิกใช้:
- `custom_addons/od19_sale_wizards/wizards/account_invoice_get_sale_lines.py`
- `custom_addons/od19_sale_wizards/wizards/account_invoice_get_sale_lines_views.xml`

- [ ] **Step 4: รันเทสต์ให้เห็นว่าผ่าน**

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_document_pull -u od19_sale_wizards --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_document_pull custom_addons/od19_sale_wizards
git commit -m "refactor(od19_sale_wizards): route invoice-line pulling through od19_document_pull"
```

---

## Task 9: Flow 5 ในตารางสเปก — แก้ `purchase_create_vendor_bill` ให้กรอง `qty_to_invoice > 0`

**Files:**
- Modify: `custom_addons/od19_purchase_wizards/wizards/purchase_create_vendor_bill.py:59-78`
- Test: `custom_addons/od19_document_pull/tests/test_purchase_create_vendor_bill_filter.py` (สร้าง, import)

- [ ] **Step 1: เขียน failing test**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCreateVendorBillFilter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Filter Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Filter Product",
                "purchase_ok": True,
                "type": "consu",
                "invoice_policy": "order",
            }
        )

    def test_create_bill_without_qty_to_invoice_creates_no_line(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 2.0,
                            "price_unit": 50.0,
                            "name": self.product.name,
                            "date_planned": "2026-01-01",
                        },
                    )
                ],
            }
        )
        # Force the line to be considered already billed.
        po.order_line.qty_invoiced = 2.0
        po.button_confirm()
        po.order_line.qty_invoiced = 2.0

        wizard = self.env["od19.purchase.create.vendor.bill"].create(
            {"purchase_order_id": po.id, "bill_date": "2026-02-01"}
        )
        action = wizard.action_create_bill()
        bill = self.env["account.move"].browse(action["res_id"])
        self.assertFalse(bill.invoice_line_ids)
```

> หมายเหตุ: `qty_invoiced` เป็น computed store field ที่ `purchase` คำนวณจาก `invoice_lines`; การ set ตรง ๆ ในเทสต์จะถูก recompute — หาก recompute ให้กำหนดผ่าน `env.cr.execute` หรือใช้เทคนิค single-line-context ของ Odoo (`self.env["purchase.order.line"].with_context(...)`) ตามที่ใช้ใน [test_procurement_line_semantics.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_purchase_procurement_core/tests/test_procurement_line_semantics.py) ถ้าวิธีตั้งค่าตรงไม่คงอยู่ ให้ใช้ `_compute_qty_invoiced` ด้วย monkeypatch บน recordset แทน

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — `bill.invoice_line_ids` มี 1 บรรทัด

- [ ] **Step 3: แก้ loop ให้กรอง**

แก้ `wizards/purchase_create_vendor_bill.py` เฉพาะ loop (คงส่วนอื่น):

```python
        invoice_lines = []
        sequence = 10
        pending_section = None
        for line in po.order_line:
            if line.display_type in ("line_section", "line_subsection"):
                pending_section = line
                continue
            if line.qty_to_invoice <= 0:
                # Skip lines with nothing left to bill (style A).
                continue
            if pending_section:
                section_vals = pending_section._prepare_account_move_line()
                section_vals.update({"sequence": sequence})
                invoice_lines.append((0, 0, section_vals))
                sequence += 10
                pending_section = None

            line_vals = line._prepare_account_move_line()
            line_vals.update({"sequence": sequence})
            invoice_lines.append((0, 0, line_vals))
            sequence += 10
```

- [ ] **Step 4: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_purchase_wizards custom_addons/od19_document_pull/tests
git commit -m "fix(od19_purchase_wizards): only bill lines with qty_to_invoice > 0"
```

---

## Task 10: คำแปลไทย + เก็บกวาด log

**Files:**
- Create: `custom_addons/od19_document_pull/i18n/th.po`
- Modify: `custom_addons/od19_document_pull/__manifest__.py` (ไม่ต้องเพิ่ม i18n ใน data — Odoo โหลดอัตโนมัติ)

- [ ] **Step 1: export/สร้างไฟล์ th.po**

สร้าง `i18n/th.po` ด้วยโครงมาตรฐาน Odoo:

```po
# Translation of Odoo Server.
# This file contains the translation of the following modules:
# 	* od19_document_pull
#
msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 19.0\n"
"Report-Msgid-Bugs-To: \n"
"PO-Revision-Date: 2026-10-23 00:00+0000\n"
"Last-Translator: OD19\n"
"Language-Team: Thai\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: th\n"
"Plural-Forms: nplurals=1; plural=0;\n"

#. module: od19_document_pull
#: model:ir.actions.act_window,name:od19_document_pull.view_od19_document_pull_wizard_form
msgid "Pull Lines from Source / ดึงรายการจากเอกสารต้นทาง"
msgstr "ดึงรายการจากเอกสารต้นทาง / Pull Lines from Source"
```

> สร้างรายการ msgid ให้ครบทุก label ที่เป็นสองภาษา โดยสลับลำดับไทย/อังกฤษเพื่อให้ผู้ใช้ไทยเห็นไทยก่อน (และเก็บอังกฤษไว้ท้ายสตริง)

- [ ] **Step 2: อัปเดต-ติดตั้งและตรวจ log**

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_document_pull --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: PASS, ไม่มี warning ที่เกี่ยวกับโมดูลนี้ (อ่าน `odoo_server.log`)

- [ ] **Step 3: Commit**

```bash
git add custom_addons/od19_document_pull/i18n
git commit -m "i18n(od19_document_pull): add Thai translations"
```

---

# เฟส 2 — Style B (ใบรับ/ใบส่ง) + รายงาน GRNI

## Task 11: Pull จากใบรับของ (flow 5) และใบส่งของ (flow 6)

**Files:**
- Modify: `custom_addons/od19_document_pull/models/account_move.py`
- Test: `custom_addons/od19_document_pull/tests/test_document_pull_picking.py` (สร้าง, import)

- [ ] **Step 1: เขียน failing test**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDocumentPullPicking(TransactionCase):
    """Style B: the receipt/delivery only filters PO/SO lines (money comes
    from the PO/SO line, never from the picking)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Pick Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Pick Product",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "received",
            }
        )

    def _receipt(self, qty=3.0):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "price_unit": 70.0,
                            "name": self.product.name,
                            "date_planned": "2026-01-01",
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids.write({"quantity": qty, "picked": True})
        picking.button_validate()
        return po, picking

    def test_pull_by_receipt_sets_source_picking(self):
        po, picking = self._receipt()
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": bill.id,
                "source_ref": "stock.picking,%s" % picking.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.od19_source_picking_id, picking)
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, po.order_line)

    def test_pull_by_receipt_skips_when_receipt_not_done(self):
        po, picking = self._receipt()
        picking2 = po.picking_ids[:1]
        picking2.state = "assigned"
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )
        self.assertFalse(
            bill._od19_pull_candidate_lines(picking2),
            "lines must not be pullable from a receipt that is not done",
        )
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — spec `stock.picking` ไม่มีใน `_od19_pull_source_specs`

- [ ] **Step 3: implement style B**

เพิ่มใน `models/account_move.py` — แก้ `_od19_pull_source_specs`, `_od19_pull_candidate_lines`, `_od19_pull_line_info`, `_od19_pull_apply`, `_od19_pull_remove`, `_od19_pull_bound_sources`, `_od19_pull_preview_lines` ให้รองรับ `stock.picking`:

```python
    def _od19_pull_picking_types(self):
        """Return the picking types allowed as a source for this document."""
        self.ensure_one()
        if self.move_type == "in_invoice":
            return ("incoming",)
        if self.move_type == "out_invoice":
            return ("outgoing",)
        return ()

    def _od19_pull_picking_line_filter(self, picking, line):
        """Return True when a PO/SO line is billable for this picking."""
        self.ensure_one()
        if picking.state != "done":
            return False
        moves = line.move_ids.filtered(lambda m: m.picking_id == picking)
        if not moves:
            return False
        if self.move_type == "in_invoice":
            return line.qty_to_invoice > 0
        return line.qty_to_invoice > 0
```

แก้ `_od19_pull_source_specs` เพิ่มท่อนท้าย (ก่อน `return []` ของกรณี in/out):

```python
        picking_types = self._od19_pull_picking_types()
        if picking_types:
            specs.append(
                {
                    "model": "stock.picking",
                    "label": _("Receipt/Delivery / ใบรับ-ใบส่งของ"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("picking_type_code", "in", picking_types),
                        ("state", "=", "done"),
                    ],
                }
            )
        return specs
```

แก้ `_od19_pull_candidate_lines` เพิ่ม:

```python
        if source._name == "stock.picking":
            taken = self.invoice_line_ids.od19_source_picking_id.ids
            if source.id in taken:
                return self.env["account.move.line"].browse()
            lines = source.move_ids.purchase_line_id.filtered(
                lambda l: self._od19_pull_picking_line_filter(source, l)
            )
            return lines
```

แก้ `_od19_pull_line_info` ให้รองรับ PO/SO line ที่มาจาก picking โดยส่ง `source_name` ของ picking ผ่าน `source` ที่เป็น picking:

```python
    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        if source._name == "stock.picking":
            po_line = line
            return {
                "res_model": po_line._name,
                "res_id": po_line.id,
                "source_name": source.display_name,
                "product_id": po_line.product_id.id,
                "name": po_line.name,
                "qty_to_pull": po_line.qty_to_invoice,
                "price_unit": po_line.price_unit,
                "product_uom_id": po_line.product_uom_id.id,
            }
        # ... ส่วนเดิม
```

แก้ `_od19_pull_apply` เพิ่มสาขา (ก่อน `else: return 0`):

```python
        elif source._name == "stock.picking":
            for po_line in lines.sorted("sequence"):
                vals = po_line._prepare_account_move_line(self)
                vals["sequence"] = sequence
                vals["od19_source_picking_id"] = source.id
                commands.append(Command.create(vals))
                sequence += 10
```

แก้ `_od19_pull_remove` และ `_od19_pull_preview_lines` และ `_od19_pull_bound_sources` เพิ่ม:

```python
        if source._name == "stock.picking":
            lines = self.invoice_line_ids.filtered(
                lambda l: l.od19_source_picking_id == source
            )
```

และใน `_od19_pull_bound_sources`:

```python
        for source in self.invoice_line_ids.od19_source_picking_id:
            count = len(
                self.invoice_line_ids.filtered(
                    lambda l: l.od19_source_picking_id == source
                )
            )
            found.append((source, count))
```

- [ ] **Step 4: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_document_pull
git commit -m "feat(od19_document_pull): bill by receipt/delivery with picking lineage (flow 5,6)"
```

---

## Task 12: รายงาน GRNI (Goods Received Not Invoiced)

**Files:**
- Create: `custom_addons/od19_document_pull/report/grni_report_views.xml`
- Modify: `custom_addons/od19_document_pull/__manifest__.py` (เพิ่ม data)
- Test: `custom_addons/od19_document_pull/tests/test_grni_report.py` (สร้าง, import)

- [ ] **Step 1: เขียน failing test**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestGrniReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "GRNI Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "GRNI Product",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "received",
            }
        )

    def test_grni_action_exists(self):
        action = self.env.ref(
            "od19_document_pull.action_od19_grni_report", raise_if_not_found=False
        )
        self.assertTrue(action, "GRNI action must be defined")
        self.assertEqual(action.res_model, "purchase.order.line")

    def test_grni_domain_returns_received_not_billed(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 3.0,
                            "price_unit": 70.0,
                            "name": self.product.name,
                            "date_planned": "2026-01-01",
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids.write({"quantity": 3.0, "picked": True})
        picking.button_validate()

        domain = self.env["purchase.order.line"]._od19_grni_domain()
        self.assertEqual(self.env["purchase.order.line"].search_count(domain), 1)

        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": bill.id,
                "source_ref": "purchase.order,%s" % po.id,
            }
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        bill.action_post()
        self.assertEqual(self.env["purchase.order.line"].search_count(domain), 0)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Expected: FAIL — ไม่มี `action_od19_grni_report` และไม่มี `_od19_grni_domain`

- [ ] **Step 3: implement**

เพิ่มใน `models/purchase_order_line.py`:

```python
    @api.model
    def _od19_grni_domain(self):
        """Lines received (receipt done) but not yet fully billed."""
        return [
            ("order_id.state", "in", ("purchase", "done")),
            ("qty_received", ">", 0),
            ("qty_to_invoice", ">", 0),
            ("display_type", "=", False),
        ]
```

`report/grni_report_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_grni_report_list" model="ir.ui.view">
        <field name="name">od19.grni.report.list</field>
        <field name="model">purchase.order.line</field>
        <field name="arch" type="xml">
            <list string="GRNI / ของรับแล้วยังไม่วางบิล" create="false" edit="false">
                <field name="order_id"/>
                <field name="partner_id"/>
                <field name="date_planned"/>
                <field name="product_id"/>
                <field name="name"/>
                <field name="product_qty"/>
                <field name="qty_received"/>
                <field name="qty_invoiced"/>
                <field name="qty_to_invoice" string="GRNI Qty / คงค้าง"/>
                <field name="price_unit"/>
                <field name="currency_id" column_invisible="1"/>
            </list>
        </field>
    </record>

    <record id="action_od19_grni_report" model="ir.actions.act_window">
        <field name="name">GRNI (Received Not Invoiced) / ของรับแล้วยังไม่วางบิล</field>
        <field name="res_model">purchase.order.line</field>
        <field name="view_mode">list,pivot,form</field>
        <field name="domain">[('order_id.state', 'in', ('purchase', 'done')), ('qty_received', '&gt;', 0), ('qty_to_invoice', '&gt;', 0), ('display_type', '=', False)]</field>
        <field name="context">{'search_default_group_by_partner': 1}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                No received-but-unbilled purchase line.
            </p>
        </field>
    </record>

    <menuitem id="menu_od19_grni_report"
              name="GRNI / ของรับแล้วยังไม่วางบิล"
              parent="purchase.menu_purchase_reports"
              action="action_od19_grni_report"
              sequence="90"/>
</odoo>
```

เพิ่มใน `__manifest__.py` data list (ต่อท้าย):

```python
        "report/grni_report_views.xml",
```

- [ ] **Step 4: รันเทสต์ให้เห็นว่าผ่าน**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_document_pull
git commit -m "feat(od19_document_pull): add GRNI (received not invoiced) report"
```

---

## Task 13: ตรวจสอบขั้นสุดท้าย (Full module verification)

- [ ] **Step 1: รันเทสต์ทั้งชุดของโมดูล**

```powershell
cd c:\odoo-dev\odoo19
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev `
  -u od19_document_pull -u od19_sale_wizards -u od19_purchase_wizards `
  --test-tags /od19_document_pull --stop-after-init --no-http
```

Expected: PASS ทั้งหมด, 0 failed, 0 error

- [ ] **Step 2: ตรวจ log ว่าไม่มี warning ของโมดูลนี้**

อ่าน `c:\odoo-dev\odoo19\odoo_server.log` และค้นหา `od19_document_pull` ที่ระดับ `WARNING` ขึ้นไป — ต้องไม่มี

- [ ] **Step 3: ตรวจ coverage เทียบสเปก**

ไล่ทีละข้อของสเปกแล้วยืนยันว่ามีเทสต์ครอบ:
- 6 flow × 2 โหมด → `test_document_pull_purchase.py`, `_sale.py`, `_purchase_request.py`, `_picking.py`
- ยืนยันก่อนลบทุกเส้นทาง → `test_document_pull_remove.py`
- guard: post แล้วห้าม, partner ไม่ตรง, lineage หาย → `test_document_pull_guards.py`
- รายงาน GRNI → `test_grni_report.py`

- [ ] **Step 4: Commit ปิดงาน**

```bash
git add custom_addons docs
git commit -m "test(od19_document_pull): final verification for phases 1-2"
```

---

## Self-Review Notes (ผู้เขียนแผน)

**Spec coverage**

| ข้อสเปก | Task |
|---|---|
| กลไกกลาง (mixin + contract) | 2 |
| 2 โหมดการดึง (all_order / select) | 4 |
| ยืนยันก่อนลบ (2 state) | 5 |
| ลบตาม lineage ไม่กระทบบรรทัดที่กรอกเอง | 4, 5 |
| flow 1,2 (ใบวางบิล ← PO / ใบวางบิลเดิม) | 4 |
| flow 3 (ใบแจ้งหนี้ ← SO) | 4, 8 |
| flow 4 (PO ← PR) | 7 |
| flow 5,6 (ใบรับ/ใบส่ง) | 11 |
| รายงาน GRNI | 12 |
| คอลัมน์ "เอกสารต้นทาง" optional | 3, 6 |
| ปุ่มสองภาษา | 6, 10 |
| ไม่แตะ core | ทั้งหมด (มีแต่ custom_addons) |

**Known risks / assumptions ที่ต้องยืนยันตอนลงมือ**

1. `account.move.line.copy_data()` ใน flow 2 — ต้องทดสอบจริงว่าได้ key ที่ต้องการครบ และไม่มี `move_id` ซ้ำ; ถ้าไม่ตรงให้เปลี่ยนไปใช้ `_prepare_account_move_line`-style explicit dict
2. `qty_invoiced` เป็น computed store — เทสต์ Task 9 อาจต้องใช้ `with_context` หรือ patch แทนการ set ตรง
3. ชื่อเมนูปลายทาง `purchase.menu_purchase_reports` และ `purchase.purchase_order_form` ต้องตรวจว่ามีอยู่จริงใน Odoo 19 (ถ้า ref เปลี่ยน ให้ปรับตาม `read` ของ view จริง)
4. `purchase.request.line.od19_price_unit` มาจาก `od19_purchase_wizards` — ถ้าไม่ติดตั้ง โมดูลนี้ยังทำงานได้ (ค่า `price_unit` จะเป็น 0 แล้ว PO line ใช้ราคาจาก vendor pricelist ตามปกติของ OCA wizard)
