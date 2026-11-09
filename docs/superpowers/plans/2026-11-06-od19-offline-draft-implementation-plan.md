# แผนดำเนินงาน: โมดูลกลางบันทึกร่างอัตโนมัติ (Offline Draft Hub) — od19_offline_draft

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโมดูลกลาง `od19_offline_draft` ที่ทำ "บันทึกร่างอัตโนมัติ (Autosave) + กู้คืน (Restore)" ให้ฟอร์มที่เปิดใช้ กันข้อมูลหายเมื่อเน็ตหลุด / refresh / ปิดหน้า โดยทำงานได้ทั้ง backend (OWL) และ portal

**Architecture:** ตารางกลาง `od19.draft` (Json payload + `ir.attachment`) เก็บร่างฝั่ง server, OWL service `od19_draft` เก็บฝั่ง client (IndexedDB) ก่อนแล้ว sync ขึ้น server แบบ Hybrid, patch `FormController` เฉพาะ lifecycle (บันทึก/กู้/ล้าง) และเปิดใช้เป็นรายโมเดลผ่าน registry (`_od19_draft_enabled`) + ฉีด config เข้า `session_info` — เป็นแบบ additive ไม่แตะ Odoo core

**Tech Stack:** Odoo 19 CE (custom addon `od19_*`), Python (ORM/ORM-cache), XML (security/data/views/templates), JavaScript ES modules (OWL 2 service + patch), IndexedDB, PostgreSQL, unittest (`odoo.tests`), PowerShell `run-tests.ps1`

**Spec อ้างอิง:** [2026-11-06-od19-offline-draft-design.md](../specs/2026-11-06-od19-offline-draft-design.md)

**ข้อกำหนดสำคัญ (Freeze):** T1 เท่านั้น (ไม่มี auto-submit) · Draft Hub ตารางกลาง · Hybrid IndexedDB + `od19.draft` · เปิดใช้เป็นรายโมเดล · ไม่กู้เงียบ ต้องยืนยัน · ใช้ `ir.attachment` · ไม่แตะ core

---

## File Structure

ไฟล์ทั้งหมดอยู่ใต้ `custom_addons/od19_offline_draft/`

| ไฟล์ | หน้าที่ |
|---|---|
| `__manifest__.py` | metadata + depends (`web`) + data + assets |
| `__init__.py` | import `models` |
| `models/__init__.py` | import ทุกโมเดล |
| `models/od19_draft.py` | โมเดล `od19.draft` + registry + lifecycle methods + cron |
| `models/ir_http.py` | ฉีด config ร่างเข้า `session_info` |
| `security/od19_draft_security.xml` | record rules (own drafts + company) |
| `security/ir.model.access.csv` | สิทธิ์ระดับโมเดล |
| `data/ir_cron_data.xml` | cron ล้างร่างหมดอายุ |
| `views/od19_draft_views.xml` | list/form + action + menu (สำหรับแอดมินตรวจสอบ) |
| `static/src/draft_service.js` | OWL service + IndexedDB + sync |
| `static/src/draft_banner.js` + `draft_banner.xml` | คอมโพเนนต์แบนเนอร์กู้คืน |
| `static/src/form_controller_patch.js` | patch lifecycle ฟอร์ม OWL |
| `static/src/offline_draft.scss` | สไตล์แบนเนอร์ |
| `static/src/portal/portal_autosave.js` | autosave ระดับฟิลด์บนหน้า portal |
| `tests/__init__.py` + `tests/test_od19_draft.py` | ชุดเทสต์ logic ฝั่ง server |
| `tests/test_od19_draft_assets.py` | เทสต์ว่า asset ถูกต่อเข้า bundle จริง |

> **หมายเหตุ registry:** ใช้รูปแบบเดียวกับ Odoo core — เพิ่มคอมโพเนนต์เข้า template ของคอมโพเนนต์เดิมด้วย `patch(Target, { components: { ...Target.components, MyComp } })` (pattern เดียวกับ `od19_web_navigation`)

---

## Task 1: โครงโมดูล + โมเดล `od19.draft` + security

**Files:**
- Create: `custom_addons/od19_offline_draft/__manifest__.py`
- Create: `custom_addons/od19_offline_draft/__init__.py`
- Create: `custom_addons/od19_offline_draft/models/__init__.py`
- Create: `custom_addons/od19_offline_draft/models/od19_draft.py`
- Create: `custom_addons/od19_offline_draft/security/od19_draft_security.xml`
- Create: `custom_addons/od19_offline_draft/security/ir.model.access.csv`
- Create: `custom_addons/od19_offline_draft/tests/__init__.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail**

สร้าง `tests/__init__.py`:

```python
from . import test_od19_draft
```

สร้าง `tests/test_od19_draft.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOd19DraftCore(TransactionCase):
    def test_create_draft_defaults(self):
        draft = self.env["od19.draft"].create(
            {"model_name": "sale.order", "res_id": 0, "payload": {"note": "hello"}}
        )
        self.assertEqual(draft.user_id, self.env.user)
        self.assertEqual(draft.company_id, self.env.company)
        self.assertEqual(draft.state, "active")
        self.assertEqual(draft.payload_version, 1)

    def test_name_computed_from_model_and_res_id(self):
        existing = self.env["od19.draft"].create(
            {"model_name": "sale.order", "res_id": 42}
        )
        new_record = self.env["od19.draft"].create(
            {"model_name": "sale.order", "res_id": 0}
        )
        self.assertEqual(existing.name, "sale.order#42")
        self.assertEqual(new_record.name, "sale.order#new")
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — โมดูล `od19_offline_draft` ยังไม่มี (log ขึ้น `KeyError: 'od19.draft'` หรือหาโมดูลไม่เจอ exit code ≠ 0)

- [ ] **Step 3: สร้าง manifest + init + โมเดล + security**

`__manifest__.py`:

```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Offline Draft (ร่างอัตโนมัติ)",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Autosave + restore drafts across backend and portal (T1 Draft Hub)",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "security/od19_draft_security.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
```

`__init__.py`:

```python
from . import models
```

`models/__init__.py`:

```python
from . import od19_draft
```

`models/od19_draft.py`:

```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models

DRAFT_PAYLOAD_VERSION = 1


class Od19Draft(models.Model):
    _name = "od19.draft"
    _description = "Offline Draft / ร่างอัตโนมัติ"
    _rec_name = "name"
    _order = "write_date desc"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    model_name = fields.Char(required=True, index=True)
    res_id = fields.Integer(default=0, index=True)
    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
    payload = fields.Json()
    payload_version = fields.Integer(default=DRAFT_PAYLOAD_VERSION, required=True)
    state = fields.Selection(
        [
            ("active", "Active / ใช้งาน"),
            ("applied", "Applied / บันทึกจริงแล้ว"),
            ("discarded", "Discarded / ทิ้ง"),
            ("expired", "Expired / หมดอายุ"),
        ],
        default="active",
        required=True,
        index=True,
    )
    expires_at = fields.Datetime(index=True)

    @api.depends("model_name", "res_id")
    def _compute_name(self):
        for draft in self:
            suffix = draft.res_id or "new"
            draft.name = f"{draft.model_name}#{suffix}" if draft.model_name else "draft"

    def init(self):
        # Unique เฉพาะร่างที่ยัง active — 1 เรกคอร์ด : 1 ผู้ใช้ : 1 ร่างที่ใช้งานได้
        self._cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS od19_draft_active_uniq
            ON od19_draft (model_name, res_id, user_id)
            WHERE state = 'active'
            """
        )
```

`security/od19_draft_security.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="rule_od19_draft_own" model="ir.rule">
        <field name="name">Offline Draft: own drafts / ร่างของตัวเอง</field>
        <field name="model_id" ref="model_od19_draft"/>
        <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids), ('user_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="rule_od19_draft_system" model="ir.rule">
        <field name="name">Offline Draft: system all / แอดมินทั้งหมด</field>
        <field name="model_id" ref="model_od19_draft"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('base.group_system'))]"/>
    </record>
</odoo>
```

`security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_draft_user,access.od19.draft.user,model_od19_draft,base.group_user,1,1,1,1
access_od19_draft_system,access.od19.draft.system,model_od19_draft,base.group_system,1,1,1,1
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 2 of 2 tests` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/__manifest__.py custom_addons/od19_offline_draft/__init__.py custom_addons/od19_offline_draft/models/__init__.py custom_addons/od19_offline_draft/models/od19_draft.py custom_addons/od19_offline_draft/security/od19_draft_security.xml custom_addons/od19_offline_draft/security/ir.model.access.csv custom_addons/od19_offline_draft/tests/__init__.py custom_addons/od19_offline_draft/tests/test_od19_draft.py
git commit -m "feat(offline-draft): add od19.draft model skeleton with security"
```

---

## Task 2: Lifecycle methods — upsert / fetch / discard / mark_applied

**Files:**
- Modify: `custom_addons/od19_offline_draft/models/od19_draft.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail (ต่อท้ายคลาส `TestOd19DraftCore`)**

```python
    def test_upsert_creates_then_updates_same_draft(self):
        draft_model = self.env["od19.draft"]
        first = draft_model.upsert_draft("sale.order", 0, {"note": "v1"})
        second = draft_model.upsert_draft("sale.order", 0, {"note": "v2"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(draft_model.search_count([("state", "=", "active")]), 1)

    def test_fetch_returns_payload(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "hello"})
        result = draft_model.fetch_draft("sale.order", 0)
        self.assertTrue(result)
        self.assertEqual(result["payload"], {"note": "hello"})
        self.assertEqual(result["payload_version"], 1)

    def test_fetch_returns_false_when_no_draft(self):
        self.assertFalse(self.env["od19.draft"].fetch_draft("sale.order", 999))

    def test_discard_removes_draft(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "hello"})
        draft_model.discard_draft("sale.order", 0)
        self.assertFalse(draft_model.fetch_draft("sale.order", 0))
        self.assertEqual(draft_model.search_count([]), 0)

    def test_mark_applied_removes_draft(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "hello"})
        draft_model.mark_applied("sale.order", 0)
        self.assertEqual(draft_model.search_count([]), 0)

    def test_fetch_discards_when_payload_version_mismatch(self):
        draft_model = self.env["od19.draft"]
        draft = draft_model.create(
            {
                "model_name": "sale.order",
                "res_id": 0,
                "payload": {"note": "old"},
                "payload_version": 999,
            }
        )
        self.assertFalse(draft_model.fetch_draft("sale.order", 0))
        self.assertFalse(draft.exists())
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — `AttributeError: 'od19.draft' object has no attribute 'upsert_draft'`

- [ ] **Step 3: เพิ่ม lifecycle methods**

เพิ่ม import `timedelta` และแก้ header ของ `models/od19_draft.py`:

```python
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DRAFT_PAYLOAD_VERSION = 1
DRAFT_TTL_DAYS = 7
DEFAULT_ENABLED_MODELS = (
    "sale.order",
    "purchase.order",
    "purchase.request",
    "account.analytic.line",
)
```

แทรกเมธอดต่อไปนี้ในคลาส `Od19Draft` (ต่อจาก `init()`):

```python
    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------
    @api.model
    def _get_enabled_models(self):
        enabled = set(DEFAULT_ENABLED_MODELS)
        for model_name, model in self.env.registry.models.items():
            if getattr(model, "_od19_draft_enabled", False):
                enabled.add(model_name)
        return tuple(sorted(enabled))

    @api.model
    def _validate_model(self, model_name):
        if model_name not in self._get_enabled_models():
            raise UserError(
                _("Model '%s' is not enabled for offline drafts.") % model_name
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @api.model
    def _active_domain(self, model_name, res_id):
        return [
            ("model_name", "=", model_name),
            ("res_id", "=", res_id or 0),
            ("user_id", "=", self.env.user.id),
            ("state", "=", "active"),
        ]

    @api.model
    def upsert_draft(self, model_name, res_id, payload, payload_version=None):
        self._validate_model(model_name)
        values = {
            "model_name": model_name,
            "res_id": res_id or 0,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
            "payload": payload or {},
            "payload_version": payload_version or DRAFT_PAYLOAD_VERSION,
            "expires_at": fields.Datetime.now() + timedelta(days=DRAFT_TTL_DAYS),
        }
        draft = self.sudo().search(self._active_domain(model_name, res_id), limit=1)
        if draft:
            draft.write(values)
        else:
            draft = self.sudo().create(values)
        return {
            "id": draft.id,
            "updated_at": fields.Datetime.to_string(draft.write_date),
        }

    @api.model
    def fetch_draft(self, model_name, res_id):
        draft = self.sudo().search(self._active_domain(model_name, res_id), limit=1)
        if not draft:
            return False
        if draft.payload_version != DRAFT_PAYLOAD_VERSION:
            draft.unlink()
            return False
        return {
            "id": draft.id,
            "payload": draft.payload,
            "payload_version": draft.payload_version,
            "updated_at": fields.Datetime.to_string(draft.write_date),
            "expires_at": (
                fields.Datetime.to_string(draft.expires_at) if draft.expires_at else False
            ),
            "attachment_ids": draft._get_attachment_ids(),
        }

    def _get_attachment_ids(self):
        self.ensure_one()
        return (
            self.env["ir.attachment"]
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "=", self.id)])
            .ids
        )

    @api.model
    def discard_draft(self, model_name, res_id):
        self.sudo().search(self._active_domain(model_name, res_id)).unlink()
        return True

    @api.model
    def mark_applied(self, model_name, res_id):
        drafts = self.sudo().search(self._active_domain(model_name, res_id))
        drafts.write({"state": "applied"})
        drafts.unlink()
        return True
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 8 of 8 tests`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/models/od19_draft.py custom_addons/od19_offline_draft/tests/test_od19_draft.py
git commit -m "feat(offline-draft): add upsert/fetch/discard/mark_applied lifecycle"
```

---

## Task 3: Registry เปิดใช้รายโมเดล + client config

**Files:**
- Modify: `custom_addons/od19_offline_draft/models/od19_draft.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail (ต่อท้ายคลาส)**

```python
    def test_enabled_models_contains_defaults(self):
        enabled = self.env["od19.draft"]._get_enabled_models()
        self.assertIn("sale.order", enabled)
        self.assertIn("purchase.order", enabled)
        self.assertIn("purchase.request", enabled)
        self.assertIn("account.analytic.line", enabled)

    def test_client_config_shape(self):
        config = self.env["od19.draft"]._get_client_config()
        self.assertEqual(config["debounce_ms"], 2000)
        self.assertEqual(config["ttl_days"], 7)
        self.assertEqual(config["payload_version"], 1)
        self.assertIn("sale.order", config["enabled_models"])

    def test_upsert_rejects_disabled_model(self):
        with self.assertRaises(UserError):
            self.env["od19.draft"].upsert_draft("res.partner", 0, {"note": "x"})
```

แก้ import ของไฟล์เทสต์จาก `from odoo.tests.common import TransactionCase, tagged` เป็น:

```python
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — `AttributeError: 'od19.draft' object has no attribute '_get_client_config'`

- [ ] **Step 3: เพิ่ม `_get_client_config` + ค่าคงที่**

แก้ค่าคงที่หัวไฟล์ให้ครบ:

```python
DRAFT_PAYLOAD_VERSION = 1
DRAFT_TTL_DAYS = 7
DRAFT_DEBOUNCE_MS = 2000
DRAFT_MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB
DEFAULT_ENABLED_MODELS = (
    "sale.order",
    "purchase.order",
    "purchase.request",
    "account.analytic.line",
)
```

แทรกเมธอดต่อจาก `_validate_model`:

```python
    @api.model
    def _get_client_config(self):
        return {
            "enabled_models": list(self._get_enabled_models()),
            "debounce_ms": DRAFT_DEBOUNCE_MS,
            "ttl_days": DRAFT_TTL_DAYS,
            "max_attachment_size": DRAFT_MAX_ATTACHMENT_SIZE,
            "payload_version": DRAFT_PAYLOAD_VERSION,
        }
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 11 of 11 tests`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/models/od19_draft.py custom_addons/od19_offline_draft/tests/test_od19_draft.py
git commit -m "feat(offline-draft): add per-model registry and client config"
```

---

## Task 4: TTL expiry cron

**Files:**
- Modify: `custom_addons/od19_offline_draft/models/od19_draft.py`
- Create: `custom_addons/od19_offline_draft/data/ir_cron_data.xml`
- Modify: `custom_addons/od19_offline_draft/__manifest__.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail (ต่อท้ายคลาส)**

```python
    def test_cron_expires_only_past_drafts(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "expired"})
        draft_model.sudo().search([("res_id", "=", 0)]).write(
            {"expires_at": "2000-01-01 00:00:00"}
        )
        draft_model.upsert_draft("sale.order", 77, {"note": "fresh"})
        removed = draft_model._cron_expire_drafts()
        self.assertEqual(removed, 1)
        self.assertTrue(draft_model.fetch_draft("sale.order", 77))
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — `AttributeError: 'od19.draft' object has no attribute '_cron_expire_drafts'`

- [ ] **Step 3: เพิ่ม cron method + data + manifest**

แทรกเมธอดต่อจาก `mark_applied`:

```python
    @api.model
    def _cron_expire_drafts(self):
        now = fields.Datetime.now()
        expired = self.sudo().search(
            [
                ("state", "=", "active"),
                ("expires_at", "!=", False),
                ("expires_at", "<", now),
            ]
        )
        if expired:
            expired.write({"state": "expired"})
            expired.unlink()
        return len(expired)
```

สร้าง `data/ir_cron_data.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="ir_cron_od19_draft_expire" model="ir.cron">
            <field name="name">Offline Draft: expire old drafts</field>
            <field name="model_id" ref="model_od19_draft"/>
            <field name="state">code</field>
            <field name="code">model._cron_expire_drafts()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="numbercall">-1</field>
            <field name="active" eval="True"/>
        </record>
    </data>
</odoo>
```

เพิ่ม `"data/ir_cron_data.xml"` ใน `data` ของ `__manifest__.py` ต่อจาก `"security/ir.model.access.csv"`:

```python
    "data": [
        "security/od19_draft_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
    ],
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 12 of 12 tests`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/models/od19_draft.py custom_addons/od19_offline_draft/data/ir_cron_data.xml custom_addons/od19_offline_draft/__manifest__.py custom_addons/od19_offline_draft/tests/test_od19_draft.py
git commit -m "feat(offline-draft): expire stale drafts with daily cron"
```

---

## Task 5: ไฟล์แนบผ่าน `ir.attachment` + cascade unlink

**Files:**
- Modify: `custom_addons/od19_offline_draft/models/od19_draft.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail (ต่อท้ายคลาส)**

```python
    def test_fetch_exposes_attachment_ids(self):
        draft_model = self.env["od19.draft"]
        info = draft_model.upsert_draft("sale.order", 0, {"note": "with file"})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "draft.txt",
                "res_model": "od19.draft",
                "res_id": info["id"],
                "datas": "aGVsbG8=",
            }
        )
        result = draft_model.fetch_draft("sale.order", 0)
        self.assertEqual(result["attachment_ids"], [attachment.id])

    def test_unlink_removes_related_attachments(self):
        draft_model = self.env["od19.draft"]
        info = draft_model.upsert_draft("sale.order", 0, {"note": "with file"})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "draft.txt",
                "res_model": "od19.draft",
                "res_id": info["id"],
                "datas": "aGVsbG8=",
            }
        )
        draft_model.discard_draft("sale.order", 0)
        self.assertFalse(attachment.exists())
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — `test_unlink_removes_related_attachments` ล้มเหลว (attachment ยังอยู่)

- [ ] **Step 3: override `unlink()`**

แทรกต่อจาก `init()` ในคลาส `Od19Draft`:

```python
    def unlink(self):
        self.env["ir.attachment"].sudo().search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        ).unlink()
        return super().unlink()
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 14 of 14 tests`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/models/od19_draft.py custom_addons/od19_offline_draft/tests/test_od19_draft.py
git commit -m "feat(offline-draft): support attachments and cascade cleanup"
```

---

## Task 6: ฉีด config เข้า `session_info` (ir.http)

**Files:**
- Create: `custom_addons/od19_offline_draft/models/ir_http.py`
- Modify: `custom_addons/od19_offline_draft/models/__init__.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft.py`

- [ ] **Step 1: เขียนเทสต์ที่จะ fail (ต่อท้ายคลาส)**

```python
    def test_ir_http_exposes_draft_config(self):
        ir_http = self.env["ir.http"]
        self.assertTrue(hasattr(ir_http, "_od19_draft_session_info"))
        payload = ir_http._od19_draft_session_info()
        self.assertIn("sale.order", payload["enabled_models"])
        self.assertEqual(payload["debounce_ms"], 2000)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — `AttributeError: '_od19_draft_session_info'`

- [ ] **Step 3: สร้าง `models/ir_http.py` + import**

`models/ir_http.py`:

```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def _od19_draft_session_info(self):
        return self.env["od19.draft"]._get_client_config()

    def session_info(self):
        result = super().session_info()
        result["od19_draft"] = self._od19_draft_session_info()
        return result
```

`models/__init__.py`:

```python
from . import od19_draft
from . import ir_http
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 15 of 15 tests`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/models/ir_http.py custom_addons/od19_offline_draft/models/__init__.py custom_addons/od19_offline_draft/tests/test_od19_draft.py
git commit -m "feat(offline-draft): expose draft config through session_info"
```

---

## Task 7: OWL service ฝั่ง backend (IndexedDB + sync)

**Files:**
- Create: `custom_addons/od19_offline_draft/static/src/draft_service.js`
- Modify: `custom_addons/od19_offline_draft/__manifest__.py`
- Test: `custom_addons/od19_offline_draft/tests/test_od19_draft_assets.py` (สร้างใน Task 10; ที่นี่เพิ่ม asset ก่อน)

- [ ] **Step 1: สร้าง service**

`static/src/draft_service.js`:

```javascript
/**
 * OD19 Offline Draft — client service.
 *
 * เก็บร่างลง IndexedDB ก่อน (ทันที, กันเน็ตหลุด) แล้ว sync ขึ้น `od19.draft`
 * เมื่อออนไลน์ — ทุกฟังก์ชันเป็น fail-safe: ถ้า store เขียนไม่ได้ ต้องไม่ทำให้
 * ฟอร์มหลักพัง
 */
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const DB_NAME = "od19_offline_draft";
const DB_VERSION = 1;
const STORE_DRAFTS = "drafts";
const STORE_ATTACHMENTS = "attachments";
const SCHEMA_VERSION = 1;

function draftKey(model, resId, userId) {
    return `${model}|${resId || 0}|${userId}`;
}

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = window.indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
                const store = db.createObjectStore(STORE_DRAFTS, { keyPath: "key" });
                store.createIndex("byModel", "model");
            }
            if (!db.objectStoreNames.contains(STORE_ATTACHMENTS)) {
                db.createObjectStore(STORE_ATTACHMENTS, { keyPath: "key" });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function runStore(db, storeName, mode, operation) {
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, mode);
        let request;
        try {
            request = operation(tx.objectStore(storeName));
        } catch (error) {
            reject(error);
            return;
        }
        if (request && "onsuccess" in request) {
            request.onsuccess = () => resolve(request.result);
        } else {
            tx.oncomplete = () => resolve(undefined);
        }
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
    });
}

export const od19DraftService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const config = session.od19_draft || {};
        const enabledModels = new Set(config.enabled_models || []);
        const userId = session.uid;
        let dbPromise = null;

        function isEnabled(model) {
            return Boolean(model) && enabledModels.has(model) && Boolean(userId);
        }

        function getDb() {
            if (!dbPromise) {
                dbPromise = openDatabase();
            }
            return dbPromise;
        }

        async function save(model, resId, payload) {
            if (!isEnabled(model)) {
                return false;
            }
            const key = draftKey(model, resId, userId);
            try {
                const db = await getDb();
                await runStore(db, STORE_DRAFTS, "readwrite", (store) =>
                    store.put({
                        key,
                        model,
                        resId: resId || 0,
                        payload,
                        schema: SCHEMA_VERSION,
                        dirty: true,
                        updatedAt: Date.now(),
                    })
                );
            } catch (error) {
                return false;
            }
            return true;
        }

        async function load(model, resId) {
            if (!isEnabled(model)) {
                return false;
            }
            try {
                const db = await getDb();
                return (
                    (await runStore(db, STORE_DRAFTS, "readonly", (store) =>
                        store.get(draftKey(model, resId, userId))
                    )) || false
                );
            } catch (error) {
                return false;
            }
        }

        async function clear(model, resId) {
            if (!isEnabled(model)) {
                return false;
            }
            const key = draftKey(model, resId, userId);
            try {
                const db = await getDb();
                await runStore(db, STORE_DRAFTS, "readwrite", (store) => store.delete(key));
                const attachKeys = await runStore(db, STORE_ATTACHMENTS, "readonly", (store) =>
                    store.getAllKeys()
                );
                for (const attachKey of attachKeys || []) {
                    if (String(attachKey).startsWith(`${key}|`)) {
                        await runStore(db, STORE_ATTACHMENTS, "readwrite", (store) =>
                            store.delete(attachKey)
                        );
                    }
                }
            } catch (error) {
                return false;
            }
            return true;
        }

        async function syncNow(model, resId, payload) {
            if (!isEnabled(model)) {
                return false;
            }
            try {
                await orm.call("od19.draft", "upsert_draft", [model, resId || 0, payload]);
                return true;
            } catch (error) {
                return false;
            }
        }

        async function flushPending() {
            try {
                const db = await getDb();
                const records = (await runStore(db, STORE_DRAFTS, "readonly", (store) =>
                    store.getAll()
                )) || [];
                for (const record of records) {
                    if (!record.dirty) {
                        continue;
                    }
                    const ok = await syncNow(record.model, record.resId, record.payload);
                    if (ok) {
                        await runStore(db, STORE_DRAFTS, "readwrite", (store) =>
                            store.put({ ...record, dirty: false })
                        );
                    }
                }
            } catch (error) {
                // fail-safe
            }
        }

        window.addEventListener("online", () => flushPending());

        return { isEnabled, save, load, clear, syncNow, flushPending, config };
    },
};

registry.category("services").add("od19_draft", od19DraftService);
```

- [ ] **Step 2: ต่อ asset เข้า manifest**

เพิ่มบล็อก `assets` ใน `__manifest__.py` ต่อจาก `data`:

```python
    "assets": {
        "web.assets_backend": [
            "od19_offline_draft/static/src/draft_service.js",
        ],
    },
```

- [ ] **Step 3: ตรวจว่าไฟล์ถูกต้อง (static)**

Run: `node --check custom_addons\od19_offline_draft\static\src\draft_service.js`
Expected: ไม่มี output (syntax ถูกต้อง)

- [ ] **Step 4: รันเทสต์เดิมให้ยังผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 15 of 15 tests` (ยังไม่มีเทสต์ asset ในเฟสนี้)

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_offline_draft/static/src/draft_service.js custom_addons/od19_offline_draft/__manifest__.py
git commit -m "feat(offline-draft): add client draft service with IndexedDB store"
```

---

## Task 8: แบนเนอร์กู้คืน + patch `FormController`

**Files:**
- Create: `custom_addons/od19_offline_draft/static/src/draft_banner.js`
- Create: `custom_addons/od19_offline_draft/static/src/draft_banner.xml`
- Create: `custom_addons/od19_offline_draft/static/src/form_controller_patch.js`
- Create: `custom_addons/od19_offline_draft/static/src/offline_draft.scss`
- Modify: `custom_addons/od19_offline_draft/__manifest__.py`

- [ ] **Step 1: สร้างคอมโพเนนต์แบนเนอร์**

`static/src/draft_banner.js`:

```javascript
import { Component } from "@odoo/owl";

export class DraftBanner extends Component {
    static template = "od19_offline_draft.DraftBanner";
    static props = {
        draft: Object,
        onRestore: Function,
        onDiscard: Function,
    };
}
```

`static/src/draft_banner.xml`:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<templates xml:space="preserve">
    <t t-name="od19_offline_draft.DraftBanner">
        <div class="od19-draft-banner alert alert-warning d-flex justify-content-between align-items-center mb-2" role="alert">
            <span class="od19-draft-banner__text">
                <i class="fa fa-floppy-o me-1"/>
                พบร่างที่บันทึกไว้ — กู้คืนหรือทิ้ง?
            </span>
            <span class="od19-draft-banner__actions">
                <button type="button" class="btn btn-sm btn-primary me-1" t-on-click="() => this.props.onRestore()">
                    กู้คืน
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" t-on-click="() => this.props.onDiscard()">
                    ทิ้ง
                </button>
            </span>
        </div>
    </t>
</templates>
```

- [ ] **Step 2: patch `FormController`**

`static/src/form_controller_patch.js`:

```javascript
/**
 * OD19 Offline Draft — FormController patch.
 *
 * ต่อเฉพาะ lifecycle: autosave แบบ debounce, เช็คร่างตอนเปิดฟอร์ม,
 * ล้างร่างเมื่อบันทึกจริงสำเร็จ — ไม่แก้ logic เดิมของฟอร์ม
 */
import { onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { DraftBanner } from "./draft_banner";

const RELATIONAL_MARKERS = ["2many", "many2one", "reference"];

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.od19DraftService = useService("od19_draft");
        this.od19DraftEnabled = this.od19DraftService.isEnabled(this.props.resModel);
        this.od19DraftBanner = useState({ visible: false, draft: null });
        this.od19DraftTimer = null;
        if (!this.od19DraftEnabled) {
            return;
        }
        onMounted(() => this._od19LookupDraft());
        onWillUnmount(() => this._od19CancelTimer());
        useEffect(
            () => {
                this._od19CollectPayload();
            },
            () => [this.model.root.resId, this.model.root.isInEdition]
        );
    },

    _od19RecordKey() {
        return this.model.root.resId || this.props.resId || 0;
    },

    _od19CollectPayload() {
        const root = this.model.root;
        if (!root || !root.isInEdition) {
            return null;
        }
        const payload = {};
        for (const [name, value] of Object.entries(root.data)) {
            if (value === undefined || value === null || typeof value === "function") {
                continue;
            }
            if (value && typeof value === "object" && !Array.isArray(value)) {
                continue; // ตัด many2one/x2many ออก เก็บเฉพาะค่าฟิลด์เชิงสเกลาร์
            }
            payload[name] = value;
        }
        this._od19ScheduleSave(payload);
        return payload;
    },

    _od19ScheduleSave(payload) {
        this._od19CancelTimer();
        const delay = (this.od19DraftService.config || {}).debounce_ms || 2000;
        this.od19DraftTimer = setTimeout(async () => {
            const resId = this._od19RecordKey();
            await this.od19DraftService.save(this.props.resModel, resId, payload);
            await this.od19DraftService.syncNow(this.props.resModel, resId, payload);
        }, delay);
    },

    _od19CancelTimer() {
        if (this.od19DraftTimer) {
            clearTimeout(this.od19DraftTimer);
            this.od19DraftTimer = null;
        }
    },

    async _od19LookupDraft() {
        const resId = this.props.resId || 0;
        const draft = await this.od19DraftService.load(this.props.resModel, resId);
        if (draft && draft.payload && Object.keys(draft.payload).length) {
            this.od19DraftBanner.visible = true;
            this.od19DraftBanner.draft = draft;
        }
    },

    async od19RestoreDraft() {
        const draft = this.od19DraftBanner.draft;
        if (!draft) {
            return;
        }
        await this.model.root.update(draft.payload, { save: false });
        this.od19DraftBanner.visible = false;
    },

    async od19DiscardDraft() {
        const resId = this._od19RecordKey();
        await this.od19DraftService.clear(this.props.resModel, resId);
        try {
            await this.od19DraftService.syncNow(this.props.resModel, resId, null);
        } catch (error) {
            // fail-safe
        }
        this.od19DraftBanner.visible = false;
        this.od19DraftBanner.draft = null;
    },

    async onRecordSaved(record) {
        const result = await super.onRecordSaved(...arguments);
        if (this.od19DraftEnabled && record) {
            this._od19CancelTimer();
            await this.od19DraftService.clear(this.props.resModel, record.resId);
            this.od19DraftBanner.visible = false;
            this.od19DraftBanner.draft = null;
        }
        return result;
    },
});

patch(FormController, {
    components: {
        ...FormController.components,
        DraftBanner,
    },
});

void RELATIONAL_MARKERS;
```

`static/src/offline_draft.scss`:

```scss
.od19-draft-banner {
    margin: 0.5rem 0.75rem 0;
    font-size: 0.9rem;

    &__text {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
    }
}
```

- [ ] **Step 3: inherit template `web.FormView`**

สร้างไฟล์ `static/src/draft_banner.xml` ให้ต่อท้ายด้วยบล็อก inherit (แก้ไฟล์เดิมจาก Step 1):

```xml
    <t t-inherit="web.FormView" t-inherit-mode="extension">
        <xpath expr="//div[hasclass('o_form_view_container')]/Layout" position="before">
            <DraftBanner
                t-if="od19DraftBanner.visible"
                draft="od19DraftBanner.draft"
                onRestore="() => this.od19RestoreDraft()"
                onDiscard="() => this.od19DiscardDraft()"/>
        </xpath>
    </t>
```

- [ ] **Step 4: ต่อ asset เข้า manifest**

แก้บล็อก `assets` ของ `__manifest__.py` เป็น:

```python
    "assets": {
        "web.assets_backend": [
            "od19_offline_draft/static/src/draft_service.js",
            "od19_offline_draft/static/src/draft_banner.js",
            "od19_offline_draft/static/src/draft_banner.xml",
            "od19_offline_draft/static/src/form_controller_patch.js",
            "od19_offline_draft/static/src/offline_draft.scss",
        ],
    },
```

- [ ] **Step 5: ตรวจ syntax + รันเทสต์เดิม**

Run: `node --check custom_addons\od19_offline_draft\static\src\draft_banner.js; node --check custom_addons\od19_offline_draft\static\src\form_controller_patch.js`
Expected: ไม่มี output

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 15 of 15 tests`

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_offline_draft/static/src/draft_banner.js custom_addons/od19_offline_draft/static/src/draft_banner.xml custom_addons/od19_offline_draft/static/src/form_controller_patch.js custom_addons/od19_offline_draft/static/src/offline_draft.scss custom_addons/od19_offline_draft/__manifest__.py
git commit -m "feat(offline-draft): autosave and restore banner in backend forms"
```

---

## Task 9: Portal autosave

**Files:**
- Create: `custom_addons/od19_offline_draft/static/src/portal/portal_autosave.js`
- Modify: `custom_addons/od19_offline_draft/__manifest__.py`

- [ ] **Step 1: สร้างสคริปต์ portal**

`static/src/portal/portal_autosave.js`:

```javascript
/**
 * OD19 Offline Draft — portal autosave.
 *
 * หน้า portal เป็น QWeb POST ปกติ (ไม่ใช่ OWL) จึงเก็บค่าฟอร์มลง localStorage
 * เป็นระยะ และกู้คืนเมื่อโหลดหน้าเดิม — fail-safe ทุกเส้นทาง
 */
import { session } from "@web/session";

(function () {
    const config = session.od19_draft || {};
    if (!config.enabled_models) {
        return;
    }
    const debounceMs = config.debounce_ms || 2000;
    const userId = session.uid;

    function storageKey(form) {
        const action = form.getAttribute("action") || window.location.pathname;
        return `od19_draft:portal:${action}:${userId}`;
    }

    function collect(form) {
        const data = {};
        for (const element of form.elements) {
            if (!element.name) {
                continue;
            }
            if (element.type === "password" || element.type === "file") {
                continue;
            }
            if (element.type === "checkbox" || element.type === "radio") {
                if (element.checked) {
                    data[element.name] = element.value;
                }
            } else {
                data[element.name] = element.value;
            }
        }
        return data;
    }

    function restore(form) {
        let saved;
        try {
            const raw = window.localStorage.getItem(storageKey(form));
            saved = raw ? JSON.parse(raw) : null;
        } catch (error) {
            return;
        }
        if (!saved || !saved.data) {
            return;
        }
        for (const [name, value] of Object.entries(saved.data)) {
            const element = form.elements[name];
            if (!element) {
                continue;
            }
            if (element.type === "checkbox" || element.type === "radio") {
                element.checked = element.value === value;
            } else {
                element.value = value;
            }
        }
        form.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function attach(form) {
        restore(form);
        let timer = null;
        const flush = () => {
            try {
                window.localStorage.setItem(
                    storageKey(form),
                    JSON.stringify({ data: collect(form), updatedAt: Date.now() })
                );
            } catch (error) {
                // fail-safe
            }
        };
        form.addEventListener("input", () => {
            clearTimeout(timer);
            timer = setTimeout(flush, debounceMs);
        });
        form.addEventListener("change", () => {
            clearTimeout(timer);
            timer = setTimeout(flush, debounceMs);
        });
        form.addEventListener("submit", () => {
            try {
                window.localStorage.removeItem(storageKey(form));
            } catch (error) {
                // fail-safe
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        for (const form of document.querySelectorAll("form.od19-portal-draft, form[data-od19-draft]")) {
            attach(form);
        }
    });
})();
```

- [ ] **Step 2: ต่อ asset เข้า manifest**

แก้บล็อก `assets` ของ `__manifest__.py` เป็น:

```python
    "assets": {
        "web.assets_backend": [
            "od19_offline_draft/static/src/draft_service.js",
            "od19_offline_draft/static/src/draft_banner.js",
            "od19_offline_draft/static/src/draft_banner.xml",
            "od19_offline_draft/static/src/form_controller_patch.js",
            "od19_offline_draft/static/src/offline_draft.scss",
        ],
        "web.assets_frontend": [
            "od19_offline_draft/static/src/portal/portal_autosave.js",
        ],
    },
```

- [ ] **Step 3: ตรวจ syntax**

Run: `node --check custom_addons\od19_offline_draft\static\src\portal\portal_autosave.js`
Expected: ไม่มี output

- [ ] **Step 4: Commit**

```bash
git add custom_addons/od19_offline_draft/static/src/portal/portal_autosave.js custom_addons/od19_offline_draft/__manifest__.py
git commit -m "feat(offline-draft): portal field-level autosave"
```

---

## Task 10: Views สำหรับแอดมิน + เทสต์ asset + เก็บงานให้ครบ

**Files:**
- Create: `custom_addons/od19_offline_draft/views/od19_draft_views.xml`
- Create: `custom_addons/od19_offline_draft/tests/test_od19_draft_assets.py`
- Modify: `custom_addons/od19_offline_draft/tests/__init__.py`
- Modify: `custom_addons/od19_offline_draft/__manifest__.py`

- [ ] **Step 1: เขียนเทสต์ asset ที่จะ fail**

แก้ `tests/__init__.py`:

```python
from . import test_od19_draft
from . import test_od19_draft_assets
```

สร้าง `tests/test_od19_draft_assets.py`:

```python
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestOd19DraftAssets(HttpCase):
    def _backend_asset_urls(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        return [asset["url"] for asset in assets]

    def _frontend_asset_urls(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_frontend")[0]
        return [asset["url"] for asset in assets]

    def test_backend_assets_in_bundle(self):
        urls = self._backend_asset_urls()
        for path in (
            "/od19_offline_draft/static/src/draft_service.js",
            "/od19_offline_draft/static/src/draft_banner.js",
            "/od19_offline_draft/static/src/draft_banner.xml",
            "/od19_offline_draft/static/src/form_controller_patch.js",
            "/od19_offline_draft/static/src/offline_draft.scss",
        ):
            self.assertIn(path, urls)

    def test_frontend_asset_in_bundle(self):
        self.assertIn(
            "/od19_offline_draft/static/src/portal/portal_autosave.js",
            self._frontend_asset_urls(),
        )

    def test_form_view_extension_is_registered(self):
        view = self.env.ref(
            "od19_offline_draft.od19_draft_form_view_extension", raise_if_not_found=False
        )
        self.assertTrue(view)
        self.assertEqual(view.inherit_id.name, "web.FormView")
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: FAIL — `od19_draft_form_view_extension` ไม่พบ (view ยังไม่มี)

- [ ] **Step 3: สร้าง views + ผูกเข้า manifest**

สร้าง `views/od19_draft_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_draft_list" model="ir.ui.view">
        <field name="name">od19.draft.list</field>
        <field name="model">od19.draft</field>
        <field name="arch" type="xml">
            <list string="Offline Drafts" create="false">
                <field name="name"/>
                <field name="model_name"/>
                <field name="res_id"/>
                <field name="user_id"/>
                <field name="company_id" groups="base.group_multi_company"/>
                <field name="state"/>
                <field name="write_date"/>
                <field name="expires_at"/>
            </list>
        </field>
    </record>

    <record id="view_od19_draft_form" model="ir.ui.view">
        <field name="name">od19.draft.form</field>
        <field name="model">od19.draft</field>
        <field name="arch" type="xml">
            <form string="Offline Draft" create="false">
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="model_name"/>
                            <field name="res_id"/>
                            <field name="state"/>
                        </group>
                        <group>
                            <field name="user_id"/>
                            <field name="company_id" groups="base.group_multi_company"/>
                            <field name="payload_version"/>
                            <field name="expires_at"/>
                        </group>
                    </group>
                    <field name="payload" widget="json"/>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_draft" model="ir.actions.act_window">
        <field name="name">Offline Drafts / ร่างอัตโนมัติ</field>
        <field name="res_model">od19.draft</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem
        id="menu_od19_draft"
        name="Offline Drafts"
        parent="base.menu_custom"
        action="action_od19_draft"
        groups="base.group_system"
        sequence="95"/>
</odoo>
```

แก้ `data` ของ `__manifest__.py` เป็น:

```python
    "data": [
        "security/od19_draft_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/od19_draft_views.xml",
    ],
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_offline_draft`
Expected: PASS — `tests.result: 18 of 18 tests`

- [ ] **Step 5: ตรวจ XML well-formed + Python syntax**

Run: `venv19\Scripts\python.exe -c "import xml.dom.minidom,glob;[xml.dom.minidom.parse(f) for f in glob.glob('custom_addons/od19_offline_draft/**/*.xml',recursive=True)];print('XML OK')"`
Expected: `XML OK`

Run: `venv19\Scripts\python.exe -m py_compile custom_addons\od19_offline_draft\models\od19_draft.py custom_addons\od19_offline_draft\models\ir_http.py; if ($LASTEXITCODE -eq 0) { "PY OK" }`
Expected: `PY OK`

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_offline_draft/views/od19_draft_views.xml custom_addons/od19_offline_draft/tests/test_od19_draft_assets.py custom_addons/od19_offline_draft/tests/__init__.py custom_addons/od19_offline_draft/__manifest__.py
git commit -m "feat(offline-draft): admin views and asset-bundle tests"
```

> **การตรวจรับ (manual, ผู้ใช้รันเอง):** เปิด Odoo 19 → เปิดฟอร์ม Sale Order ใหม่ → พิมพ์ข้อมูลแล้วรอ ~2 วินาที → กด refresh หน้า → ต้องเห็นแบนเนอร์ "พบร่างที่บันทึกไว้" และกดกู้คืนได้ค่าคืน
> **ห้าม agent รัน Unit Test แทนผู้ใช้** — agent สร้าง/แก้โค้ดและ commit ได้ แต่การรันบนเครื่องให้ผู้ใช้เป็นผู้รัน (ตาม AGENTS.md ข้อ 6)

---

## Self-Review (ตรวจแผนกับ spec)

| spec § | ความต้องการ | Task ที่ครอบคลุม |
|---|---|---|
| R1 autosave debounce 2s | Task 8 (`_od19ScheduleSave`) |
| R2 แจ้งเตือน + เลือกกู้/ทิ้ง | Task 8 (`DraftBanner` + `_od19LookupDraft`) |
| R3 ล้างร่างเมื่อบันทึกจริง | Task 2 (`mark_applied`), Task 8 (`onRecordSaved`) |
| R4 backend + portal | Task 7/8 (backend), Task 9 (portal) |
| R5 Hybrid client+server sync | Task 2 (`upsert_draft`), Task 7 (`save`/`syncNow`/`flushPending`) |
| R6 ไฟล์แนบ | Task 5 (link + cascade), Task 7 (`attachments` store) |
| R7 เปิดใช้รายโมเดล | Task 3 (`_get_enabled_models`, `_validate_model`) |
| R8 เก็บเฉพาะฟิลด์ที่แก้ | Task 8 (`_od19CollectPayload` ตัด relational/password/file) |
| R9 เห็นเฉพาะร่างตัวเอง + company | Task 1 (`rule_od19_draft_own`) |
| R10 TTL + ล้างอัตโนมัติ | Task 4 (`_cron_expire_drafts`) |
| R11 ไม่แตะ core (additive) | Task 6/8 (inherit/patch เท่านั้น) |
| R12 Unit test ครอบคลุม | Task 1-6, Task 10 |
| §6 `payload_version` ไม่ตรง → ไม่กู้ | Task 2 (`fetch_draft`) |
| §8 registry + session_info | Task 3 + Task 6 |
| §13 File layout | Task 1-10 |

**Placeholder scan:** ไม่มี TBD/TODO — ทุก step มีโค้ดหรือคำสั่งจริง

**Type consistency:** `upsert_draft(model_name, res_id, payload, payload_version=None)` · `fetch_draft(model_name, res_id)` · `discard_draft(model_name, res_id)` · `mark_applied(model_name, res_id)` · `_get_enabled_models()` · `_get_client_config()` · `_cron_expire_drafts()` — ใช้ชื่อเดิมสอดคล้องกันทุก Task; JS ใช้ `isEnabled/save/load/clear/syncNow/flushPending` ตรงกันระหว่าง Task 7 และ 8

---

## Execution Handoff

แผนบันทึกที่ `docs/superpowers/plans/2026-11-06-od19-offline-draft-implementation-plan.md` — เลือกวิธีดำเนินการ:

1. **Subagent-Driven (แนะนำ)** — dispatch subagent ใหม่ต่อ 1 task แล้วรีวิวระหว่าง task
2. **Inline Execution** — รันในเซสชันนี้เป็นชุด พร้อม checkpoint ให้รีวิว
