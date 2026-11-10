# AI Coverage (od19_ai_assistant) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ยกระดับผู้ช่วย AI (`od19_ai_assistant`) จากเครื่องมือเฉพาะ 11 ตัว ให้ครอบคลุมทุกโดเมนของ Odoo ผ่าน Generic Explorer + Progressive Disclosure + Capability Mode (อ่านเท่านั้น / อ่าน+ร่าง) + Audit โดยไม่กระทบประสิทธิภาพระบบ

**Architecture:** สถาปัตยกรรมแบบมีชั้น (Hybrid) — ชั้น 0 Capability Index (สารบัญสั้นใน prompt) → ชั้น 1 Generic Explorer (`list_models` / `describe_model` / `search_records` / `aggregate_records`) → ชั้น 2 Curated Fast-path (เครื่องมือเดิม 11 ตัว) → ชั้น 3 External Providers (โครง registry, ปิดดีฟอลต์) → ชั้น 4 Capability Mode gate + Performance Guards. ทุกอย่างเป็น additive ภายใต้โมดูลเดิม ไม่แตะ Odoo core และใช้สิทธิ์ผู้ใช้จริง (ไม่ `sudo()`)

**Tech Stack:** Odoo 19 CE · Python ORM (`odoo.fields.Domain`, `_read_group`, `tools.ormcache`) · `ir.model.access._get_allowed_models` · OWL 2 (`Component`, `rpc`, SSE ผ่าน `fetch` + `TextDecoder`) · `TransactionCase` / `HttpCase` + `unittest.mock.patch`

**อ้างอิง:** Spec `docs/superpowers/specs/2026-11-10-od19-ai-assistant-coverage-design.md` (§5–§19) · AGENTS.md (ห้ามแตะ core · Conventional Commits · ห้าม `git add -A` · รัน Unit Test บน `odoo19_pdev`)

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_ai_assistant/lib/orm_guard.py` | ตรวจ domain/field/limit/aggregate ให้ปลอดภัย | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/od19_ai_tool.py` | registry รวม curated + generic + meta + draft, `execute` + audit | แก้ |
| `custom_addons/od19_ai_assistant/models/od19_ai_tool_generic.py` | Generic Explorer (ชั้น 1) + cache metadata | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/od19_ai_tool_index.py` | Capability Index + `tool_help` (ชั้น 0) | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/od19_ai_tool_log.py` | โมเดล audit `od19.ai.tool.log` | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/od19_ai_capability.py` | gate โหมด + draft + audit + tool `draft_record` | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/od19_ai_provider.py` | registry ผู้ให้บริการภายนอก (โครง) | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/res_users.py` | ฟิลด์ `od19_ai_capability_mode` รายผู้ใช้ | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/od19_ai_chat.py` | ใช้ `prompt_index()` แทน catalog เต็ม | แก้ |
| `custom_addons/od19_ai_assistant/models/res_config_settings.py` | เพิ่มฟิลด์โหมดดีฟอลต์ระบบ | แก้ |
| `custom_addons/od19_ai_assistant/models/__init__.py` | import ไฟล์โมเดลใหม่ | แก้ |
| `custom_addons/od19_ai_assistant/security/ir.model.access.csv` | สิทธิ์ `od19.ai.tool.log` | แก้ |
| `custom_addons/od19_ai_assistant/security/od19_ai_security.xml` | record rule ของ log | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/views/res_config_settings_views.xml` | ฟิลด์โหมด (settings + res.users) | แก้ |
| `custom_addons/od19_ai_assistant/controllers/main.py` | SSE `draft` event + route ยืนยัน draft | แก้ |
| `custom_addons/od19_ai_assistant/static/src/js/od19_ai_chat.js` | การ์ดร่าง + `confirmDraft` | แก้ |
| `custom_addons/od19_ai_assistant/static/src/xml/od19_ai_chat.xml` | การ์ดร่าง (UI) | แก้ |
| `custom_addons/od19_ai_assistant/__manifest__.py` | เพิ่ม `security/od19_ai_security.xml` + bump version | แก้ |
| `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py` | เทสต์ครอบคลุมทุกส่วนใหม่ | แก้ |

---

## Decisions (locked — อย่าเปลี่ยนระหว่างลงมือ)

1. **ไม่แตะ `prompt_catalog()` และ `_safe_limit()` เดิม** — เทสต์เดิม (`test_tool_catalog_lists_installed_tools`, `test_safe_limit_is_clamped`, `test_system_prompt_includes_tool_catalog`) ยังต้องผ่าน → คงทั้งสองเมธอดไว้ (ให้ `prompt_catalog` ใช้ `available_tools()` และ `_safe_limit` delegate ไปที่ `orm_guard.safe_limit`)
2. **`_tool_definitions()` = curated 11 ตัวเท่านั้น** — เทสต์เดิม `test_extended_tool_catalog_is_declared` อ้างถึงเมธอดนี้โดยตรง
3. **ACL `ir.model`** — ผู้ใช้ทั่วไป (`base.group_user`) ไม่มีสิทธิ์ read `ir.model` จึง **ห้ามใช้** `search` บน `ir.model` ให้ใช้ `self.env["ir.model.access"]._get_allowed_models("read")` (คืน `frozenset` ชื่อโมเดล, มี ormcache `('self.env.uid','mode')`) แล้ว intersection กับ `self.env` (ยืนยันจาก `odoo/addons/base/models/ir_model.py:2157`)
4. **Map `relation` → `comodel_name`** — Odoo 19 ไม่มี attribute `relation` บน field (spec §6.1 เขียน `relation`); field ที่เป็นความสัมพันธ์ใช้ `field.comodel_name`
5. **Field description** — ใช้ attribute ตรงจาก `model._fields[name]` (`type`, `string`, `required`, `comodel_name`, `store`, `compute`) ซึ่งเป็น registry-level ไม่ยิง query และไม่ติด ACL
6. **`DEFAULTS["timeout"]` คงเป็น 60** — spec §16 ระบุ timeout ปรับผ่าน `res.config.settings`; **ห้ามเปลี่ยนค่าดีฟอลต์** เพราะ `test_config_falls_back_to_defaults` assert `timeout == 60`. ผู้ใช้ตั้ง 180s ได้เองผ่าน Settings
7. **Draft whitelist อ่านจาก `ir.config_parameter`** `od19_ai.draft_models` (คั่นด้วย comma) และ fallback เป็นค่าคงที่ → ทำให้เทสต์กำหนด whitelist ได้โดยไม่พึ่งโมดูลภายนอก (sale/account ฯลฯ ที่อาจไม่ติดตั้ง)
8. **Draft ยืนยัน 2 จังหวะ** — เครื่องมือ `draft_record` **ไม่สร้าง** record; มันคืน sentinel `__OD19_DRAFT__{json}` ให้ controller แสดงการ์ด แล้วผู้ใช้กด "ยืนยัน" จึงเรียก route `/od19_ai/draft/confirm` → `create_draft()` สร้างจริง (สิทธิ์ผู้ใช้, บังคับ draft)
9. **ห้าม post/confirm/pay/approve เด็ดขาด** — `create_draft()` บังคับ `state="draft"` เมื่อโมเดลมี state และปฏิเสธฟิลด์ใน `FORBIDDEN_FIELDS`
10. **ไม่มีงานตอน idle** — ไม่เพิ่ม cron/worker/`ir.cron` ใด ๆ

## Test-Run Convention

- รัน Unit Test (ตาม §14 ของ spec): `.\run-tests.ps1 -Module od19_ai_assistant` → เป้าหมาย **0 failed / 0 error(s)**
- ตรวจไวยากรณ์เร็วระหว่างทาง: `venv19\Scripts\python.exe -m py_compile <path>` → ไม่มี output
- ตรวจ XML well-formed: `venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('<path>')"` → ไม่มี output
- ห้าม commit จนกว่าเทสต์ทั้งโมดูลจะผ่าน (AGENTS.md §3)

---

## Task 1: Domain/Field/Limit Guard (`lib/orm_guard.py`)

**Files:**
- Create: `custom_addons/od19_ai_assistant/lib/orm_guard.py`
- Modify: `custom_addons/od19_ai_assistant/lib/__init__.py`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py` (เพิ่มคลาสใหม่ท้ายไฟล์)

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestOrmGuard(TransactionCase):
    def _guard(self):
        from odoo.addons.od19_ai_assistant.lib import orm_guard

        return orm_guard

    def test_safe_limit_caps_and_defaults(self):
        guard = self._guard()
        self.assertEqual(guard.safe_limit(100), 20)
        self.assertEqual(guard.safe_limit(0), 1)
        self.assertEqual(guard.safe_limit("bad"), 5)
        self.assertEqual(guard.safe_limit(None, default=7), 7)

    def test_safe_offset_never_negative(self):
        guard = self._guard()
        self.assertEqual(guard.safe_offset(-5), 0)
        self.assertEqual(guard.safe_offset("3"), 3)
        self.assertEqual(guard.safe_offset("bad"), 0)

    def test_validate_fields_rejects_unknown_field(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_fields(self.env, "res.partner", ["no_such_field"])

    def test_validate_fields_defaults_to_display_name(self):
        guard = self._guard()
        self.assertEqual(
            guard.validate_fields(self.env, "res.partner", None), ["display_name"]
        )

    def test_validate_domain_accepts_safe_operator(self):
        guard = self._guard()
        domain = guard.validate_domain(
            self.env, "res.partner", [["name", "ilike", "abc"]]
        )
        self.env["res.partner"].create({"name": "abc co"})
        self.assertTrue(self.env["res.partner"].search_count(domain))

    def test_validate_domain_rejects_unknown_operator(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(
                self.env, "res.partner", [["name", "regex", "abc"]]
            )

    def test_validate_domain_rejects_unknown_field(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(
                self.env, "res.partner", [["nope", "=", 1]]
            )

    def test_validate_domain_accepts_dotted_path(self):
        guard = self._guard()
        domain = guard.validate_domain(
            self.env, "res.partner", [["user_ids.login", "ilike", "admin"]]
        )
        self.assertTrue(self.env["res.partner"].search_count(domain))

    def test_validate_domain_rejects_non_stored_compute(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(
                self.env, "res.partner", [["display_name", "=", "x"]]
            )

    def test_check_model_rejects_missing_model(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.check_model(self.env, "does.not.exist")

    def test_validate_order_rejects_unknown_field(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_order(self.env, "res.partner", "nope desc")

    def test_validate_aggregates_rejects_unknown_function(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_aggregates(self.env, "res.partner", ["id:median"])

    def test_validate_groupby_rejects_bad_granularity(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_groupby(
                self.env, "res.partner", ["create_date:fortnight"]
            )
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — `ModuleNotFoundError: ... lib.orm_guard` (หรือ `AttributeError`)

- [ ] **Step 3: เขียน implementation**

สร้าง `custom_addons/od19_ai_assistant/lib/orm_guard.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Safety guard for AI-driven ORM access.

Everything the AI asks for (model, domain, fields, order, aggregates) passes
through this module *before* it reaches the ORM, so a hallucinating model can
never query an uninstalled model, an unknown field, a forbidden operator or an
unbounded result set.
"""

from odoo.fields import Domain

#: Operators the AI is allowed to use inside a domain condition.
SAFE_OPERATORS = frozenset(
    {"=", "!=", ">", ">=", "<", "<=", "in", "not in", "like", "ilike", "child_of"}
)
#: Prefix logic operators accepted at the domain level.
LOGIC_OPERATORS = ("&", "|", "!")
#: Aggregate functions allowed in ``aggregate_records``.
AGGREGATE_FUNCTIONS = frozenset({"sum", "avg", "min", "max", "count"})
#: Date granularities allowed in ``groupby``.
GROUPBY_GRANULARITIES = frozenset({"day", "week", "month", "quarter", "year"})

MAX_LIMIT = 20
DEFAULT_LIMIT = 5
MAX_FIELDS = 60
MAX_AGGREGATES = 8
MAX_GROUPBY = 3


class OrmGuardError(ValueError):
    """Raised when an AI request would be unsafe; the message is user facing."""


def safe_limit(value, default=DEFAULT_LIMIT, cap=MAX_LIMIT):
    """Coerce ``value`` into ``1..cap`` (or ``default`` when unparsable)."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, cap))


def safe_offset(value):
    """Coerce ``value`` into a non-negative offset."""
    try:
        offset = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, offset)


def check_model(env, model_name):
    """Ensure the model exists and the current user may read it."""
    if not model_name or not isinstance(model_name, str) or model_name not in env:
        raise OrmGuardError("ไม่พบโมเดล %s" % (model_name or ""))
    if not env[model_name].has_access("read"):
        raise OrmGuardError("คุณไม่มีสิทธิ์อ่านข้อมูลโมเดล %s" % model_name)
    return model_name


def check_field(env, model_name, path, require_stored=True):
    """Validate a (possibly dotted) field path against ``model_name``."""
    if not isinstance(path, str) or not path.strip():
        raise OrmGuardError("ชื่อฟิลด์ไม่ถูกต้อง")
    current = model_name
    parts = path.strip().split(".")
    for index, part in enumerate(parts):
        if current not in env:
            raise OrmGuardError("ไม่พบโมเดล %s" % current)
        field = env[current]._fields.get(part)
        if field is None:
            raise OrmGuardError('ไม่พบฟิลด์ "%s" ในโมเดล %s' % (part, current))
        if require_stored and field.compute and not field.store:
            raise OrmGuardError('ฟิลด์ "%s" เป็นค่าคำนวณที่ใช้กรองไม่ได้' % part)
        if index < len(parts) - 1:
            comodel = getattr(field, "comodel_name", None)
            if not comodel or comodel not in env:
                raise OrmGuardError(
                    'ฟิลด์ "%s" ไม่ใช่ความสัมพันธ์ที่อ้างอิงต่อได้' % part
                )
            current = comodel
    return path


def validate_fields(env, model_name, fields_):
    """Validate the list of fields to read (existence only, no stored check)."""
    if fields_ in (None, False, ""):
        return ["display_name"]
    if not isinstance(fields_, (list, tuple)):
        raise OrmGuardError("รายการฟิลด์ไม่ถูกต้อง")
    result = []
    for name in list(fields_)[:MAX_FIELDS]:
        check_field(env, model_name, name, require_stored=False)
        result.append(name)
    return result or ["display_name"]


def validate_order(env, model_name, order):
    """Validate an ``order`` clause (``"field asc, other desc"``)."""
    if order in (None, False, ""):
        return None
    if not isinstance(order, str):
        raise OrmGuardError("ลำดับการเรียงไม่ถูกต้อง")
    cleaned = []
    for token in order.replace(",", " ").split():
        if token.lower() in ("asc", "desc", "nulls", "first", "last"):
            cleaned.append(token)
            continue
        check_field(env, model_name, token)
        cleaned.append(token)
    return " ".join(cleaned) or None


def validate_groupby(env, model_name, groupby):
    """Validate a ``groupby`` list (``["state", "date:month"]``)."""
    if groupby in (None, False, ""):
        return []
    if not isinstance(groupby, (list, tuple)):
        raise OrmGuardError("รายการจัดกลุ่มไม่ถูกต้อง")
    result = []
    for item in list(groupby)[:MAX_GROUPBY]:
        if not isinstance(item, str):
            raise OrmGuardError("รายการจัดกลุ่มไม่ถูกต้อง")
        parts = item.split(":")
        if len(parts) > 2:
            raise OrmGuardError('รูปแบบการจัดกลุ่ม "%s" ไม่ถูกต้อง' % item)
        if len(parts) == 2 and parts[1] not in GROUPBY_GRANULARITIES:
            raise OrmGuardError('ความละเอียด "%s" ไม่ได้รับอนุญาต' % parts[1])
        check_field(env, model_name, parts[0])
        result.append(item)
    return result


def validate_aggregates(env, model_name, aggregates):
    """Validate an ``aggregates`` list (``["amount_total:sum", "__count"]``)."""
    if not isinstance(aggregates, (list, tuple)) or not aggregates:
        raise OrmGuardError("ต้องระบุฟิลด์สรุปอย่างน้อยหนึ่งรายการ")
    result = []
    for expr in list(aggregates)[:MAX_AGGREGATES]:
        if not isinstance(expr, str):
            raise OrmGuardError("รายการสรุปไม่ถูกต้อง")
        if expr == "__count":
            result.append(expr)
            continue
        parts = expr.split(":")
        if len(parts) != 2:
            raise OrmGuardError('รูปแบบการสรุป "%s" ไม่ถูกต้อง' % expr)
        _field_name, func = parts
        if func not in AGGREGATE_FUNCTIONS:
            raise OrmGuardError('ฟังก์ชันสรุป "%s" ไม่ได้รับอนุญาต' % func)
        check_field(env, model_name, parts[0])
        result.append(expr)
    return result


def validate_domain(env, model_name, domain):
    """Return a safe :class:`~odoo.fields.Domain` or raise :class:`OrmGuardError`."""
    if isinstance(domain, Domain):
        return domain
    if domain is None or domain is False or domain == "" or domain == []:
        return Domain.TRUE
    if not isinstance(domain, (list, tuple)):
        raise OrmGuardError("โดเมนการค้นหาไม่ถูกต้อง")
    return Domain(_parse_tokens(env, model_name, list(domain)))


def _parse_tokens(env, model_name, tokens):
    """Recursively validate legacy domain tokens (nested groups become Domain)."""
    result = []
    for token in tokens:
        if isinstance(token, str):
            if token not in LOGIC_OPERATORS:
                raise OrmGuardError('ตัวดำเนินการ "%s" ไม่ได้รับอนุญาต' % token)
            result.append(token)
        elif isinstance(token, (list, tuple)):
            is_leaf = (
                len(token) == 3
                and isinstance(token[0], str)
                and token[0] not in LOGIC_OPERATORS
            )
            if is_leaf:
                field_name, operator, value = token
                if not isinstance(operator, str) or operator not in SAFE_OPERATORS:
                    raise OrmGuardError(
                        'ตัวดำเนินการ "%s" ไม่ได้รับอนุญาต' % (operator,)
                    )
                check_field(env, model_name, field_name)
                result.append((field_name, operator, value))
            else:
                result.append(
                    Domain(_parse_tokens(env, model_name, list(token)))
                )
        else:
            raise OrmGuardError("โดเมนการค้นหาไม่ถูกต้อง")
    return result
```

แก้ `custom_addons/od19_ai_assistant/lib/__init__.py` ให้เป็น:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import orm_guard
from .client import AiClientError, chat_completion
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 5: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/lib/orm_guard.py custom_addons/od19_ai_assistant/lib/__init__.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add ORM safety guard for AI tool access"
```

---

## Task 2: Generic Explorer (`models/od19_ai_tool_generic.py`)

**Files:**
- Create: `custom_addons/od19_ai_assistant/models/od19_ai_tool_generic.py`
- Modify: `custom_addons/od19_ai_assistant/models/od19_ai_tool.py` (เพิ่ม `all_tools`, ปรับ `available_tools`/`execute`)
- Modify: `custom_addons/od19_ai_assistant/models/__init__.py`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestGenericExplorer(TransactionCase):
    def test_generic_tools_are_available(self):
        names = [t["name"] for t in self.env["od19.ai.tool"].available_tools()]
        for expected in (
            "list_models",
            "describe_model",
            "search_records",
            "aggregate_records",
        ):
            self.assertIn(expected, names)

    def test_list_models_returns_partner(self):
        result = self.env["od19.ai.tool"].execute(
            "list_models", {"keyword": "res.partner"}
        )
        self.assertIn("res.partner", result)

    def test_list_models_respects_limit(self):
        result = self.env["od19.ai.tool"].execute("list_models", {"limit": 3})
        lines = [line for line in result.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(lines), 3)

    def test_describe_model_lists_fields(self):
        result = self.env["od19.ai.tool"].execute(
            "describe_model", {"model": "res.partner"}
        )
        self.assertIn("res.partner", result)
        self.assertIn("name", result)

    def test_describe_model_rejects_unknown_model(self):
        result = self.env["od19.ai.tool"].execute(
            "describe_model", {"model": "does.not.exist"}
        )
        self.assertIn("ไม่พบโมเดล", result)

    def test_search_records_finds_created_partner(self):
        self.env["res.partner"].create({"name": "บริษัท ทดสอบทั่วไป จำกัด"})
        result = self.env["od19.ai.tool"].execute(
            "search_records",
            {
                "model": "res.partner",
                "domain": [["name", "ilike", "ทดสอบทั่วไป"]],
                "fields": ["name"],
            },
        )
        self.assertIn("บริษัท ทดสอบทั่วไป จำกัด", result)

    def test_search_records_rejects_bad_domain(self):
        result = self.env["od19.ai.tool"].execute(
            "search_records",
            {"model": "res.partner", "domain": [["name", "regex", "x"]]},
        )
        self.assertIn("ไม่ได้รับอนุญาต", result)

    def test_search_records_caps_limit(self):
        self.env["res.partner"].create([{"name": "ลูกค้า %s" % i} for i in range(30)])
        result = self.env["od19.ai.tool"].execute(
            "search_records", {"model": "res.partner", "fields": ["name"], "limit": 500}
        )
        lines = [line for line in result.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(lines), 20)

    def test_aggregate_records_counts(self):
        self.env["res.partner"].create([{"name": "agg %s" % i} for i in range(3)])
        result = self.env["od19.ai.tool"].execute(
            "aggregate_records",
            {
                "model": "res.partner",
                "domain": [["name", "ilike", "agg"]],
                "aggregates": ["__count"],
            },
        )
        self.assertIn("จำนวน", result)
        self.assertIn("3", result)

    def test_aggregate_records_rejects_bad_function(self):
        result = self.env["od19.ai.tool"].execute(
            "aggregate_records",
            {"model": "res.partner", "aggregates": ["id:median"]},
        )
        self.assertIn("ไม่ได้รับอนุญาต", result)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — `list_models` ไม่อยู่ใน `available_tools()` / `execute("list_models", ...)` คืน `"ไม่พบเครื่องมือชื่อ list_models"`

- [ ] **Step 3: ปรับ `models/od19_ai_tool.py`** — เพิ่ม `all_tools()`, ปรับ `available_tools()` และ `execute()`

ใน `models/od19_ai_tool.py` แทนที่บล็อก `available_tools` เดิม (บรรทัด ~126-133) ด้วย:

```python
    @api.model
    def all_tools(self):
        """Every declared tool: curated + generic + meta + draft.

        Each specialised layer contributes through its own ``_*_definitions``
        method (defined in its own file). ``getattr`` keeps the layers optional
        so the module still loads while they are being built.
        """
        definitions = list(self._tool_definitions())
        for method_name in (
            "_generic_definitions",
            "_index_definitions",
            "_draft_definitions",
        ):
            method = getattr(self, method_name, None)
            if method:
                definitions.extend(method())
        return definitions

    @api.model
    def available_tools(self):
        """Definitions whose backing model is installed (model-less = always)."""
        result = []
        for tool in self.all_tools():
            model_name = tool.get("model")
            if model_name is None or model_name in self.env:
                result.append(tool)
        return result
```

แทนที่เมธอด `execute` เดิม (บรรทัด ~147-167) ด้วย:

```python
    @api.model
    def execute(self, name, arguments):
        """Run a tool by ``name`` and return a plain-text result."""
        tool = next(
            (t for t in self.available_tools() if t["name"] == name), None
        )
        if tool is None:
            return "ไม่พบเครื่องมือชื่อ %s" % name
        method = getattr(self, "_run_%s" % name, None)
        if method is None:
            return "เครื่องมือ %s ยังไม่พร้อมใช้งาน" % name
        model_name = tool.get("model")
        if model_name and not self._check_read_access(model_name):
            return "คุณไม่มีสิทธิ์อ่านข้อมูล %s" % self.env[
                model_name
            ]._description
        arguments = arguments if isinstance(arguments, dict) else {}
        try:
            return method(arguments)
        except Exception as exc:  # noqa: BLE001 - never break the chat loop
            _logger.warning("AI tool %s failed: %s", name, exc)
            return "เรียกเครื่องมือ %s ไม่สำเร็จ: %s" % (name, exc)
```

- [ ] **Step 4: สร้าง `models/od19_ai_tool_generic.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Generic Explorer — the layer that gives the assistant access to *every*
installed Odoo model the current user may read, without a bespoke tool.

The four meta-tools are bounded (``orm_guard``), read with the user's real
rights (no ``sudo``) and cached metadata-wise so repeated calls are free.
"""

import logging

from odoo import api, models, tools

from ..lib import orm_guard

_logger = logging.getLogger(__name__)

MAX_LIST_MODELS = 60
MAX_DESCRIBE_FIELDS = 60


class Od19AiToolGeneric(models.AbstractModel):
    _inherit = "od19.ai.tool"

    # ------------------------------------------------------------------
    # Registry contribution
    # ------------------------------------------------------------------
    @api.model
    def _generic_definitions(self):
        return [
            {
                "name": "list_models",
                "model": None,
                "kind": "read",
                "description": "ค้นหาโมเดล (ตาราง) ในระบบที่ผู้ใช้มีสิทธิ์อ่าน",
                "arguments": {
                    "keyword": "คำค้นหา (ไม่บังคับ)",
                    "limit": "จำนวนผลสูงสุด",
                },
            },
            {
                "name": "describe_model",
                "model": None,
                "kind": "read",
                "description": "ดูรายชื่อฟิลด์ของโมเดล (ชื่อ ชนิด ป้าย จำเป็น ความสัมพันธ์)",
                "arguments": {"model": "ชื่อโมเดล"},
            },
            {
                "name": "search_records",
                "model": None,
                "kind": "read",
                "description": "ค้นหาเรกคอร์ดจริงในโมเดลใดก็ได้ ด้วย domain/fields/limit",
                "arguments": {
                    "model": "ชื่อโมเดล",
                    "domain": "เงื่อนไข เช่น [['name','ilike','abc']]",
                    "fields": "รายชื่อฟิลด์ที่ต้องการ",
                    "limit": "จำนวนผลสูงสุด (ไม่เกิน 20)",
                    "order": "การเรียง (ไม่บังคับ)",
                },
            },
            {
                "name": "aggregate_records",
                "model": None,
                "kind": "read",
                "description": "สรุปผลด้วย _read_group (groupby/aggregates)",
                "arguments": {
                    "model": "ชื่อโมเดล",
                    "domain": "เงื่อนไข",
                    "groupby": "เช่น ['state'] หรือ ['create_date:month']",
                    "aggregates": "เช่น ['__count', 'amount_total:sum']",
                },
            },
        ]

    # ------------------------------------------------------------------
    # Metadata cache
    # ------------------------------------------------------------------
    @api.model
    @tools.ormcache("self.env.uid", cache="stable")
    def _readable_model_names(self):
        """Cached set of model names the current user may read.

        Uses ``ir.model.access._get_allowed_models`` (itself ormcached) instead
        of reading ``ir.model``, which plain users cannot access. The
        ``stable`` cache is cleared whenever the registry reloads.
        """
        allowed = self.env["ir.model.access"]._get_allowed_models("read")
        return frozenset(name for name in allowed if name in self.env)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    @api.model
    def _run_list_models(self, arguments):
        keyword = (arguments.get("keyword") or "").strip().lower()
        limit = orm_guard.safe_limit(
            arguments.get("limit"), default=20, cap=MAX_LIST_MODELS
        )
        lines = []
        for model_name in sorted(self._readable_model_names()):
            label = self.env[model_name]._description or model_name
            if (
                keyword
                and keyword not in model_name.lower()
                and keyword not in (label or "").lower()
            ):
                continue
            lines.append("- %s: %s" % (model_name, label))
            if len(lines) >= limit:
                break
        return "\n".join(lines) or "ไม่พบโมเดล"

    @api.model
    def _run_describe_model(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        try:
            orm_guard.check_model(self.env, model_name)
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        model = self.env[model_name]
        lines = [
            "โมเดล %s — %s" % (model_name, model._description or model_name)
        ]
        shown = 0
        for field_name in sorted(model._fields):
            field = model._fields[field_name]
            if not field.store:
                continue
            if shown >= MAX_DESCRIBE_FIELDS:
                lines.append("... (แสดง %d ฟิลด์แรก)" % MAX_DESCRIBE_FIELDS)
                break
            parts = [field_name, field.type]
            if field.required:
                parts.append("required")
            relation = getattr(field, "comodel_name", None)
            if relation:
                parts.append("→ %s" % relation)
            label = field.string or field_name
            lines.append("- %s: %s" % (", ".join(parts), label))
            shown += 1
        return "\n".join(lines)

    @api.model
    def _run_search_records(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        try:
            orm_guard.check_model(self.env, model_name)
            domain = orm_guard.validate_domain(
                self.env, model_name, arguments.get("domain")
            )
            fields_ = orm_guard.validate_fields(
                self.env, model_name, arguments.get("fields")
            )
            order = orm_guard.validate_order(
                self.env, model_name, arguments.get("order")
            )
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        limit = orm_guard.safe_limit(arguments.get("limit"))
        offset = orm_guard.safe_offset(arguments.get("offset"))
        records = self.env[model_name].search_read(
            domain, fields_, limit=limit, offset=offset, order=order
        )
        return self._format_records(records, fields_)

    @api.model
    def _run_aggregate_records(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        try:
            orm_guard.check_model(self.env, model_name)
            domain = orm_guard.validate_domain(
                self.env, model_name, arguments.get("domain")
            )
            groupby = orm_guard.validate_groupby(
                self.env, model_name, arguments.get("groupby")
            )
            aggregates = orm_guard.validate_aggregates(
                self.env, model_name, arguments.get("aggregates")
            )
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        try:
            rows = self.env[model_name]._read_group(
                domain,
                groupby=groupby,
                aggregates=aggregates,
                limit=orm_guard.safe_limit(arguments.get("limit"), default=20),
            )
        except Exception as exc:  # noqa: BLE001 - report, never crash the chat
            _logger.warning("aggregate_records failed: %s", exc)
            return "สรุปข้อมูลไม่สำเร็จ: %s" % exc
        group_labels = self._groupby_labels(model_name, groupby)
        aggregate_labels = [
            self._aggregate_label(model_name, expr) for expr in aggregates
        ]
        return self._format_groups(rows, group_labels, aggregate_labels)

    # ------------------------------------------------------------------
    # Label helpers
    # ------------------------------------------------------------------
    @api.model
    def _groupby_labels(self, model_name, groupby):
        model = self.env[model_name]
        labels = []
        for item in groupby:
            field_name = item.split(":")[0]
            field = model._fields.get(field_name)
            labels.append(field.string if field else field_name)
        return labels

    @api.model
    def _aggregate_label(self, model_name, expr):
        if expr == "__count":
            return "จำนวน"
        field_name, func = expr.split(":")
        field = self.env[model_name]._fields.get(field_name)
        base = field.string if field else field_name
        return "%s (%s)" % (base, func)
```

แก้ `models/__init__.py` ให้เป็น:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import od19_ai_tool
from . import od19_ai_tool_generic
from . import od19_ai_message
from . import od19_ai_chat
from . import res_config_settings
```

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 6: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/models/od19_ai_tool.py custom_addons/od19_ai_assistant/models/od19_ai_tool_generic.py custom_addons/od19_ai_assistant/models/__init__.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add generic ORM explorer tools (list/describe/search/aggregate)"
```

---

## Task 3: Capability Index + Progressive Disclosure (`models/od19_ai_tool_index.py`)

**Files:**
- Create: `custom_addons/od19_ai_assistant/models/od19_ai_tool_index.py`
- Modify: `custom_addons/od19_ai_assistant/models/od19_ai_chat.py` (ใช้ `prompt_index()` + ปรับข้อความ `TOOL_PROTOCOL`)
- Modify: `custom_addons/od19_ai_assistant/models/__init__.py`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestCapabilityIndex(TransactionCase):
    def test_prompt_index_lists_tools_without_schemas(self):
        index = self.env["od19.ai.tool"].prompt_index()
        self.assertIn("search_partners", index)
        self.assertIn("search_records", index)
        # Argument schemas must NOT be inlined in the index.
        self.assertNotIn("จำนวนผลสูงสุด", index)

    def test_prompt_index_respects_char_budget(self):
        index = self.env["od19.ai.tool"].prompt_index()
        self.assertLessEqual(
            len(index), self.env["od19.ai.tool"].MAX_INDEX_CHARS
        )

    def test_tool_help_returns_argument_schema(self):
        help_text = self.env["od19.ai.tool"].execute(
            "tool_help", {"name": "search_records"}
        )
        self.assertIn("search_records", help_text)
        self.assertIn("domain", help_text)

    def test_tool_help_unknown_tool(self):
        help_text = self.env["od19.ai.tool"].execute(
            "tool_help", {"name": "no_such_tool"}
        )
        self.assertIn("ไม่พบเครื่องมือ", help_text)

    def test_full_schema_returns_arguments(self):
        schema = self.env["od19.ai.tool"].full_schema("search_partners")
        self.assertIn("keyword", schema["arguments"])

    def test_system_prompt_uses_index(self):
        prompt = self.env["od19.ai.chat"]._build_system_prompt("BASE")
        self.assertIn("tool_help", prompt)
        self.assertIn("search_partners", prompt)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — `AttributeError: 'od19.ai.tool' object has no attribute 'prompt_index'`

- [ ] **Step 3: สร้าง `models/od19_ai_tool_index.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Layer 0 — Capability Index and progressive disclosure.

The system prompt only ever carries a short one-line-per-tool index. When the
model needs a tool's argument schema it asks for it explicitly through
``tool_help``, which keeps the prompt small no matter how many tools exist.
"""

from odoo import api, models


class Od19AiToolIndex(models.AbstractModel):
    _inherit = "od19.ai.tool"

    #: Hard ceiling for the index injected into the system prompt.
    MAX_INDEX_CHARS = 3000
    #: One-line description length inside the index.
    INDEX_DESC_LENGTH = 70

    # ------------------------------------------------------------------
    # Registry contribution
    # ------------------------------------------------------------------
    @api.model
    def _index_definitions(self):
        return [
            {
                "name": "tool_help",
                "model": None,
                "kind": "meta",
                "description": "ดูรายละเอียดพารามิเตอร์ของเครื่องมือหนึ่งตัว",
                "arguments": {"name": "ชื่อเครื่องมือ"},
            },
        ]

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------
    @api.model
    def prompt_index(self):
        """One compact line per tool, capped by :attr:`MAX_INDEX_CHARS`."""
        lines = []
        for tool in self.available_tools():
            description = (tool.get("description") or "").strip().splitlines()
            short = description[0] if description else ""
            if len(short) > self.INDEX_DESC_LENGTH:
                short = short[: self.INDEX_DESC_LENGTH - 1] + "…"
            lines.append("- %s: %s" % (tool["name"], short))
        index = "\n".join(lines)
        if len(index) > self.MAX_INDEX_CHARS:
            index = index[: self.MAX_INDEX_CHARS - 1] + "…"
        return index

    @api.model
    def full_schema(self, name):
        """Return the full definition dict of ``name`` (or ``{}``)."""
        return next(
            (t for t in self.available_tools() if t["name"] == name), {}
        )

    # ------------------------------------------------------------------
    # tool_help implementation
    # ------------------------------------------------------------------
    @api.model
    def _run_tool_help(self, arguments):
        name = (arguments.get("name") or "").strip()
        tool = self.full_schema(name)
        if not tool:
            return "ไม่พบเครื่องมือชื่อ %s" % name
        lines = ["เครื่องมือ %s: %s" % (tool["name"], tool["description"])]
        arguments_schema = tool.get("arguments") or {}
        if arguments_schema:
            for key, description in arguments_schema.items():
                lines.append("- %s: %s" % (key, description))
        else:
            lines.append("- (ไม่มีพารามิเตอร์)")
        return "\n".join(lines)
```

แก้ `models/__init__.py` ให้เพิ่มบรรทัด (วางต่อจาก `od19_ai_tool_generic`):

```python
from . import od19_ai_tool_index
```

- [ ] **Step 4: ปรับ `models/od19_ai_chat.py`**

แทนที่ค่าคงที่ `TOOL_PROTOCOL` (บรรทัด ~24-31) ด้วย:

```python
TOOL_PROTOCOL = (
    "\n\nคุณสามารถเรียกใช้เครื่องมือเพื่ออ่านข้อมูลจริงจากระบบ Odoo ได้ "
    "เมื่อต้องการข้อมูล ให้ตอบกลับเป็น JSON เท่านั้นในรูปแบบ:\n"
    '{{"tool": "<ชื่อเครื่องมือ>", "arguments": {{<พารามิเตอร์>}}}}\n'
    "เครื่องมือที่มี:\n%s\n"
    "หากต้องการทราบพารามิเตอร์ของเครื่องมือ ให้เรียก tool_help ก่อน "
    'เช่น {{"tool": "tool_help", "arguments": {{"name": "search_records"}}}}\n'
    "เมื่อได้ข้อมูลเพียงพอแล้ว ให้ตอบเป็นข้อความภาษาไทยปกติ ห้ามใส่ JSON\n"
    "ห้ามสมมติข้อมูลเอง หากไม่พบให้แจ้งผู้ใช้ตามจริง"
)
```

แทนที่เมธอด `_build_system_prompt` (บรรทัด ~170-176) ด้วย:

```python
    @api.model
    def _build_system_prompt(self, base_prompt):
        """Append the compact tool index to the base system prompt."""
        index = self.env["od19.ai.tool"].prompt_index()
        if not index:
            return base_prompt
        return base_prompt + TOOL_PROTOCOL % index
```

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s) (รวมเทสต์เดิม `test_system_prompt_includes_tool_catalog` ที่ตรวจ `search_partners`)

- [ ] **Step 6: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/models/od19_ai_tool_index.py custom_addons/od19_ai_assistant/models/od19_ai_chat.py custom_addons/od19_ai_assistant/models/__init__.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add capability index with progressive tool disclosure"
```

---

## Task 4: Capability Mode + Draft Gate + Audit (`od19_ai_capability.py`, `od19_ai_tool_log.py`)

**Files:**
- Create: `custom_addons/od19_ai_assistant/models/od19_ai_tool_log.py`
- Create: `custom_addons/od19_ai_assistant/models/od19_ai_capability.py`
- Create: `custom_addons/od19_ai_assistant/security/od19_ai_security.xml`
- Modify: `custom_addons/od19_ai_assistant/security/ir.model.access.csv`
- Modify: `custom_addons/od19_ai_assistant/__manifest__.py`
- Modify: `custom_addons/od19_ai_assistant/models/od19_ai_tool.py` (เพิ่ม audit log ใน `execute`)
- Modify: `custom_addons/od19_ai_assistant/models/__init__.py`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestCapabilityMode(TransactionCase):
    def setUp(self):
        super().setUp()
        self.params = self.env["ir.config_parameter"].sudo()
        self.params.search([("key", "=like", "od19_ai.%")]).unlink()
        self.capability = self.env["od19.ai.capability"]

    def test_default_mode_is_read_only(self):
        self.assertEqual(self.capability.system_mode(), "read_only")

    def test_can_draft_false_in_read_only(self):
        self.params.set_param("od19_ai.capability_mode", "read_only")
        self.assertFalse(self.capability.can_draft("res.partner"))

    def test_can_draft_true_for_whitelisted_model(self):
        self.params.set_param("od19_ai.capability_mode", "read_draft")
        self.params.set_param("od19_ai.draft_models", "res.partner")
        self.assertTrue(self.capability.can_draft("res.partner"))

    def test_can_draft_false_for_non_whitelisted_model(self):
        self.params.set_param("od19_ai.capability_mode", "read_draft")
        self.params.set_param("od19_ai.draft_models", "res.partner")
        self.assertFalse(self.capability.can_draft("res.company"))

    def test_create_draft_rejected_in_read_only(self):
        self.params.set_param("od19_ai.capability_mode", "read_only")
        with self.assertRaises(UserError):
            self.capability.create_draft("res.partner", {"name": "ห้ามสร้าง"})

    def test_create_draft_creates_record(self):
        self.params.set_param("od19_ai.capability_mode", "read_draft")
        self.params.set_param("od19_ai.draft_models", "res.partner")
        record = self.capability.create_draft("res.partner", {"name": "ร่างใหม่"})
        self.assertTrue(record.exists())
        self.assertEqual(record.name, "ร่างใหม่")

    def test_sanitize_rejects_unknown_field(self):
        from odoo.addons.od19_ai_assistant.lib import orm_guard

        self.params.set_param("od19_ai.draft_models", "res.partner")
        with self.assertRaises(orm_guard.OrmGuardError):
            self.capability._sanitize_values(
                "res.partner", {"name": "x", "nope": 1}
            )

    def test_preview_draft_does_not_create(self):
        self.params.set_param("od19_ai.draft_models", "res.partner")
        before = self.env["res.partner"].search_count([])
        self.capability.preview_draft("res.partner", {"name": "พรีวิว"})
        self.assertEqual(self.env["res.partner"].search_count([]), before)

    def test_draft_record_tool_returns_marker(self):
        self.params.set_param("od19_ai.capability_mode", "read_draft")
        self.params.set_param("od19_ai.draft_models", "res.partner")
        result = self.env["od19.ai.tool"].execute(
            "draft_record", {"model": "res.partner", "values": {"name": "ร่าง"}}
        )
        self.assertTrue(result.startswith("__OD19_DRAFT__"))

    def test_draft_record_tool_rejected_in_read_only(self):
        self.params.set_param("od19_ai.capability_mode", "read_only")
        result = self.env["od19.ai.tool"].execute(
            "draft_record", {"model": "res.partner", "values": {"name": "ร่าง"}}
        )
        self.assertFalse(result.startswith("__OD19_DRAFT__"))

    def test_execute_writes_audit_log(self):
        before = self.env["od19.ai.tool.log"].search_count([])
        self.env["od19.ai.tool"].execute(
            "search_partners", {"keyword": "audit-probe"}
        )
        logs = self.env["od19.ai.tool.log"].search(
            [("tool_name", "=", "search_partners")]
        )
        self.assertGreaterEqual(len(logs), 1)
        self.assertGreater(self.env["od19.ai.tool.log"].search_count([]), before)
        self.assertTrue(logs[0].success)

    def test_audit_log_redacts_secrets(self):
        capability = self.capability
        log = self.env["od19.ai.tool.log"].create(
            {
                "tool_name": "demo",
                "tool_kind": "read",
                "arguments": capability._redact_arguments(
                    {"api_key": "secret", "keyword": "ok"}
                ),
            }
        )
        self.assertNotIn("secret", str(log.arguments))
        self.assertIn("ok", str(log.arguments))
```

เพิ่ม import ด้านบนของไฟล์เทสต์ (ถัดจาก import เดิม):

```python
from odoo.exceptions import UserError
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — `KeyError: 'od19.ai.capability'` / `KeyError: 'od19.ai.tool.log'`

- [ ] **Step 3: สร้าง `models/od19_ai_tool_log.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Audit trail for every AI tool call."""

from odoo import api, fields, models


class Od19AiToolLog(models.Model):
    _name = "od19.ai.tool.log"
    _description = "บันทึกการเรียกเครื่องมือของผู้ช่วย AI (OD19)"
    _order = "create_date desc"

    name = fields.Char(compute="_compute_name", store=True)
    user_id = fields.Many2one(
        "res.users",
        string="ผู้ใช้",
        required=True,
        index=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    chat_id = fields.Many2one(
        "od19.ai.chat", string="บทสนทนา", index=True, ondelete="set null"
    )
    tool_name = fields.Char(string="เครื่องมือ", index=True)
    tool_kind = fields.Selection(
        [("read", "อ่าน"), ("draft", "ร่าง"), ("external", "ภายนอก")],
        string="ประเภท",
        default="read",
    )
    arguments = fields.Json(string="พารามิเตอร์")
    result_summary = fields.Char(string="สรุปผล")
    success = fields.Boolean(string="สำเร็จ", default=True)
    error_message = fields.Char(string="ข้อผิดพลาด")
    duration_ms = fields.Integer(string="เวลา (มิลลิวินาที)")

    @api.depends("tool_name", "tool_kind")
    def _compute_name(self):
        for record in self:
            record.name = "%s (%s)" % (
                record.tool_name or "-",
                record.tool_kind or "-",
            )
```

- [ ] **Step 4: สร้าง `models/od19_ai_capability.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Capability gate + safe draft creation + audit logging.

Two modes exist: ``read_only`` (A, default) and ``read_draft`` (B, opt-in).
Draft creation always uses the *current user's* rights (never ``sudo``), only
for whitelisted models, and always forces a non-posting ``draft`` state.
"""

import json
import logging
import time

from odoo import api, models
from odoo.exceptions import UserError

from ..lib import orm_guard

_logger = logging.getLogger(__name__)

#: Sentinel prefix marking a tool result as a draft proposal (never a record).
DRAFT_MARKER = "__OD19_DRAFT__"

#: Secret-ish argument keys that must never reach the audit log.
REDACTED_KEYS = ("password", "api_key", "token", "secret", "key")

#: Fields the AI may never set on a draft.
FORBIDDEN_FIELDS = frozenset(
    {
        "payment_state",
        "amount_residual",
        "amount_residual_signed",
        "reconciled",
    }
)


class Od19AiCapability(models.AbstractModel):
    _name = "od19.ai.capability"
    _description = "ชั้นควบคุมความสามารถของผู้ช่วย AI (OD19)"

    DRAFT_MODES = ("read_only", "read_draft")
    DEFAULT_DRAFT_MODELS = (
        "sale.order",
        "purchase.order",
        "account.move",
        "project.task",
        "mail.activity",
        "helpdesk.ticket",
        "crm.lead",
    )

    # ------------------------------------------------------------------
    # Mode resolution
    # ------------------------------------------------------------------
    @api.model
    def _param(self, key, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_ai.%s" % key, default)
        )

    @api.model
    def system_mode(self):
        mode = self._param("capability_mode")
        return mode if mode in self.DRAFT_MODES else "read_only"

    @api.model
    def capability_mode(self, user=None):
        user = user or self.env.user
        mode = getattr(user, "od19_ai_capability_mode", None) or self.system_mode()
        return mode if mode in self.DRAFT_MODES else "read_only"

    @api.model
    def _draft_whitelist(self):
        raw = self._param("draft_models")
        names = [item.strip() for item in (raw or "").split(",") if item.strip()]
        if not names:
            names = list(self.DEFAULT_DRAFT_MODELS)
        return tuple(name for name in names if name in self.env)

    @api.model
    def can_draft(self, model_name=None):
        if self.capability_mode() != "read_draft":
            return False
        if not model_name:
            return True
        if model_name not in self._draft_whitelist():
            return False
        return self.env[model_name].has_access("create")

    # ------------------------------------------------------------------
    # Draft creation (2-step: preview -> confirm)
    # ------------------------------------------------------------------
    @api.model
    def preview_draft(self, model_name, values):
        if not self.can_draft(model_name):
            raise UserError("โหมดปัจจุบันไม่อนุญาตให้สร้างเอกสารร่าง")
        cleaned = self._sanitize_values(model_name, values)
        return {
            "model": model_name,
            "model_label": self.env[model_name]._description or model_name,
            "values": {key: str(value) for key, value in cleaned.items()},
        }

    @api.model
    def create_draft(self, model_name, values):
        """Create a draft record with the current user's rights (never sudo)."""
        if not self.can_draft(model_name):
            raise UserError("โหมดปัจจุบันไม่อนุญาตให้สร้างเอกสารร่าง")
        cleaned = self._sanitize_values(model_name, values)
        record = self.env[model_name].create(cleaned)
        self.log_call(
            "draft_record",
            "draft",
            {"model": model_name, "values": cleaned},
            "สร้างร่าง %s" % record.display_name,
            success=True,
        )
        return record

    @api.model
    def _sanitize_values(self, model_name, values):
        model = self.env[model_name]
        cleaned = {}
        for field_name, value in (values or {}).items():
            if field_name in FORBIDDEN_FIELDS:
                raise orm_guard.OrmGuardError(
                    'ไม่อนุญาตให้ตั้งค่าฟิลด์ "%s"' % field_name
                )
            field = model._fields.get(field_name)
            if field is None or not field.store:
                raise orm_guard.OrmGuardError(
                    'ไม่พบฟิลด์ "%s" ในโมเดล %s' % (field_name, model_name)
                )
            cleaned[field_name] = value
        state_field = model._fields.get("state")
        if state_field and state_field.type == "selection":
            selection = [key for key, _label in (state_field.selection or [])]
            if "draft" in selection:
                cleaned["state"] = "draft"
        return cleaned

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    @api.model
    def _redact_arguments(self, arguments):
        if not isinstance(arguments, dict):
            return {}
        redacted = {}
        for key, value in arguments.items():
            lowered = key.lower()
            if any(marker in lowered for marker in REDACTED_KEYS):
                redacted[key] = "***"
            else:
                redacted[key] = value
        return redacted

    @api.model
    def log_call(
        self,
        tool_name,
        tool_kind,
        arguments,
        result,
        success=True,
        error="",
        duration_ms=0,
        chat=None,
    ):
        try:
            self.env["od19.ai.tool.log"].create(
                {
                    "user_id": self.env.user.id,
                    "chat_id": chat.id if chat else False,
                    "tool_name": tool_name,
                    "tool_kind": tool_kind or "read",
                    "arguments": self._redact_arguments(arguments),
                    "result_summary": (result or "")[:120],
                    "success": success,
                    "error_message": (error or "")[:200],
                    "duration_ms": duration_ms,
                }
            )
        except Exception:  # noqa: BLE001 - audit must never break a call
            _logger.warning("OD19 AI audit log failed", exc_info=True)


class Od19AiToolDraft(models.AbstractModel):
    """Registers the ``draft_record`` tool on the shared tool registry."""

    _inherit = "od19.ai.tool"

    @api.model
    def _draft_definitions(self):
        return [
            {
                "name": "draft_record",
                "model": None,
                "kind": "draft",
                "description": (
                    "เสนอสร้างเอกสารร่าง (ต้องได้รับการยืนยันจากผู้ใช้ก่อนสร้างจริง)"
                ),
                "arguments": {
                    "model": "ชื่อโมเดลที่อนุญาต",
                    "values": "ค่าฟิลด์ของเอกสารร่าง",
                },
            },
        ]

    @api.model
    def _run_draft_record(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        values = arguments.get("values") or {}
        capability = self.env["od19.ai.capability"]
        if not capability.can_draft(model_name):
            return (
                "โหมดปัจจุบันไม่อนุญาตให้สร้างเอกสารร่าง "
                "หรือโมเดล %s ไม่อยู่ในรายการที่อนุญาต" % model_name
            )
        try:
            preview = capability.preview_draft(model_name, values)
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        return DRAFT_MARKER + json.dumps(preview, ensure_ascii=False)
```

- [ ] **Step 5: ปรับ `models/od19_ai_tool.py` ให้บันทึก audit ใน `execute`**

เพิ่ม `import time` ในส่วน import ของไฟล์ (ถัดจาก `import logging`):

```python
import time
```

แทนที่เมธอด `execute` ด้วยเวอร์ชันที่มีการวัดเวลา + เขียน log:

```python
    @api.model
    def execute(self, name, arguments):
        """Run a tool by ``name``, audit it, and return a plain-text result."""
        tool = next(
            (t for t in self.available_tools() if t["name"] == name), None
        )
        if tool is None:
            return "ไม่พบเครื่องมือชื่อ %s" % name
        method = getattr(self, "_run_%s" % name, None)
        if method is None:
            return "เครื่องมือ %s ยังไม่พร้อมใช้งาน" % name
        model_name = tool.get("model")
        if model_name and not self._check_read_access(model_name):
            return "คุณไม่มีสิทธิ์อ่านข้อมูล %s" % self.env[
                model_name
            ]._description
        arguments = arguments if isinstance(arguments, dict) else {}
        started = time.monotonic()
        success = True
        error = ""
        try:
            result = method(arguments)
        except Exception as exc:  # noqa: BLE001 - never break the chat loop
            success = False
            error = str(exc)
            _logger.warning("AI tool %s failed: %s", name, exc)
            result = "เรียกเครื่องมือ %s ไม่สำเร็จ: %s" % (name, exc)
        duration_ms = int((time.monotonic() - started) * 1000)
        self.env["od19.ai.capability"].log_call(
            name,
            tool.get("kind", "read"),
            arguments,
            result,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        return result
```

- [ ] **Step 6: เพิ่มสิทธิ์และ record rule**

แก้ `security/ir.model.access.csv` — เพิ่มบรรทัดที่ 4:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_ai_chat_user,od19.ai.chat user,model_od19_ai_chat,base.group_user,1,1,1,1
access_od19_ai_message_user,od19.ai.message user,model_od19_ai_message,base.group_user,1,1,1,1
access_od19_ai_tool_log_user,od19.ai.tool.log user,model_od19_ai_tool_log,base.group_user,1,0,1,0
```

สร้าง `security/od19_ai_security.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="rule_od19_ai_tool_log_user" model="ir.rule">
        <field name="name">OD19 AI tool log: ผู้ใช้เห็นเฉพาะของตัวเอง</field>
        <field name="model_id" ref="model_od19_ai_tool_log"/>
        <field name="domain_force">[('user_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="rule_od19_ai_tool_log_system" model="ir.rule">
        <field name="name">OD19 AI tool log: ผู้ดูแลเห็นทั้งหมด</field>
        <field name="model_id" ref="model_od19_ai_tool_log"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('base.group_system'))]"/>
    </record>

</odoo>
```

แก้ `__manifest__.py` — เพิ่มไฟล์ security ใน `data`:

```python
    "data": [
        "security/ir.model.access.csv",
        "security/od19_ai_security.xml",
        "views/res_config_settings_views.xml",
        "views/od19_ai_chat_views.xml",
    ],
```

แก้ `models/__init__.py` ให้เป็นลำดับนี้ (log ก่อน capability เพื่อให้ ACL พร้อมก่อนเขียน log):

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import od19_ai_tool
from . import od19_ai_tool_generic
from . import od19_ai_tool_index
from . import od19_ai_message
from . import od19_ai_chat
from . import od19_ai_tool_log
from . import od19_ai_capability
from . import res_config_settings
```

- [ ] **Step 7: รันเทสต์ให้ผ่าน**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 8: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/models/od19_ai_tool_log.py custom_addons/od19_ai_assistant/models/od19_ai_capability.py custom_addons/od19_ai_assistant/models/od19_ai_tool.py custom_addons/od19_ai_assistant/models/__init__.py custom_addons/od19_ai_assistant/security/ir.model.access.csv custom_addons/od19_ai_assistant/security/od19_ai_security.xml custom_addons/od19_ai_assistant/__manifest__.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add capability mode gate, safe drafts and audit log"
```

---

## Task 5: Settings Default + Per-User Mode (`res_config_settings.py`, `models/res_users.py`, views)

**Files:**
- Create: `custom_addons/od19_ai_assistant/models/res_users.py`
- Modify: `custom_addons/od19_ai_assistant/models/res_config_settings.py`
- Modify: `custom_addons/od19_ai_assistant/models/__init__.py`
- Modify: `custom_addons/od19_ai_assistant/views/res_config_settings_views.xml`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestCapabilitySettings(TransactionCase):
    def setUp(self):
        super().setUp()
        self.params = self.env["ir.config_parameter"].sudo()
        self.params.search([("key", "=like", "od19_ai.%")]).unlink()

    def test_users_default_mode_is_read_only(self):
        self.assertEqual(self.env.user.od19_ai_capability_mode, "read_only")

    def test_settings_mode_field_persists(self):
        settings = self.env["res.config.settings"].create(
            {"od19_ai_capability_mode": "read_draft"}
        )
        settings.set_values()
        self.assertEqual(
            self.params.get_param("od19_ai.capability_mode"), "read_draft"
        )

    def test_new_user_default_follows_system_mode(self):
        self.params.set_param("od19_ai.capability_mode", "read_draft")
        user = self.env["res.users"].create(
            {
                "name": "OD19 Mode User",
                "login": "od19_mode_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertEqual(user.od19_ai_capability_mode, "read_draft")

    def test_user_override_wins_over_system(self):
        self.params.set_param("od19_ai.capability_mode", "read_draft")
        user = self.env["res.users"].create(
            {
                "name": "OD19 Readonly User",
                "login": "od19_readonly_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                "od19_ai_capability_mode": "read_only",
            }
        )
        self.assertEqual(
            self.env["od19.ai.capability"].capability_mode(user), "read_only"
        )
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — `res.config.settings` ไม่มีฟิลด์ `od19_ai_capability_mode`

- [ ] **Step 3: สร้าง `models/res_users.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models

from odoo.addons.base.models.res_users import ResUsers as BaseResUsers


class ResUsers(models.Model):
    _inherit = "res.users"

    od19_ai_capability_mode = fields.Selection(
        selection=[
            ("read_only", "อ่านเท่านั้น (A)"),
            ("read_draft", "อ่าน + ร่างเอกสาร (B)"),
        ],
        string="โหมดผู้ช่วย AI",
        default=lambda self: self._od19_ai_default_mode(),
        help="โหมดการทำงานของผู้ช่วย AI สำหรับผู้ใช้รายนี้ "
        "ค่าเริ่มต้นอ้างอิงจากดีฟอลต์ของระบบในหน้าตั้งค่า",
    )

    SELF_READABLE_FIELDS = BaseResUsers.SELF_READABLE_FIELDS + [
        "od19_ai_capability_mode"
    ]
    SELF_WRITEABLE_FIELDS = BaseResUsers.SELF_WRITEABLE_FIELDS + [
        "od19_ai_capability_mode"
    ]

    @api.model
    def _od19_ai_default_mode(self):
        mode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_ai.capability_mode")
        )
        return mode if mode in ("read_only", "read_draft") else "read_only"
```

แก้ `models/__init__.py` — เพิ่ม `from . import res_users` ใต้ `res_config_settings`:

```python
from . import res_config_settings
from . import res_users
```

- [ ] **Step 4: ปรับ `models/res_config_settings.py`**

เพิ่มฟิลด์ (วางต่อจาก `od19_ai_system_prompt`) — โมเดล `res.config.settings`:

```python
    od19_ai_capability_mode = fields.Selection(
        selection=[
            ("read_only", "อ่านเท่านั้น (A)"),
            ("read_draft", "อ่าน + ร่างเอกสาร (B)"),
        ],
        string="โหมดผู้ช่วย AI (ดีฟอลต์ระบบ)",
        config_parameter="od19_ai.capability_mode",
        default="read_only",
        help="โหมดเริ่มต้นของผู้ช่วย AI สำหรับผู้ใช้ใหม่ "
        "read_only = อ่านข้อมูลเท่านั้น; read_draft = อ่าน + เสนอร่างเอกสาร "
        "(ต้องยืนยันก่อนสร้างจริงเสมอ)",
    )
```

หมายเหตุ: ถ้า `res.config.settings` ยังไม่ import `fields` — มีอยู่แล้ว (บรรทัด 4)

- [ ] **Step 5: ปรับ `views/res_config_settings_views.xml`**

เพิ่ม `div.row` สำหรับฟิลด์โหมด ใใน `div.content-group` (ต่อจาก row ของ `od19_ai_system_prompt`):

```xml
                            <div class="row">
                                <label for="od19_ai_capability_mode" class="col-lg-3 o_light_label"/>
                                <field name="od19_ai_capability_mode"/>
                            </div>
```

เพิ่ม record ใหม่ท้ายไฟล์ (ก่อน `</odoo>`) — โชว์โหมดรายผู้ใช้ในหน้า Preferences:

```xml
    <record id="view_users_form_od19_ai" model="ir.ui.view">
        <field name="name">res.users.form.od19.ai</field>
        <field name="model">res.users</field>
        <field name="inherit_id" ref="base.view_users_form"/>
        <field name="arch" type="xml">
            <xpath expr="//page[@name='preferences']" position="inside">
                <group string="ผู้ช่วย AI">
                    <field name="od19_ai_capability_mode"/>
                </group>
            </xpath>
        </field>
    </record>
```

- [ ] **Step 6: ตรวจ XML well-formed + รันเทสต์**

Run: `venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_ai_assistant/views/res_config_settings_views.xml')"`
Expected: ไม่มี output

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 7: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/models/res_users.py custom_addons/od19_ai_assistant/models/res_config_settings.py custom_addons/od19_ai_assistant/models/__init__.py custom_addons/od19_ai_assistant/views/res_config_settings_views.xml custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add capability mode settings and per-user override"
```

---

## Task 6: External Provider Registry — โครง (`models/od19_ai_provider.py`)

**Files:**
- Create: `custom_addons/od19_ai_assistant/models/od19_ai_provider.py`
- Modify: `custom_addons/od19_ai_assistant/models/__init__.py`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestExternalProvider(TransactionCase):
    def setUp(self):
        super().setUp()
        self.params = self.env["ir.config_parameter"].sudo()
        self.params.search([("key", "=", "od19_ai.external_enabled")]).unlink()

    def test_disabled_by_default(self):
        provider = self.env["od19.ai.provider"]
        self.assertFalse(provider.enabled())
        self.assertEqual(provider.list_tools(), [])

    def test_execute_reports_disabled(self):
        result = self.env["od19.ai.provider"].execute("web_search", {})
        self.assertIn("ยังไม่เปิดใช้งาน", result)

    def test_enabled_flag_reads_parameter(self):
        self.params.set_param("od19_ai.external_enabled", "1")
        self.assertTrue(self.env["od19.ai.provider"].enabled())
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — `KeyError: 'od19.ai.provider'`

- [ ] **Step 3: สร้าง `models/od19_ai_provider.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Layer 3 — external provider registry (structure only, disabled by default).

Phase 2 (internet: web search/fetch) and phase 3 (company systems: ZKTeco,
e-Tax, currency bot, external DB) plug in here. Nothing is enabled now; the
registry merely exists so those phases are additive.
"""

from odoo import api, models


class Od19AiProvider(models.AbstractModel):
    _name = "od19.ai.provider"
    _description = "ทะเบียนผู้ให้บริการภายนอกของผู้ช่วย AI (OD19)"

    @api.model
    def _provider_definitions(self):
        """External tools; populated in phase 2/3. Empty for now."""
        return []

    @api.model
    def enabled(self):
        return bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_ai.external_enabled")
        )

    @api.model
    def list_tools(self):
        if not self.enabled():
            return []
        return list(self._provider_definitions())

    @api.model
    def execute(self, name, arguments):
        if not self.enabled():
            return "ยังไม่เปิดใช้งานเครื่องมือภายนอก: %s" % name
        return "ยังไม่รองรับเครื่องมือภายนอก: %s" % name
```

แก้ `models/__init__.py` — เพิ่ม `from . import od19_ai_provider` ใต้ `od19_ai_capability`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 5: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/models/od19_ai_provider.py custom_addons/od19_ai_assistant/models/__init__.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add external provider registry scaffold (disabled)"
```

---

## Task 7: Draft Confirmation UI (controller route + SSE `draft` + OWL card)

**Files:**
- Modify: `custom_addons/od19_ai_assistant/controllers/main.py`
- Modify: `custom_addons/od19_ai_assistant/static/src/js/od19_ai_chat.js`
- Modify: `custom_addons/od19_ai_assistant/static/src/xml/od19_ai_chat.xml`
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestDraftHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plain_user = cls.env["res.users"].create(
            {
                "name": "OD19 Draft User",
                "login": "od19_draft_user",
                "password": "od19_draft_user",
                "group_ids": [
                    (6, 0, [cls.env.ref("base.group_user").id])
                ],
            }
        )

    def _login(self):
        self.authenticate("od19_draft_user", "od19_draft_user")

    def test_draft_confirm_creates_record(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("od19_ai.capability_mode", "read_draft")
        params.set_param("od19_ai.draft_models", "res.partner")
        self._login()
        before = self.env["res.partner"].search_count([])
        response = self.url_open(
            "/od19_ai/draft/confirm",
            json={"model": "res.partner", "values": {"name": "ร่างผ่าน HTTP"}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(self.env["res.partner"].search_count([]), before)

    def test_draft_confirm_rejected_in_read_only(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("od19_ai.capability_mode", "read_only")
        self._login()
        response = self.url_open(
            "/od19_ai/draft/confirm",
            json={"model": "res.partner", "values": {"name": "ห้าม"}},
        )
        payload = response.json()
        self.assertIn("error", payload)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: FAIL — HTTP 404 ที่ `/od19_ai/draft/confirm`

- [ ] **Step 3: ปรับ `controllers/main.py`**

เพิ่ม import constant:

```python
from ..models.od19_ai_capability import DRAFT_MARKER
```

ใน `_stream_answer` แทนที่ 3 บรรทัดเดิม (บรรทัด ~78-81):

```python
                name, arguments = call
                chat._post_message("assistant", raw)
                yield _sse({"type": "tool", "name": name, "status": "running"})
                chat._post_message("tool", tool_model.execute(name, arguments))
                yield _sse({"type": "tool", "name": name, "status": "done"})
```

ด้วย:

```python
                name, arguments = call
                chat._post_message("assistant", raw)
                yield _sse({"type": "tool", "name": name, "status": "running"})
                result = tool_model.execute(name, arguments)
                if result.startswith(DRAFT_MARKER):
                    draft = json.loads(result[len(DRAFT_MARKER):])
                    chat._post_message(
                        "tool", "เสนอร่างเอกสาร: %s" % draft.get("model_label", "")
                    )
                    yield _sse({"type": "draft", "draft": draft})
                else:
                    chat._post_message("tool", result)
                yield _sse({"type": "tool", "name": name, "status": "done"})
```

เพิ่ม route ใหม่ในคลาส `Od19AiChatController` (ต่อจาก `chat_delete`):

```python
    @http.route("/od19_ai/draft/confirm", type="jsonrpc", auth="user")
    def draft_confirm(self, model=None, values=None, **kwargs):
        record = request.env["od19.ai.capability"].create_draft(
            (model or "").strip(), values or {}
        )
        return {"id": record.id, "name": record.display_name}
```

- [ ] **Step 4: ปรับ `static/src/xml/od19_ai_chat.xml`**

เพิ่มบล็อกการ์ดร่าง ภายใน `o_od19_ai_messages` หลังบล็อก error (ก่อนปิด container ของ messages):

```xml
                    <div class="o_od19_ai_draft" t-if="state.pendingDraft">
                        <div class="o_od19_ai_draft_title">
                            <i class="fa fa-file-text-o me-1"/>
                            ขอสร้างเอกสารร่าง: <t t-out="state.pendingDraft.model_label"/>
                        </div>
                        <ul class="o_od19_ai_draft_values">
                            <t t-foreach="Object.entries(state.pendingDraft.values)"
                               t-as="entry" t-key="entry[0]">
                                <li><t t-out="entry[0]"/>: <t t-out="entry[1]"/></li>
                            </t>
                        </ul>
                        <div class="o_od19_ai_draft_actions">
                            <button type="button" class="btn btn-primary btn-sm"
                                    t-on-click="confirmDraft">ยืนยันการสร้าง</button>
                            <button type="button" class="btn btn-secondary btn-sm"
                                    t-on-click="cancelDraft">ยกเลิก</button>
                        </div>
                    </div>
```

เพิ่ม field ใน state ของ `setup()` และเมธอดใหม่:

```js
// inside setup(): extend the existing useState object with:
        state = useState({
            chats: [],
            activeChatId: null,
            messages: [],
            draft: "",
            streaming: false,
            streamText: "",
            toolChips: [],
            error: "",
            pendingDraft: null,
        });
```

```js
    async confirmDraft() {
        const pending = this.state.pendingDraft;
        if (!pending) {
            return;
        }
        try {
            const result = await rpc("/od19_ai/draft/confirm", {
                model: pending.model,
                values: pending.values,
            });
            this.notification.add(
                `สร้างเอกสารร่างแล้ว: ${result.name}`,
                { type: "success" }
            );
            this.state.pendingDraft = null;
        } catch (error) {
            this.state.error = error.message || "ยืนยันร่างไม่สำเร็จ";
        }
    }

    cancelDraft() {
        this.state.pendingDraft = null;
    }
```

ใน `onStreamEvent(event)` เพิ่ม case `draft`:

```js
            case "draft":
                this.state.pendingDraft = event.draft;
                this.state.streamText = "";
                break;
```

- [ ] **Step 5: ตรวจไวยากรณ์ JS + รันเทสต์**

Run: `venv19\Scripts\python.exe -m py_compile custom_addons/od19_ai_assistant/controllers/main.py`
Expected: ไม่มี output

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 6: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/controllers/main.py custom_addons/od19_ai_assistant/static/src/js/od19_ai_chat.js custom_addons/od19_ai_assistant/static/src/xml/od19_ai_chat.xml custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "feat(od19_ai_assistant): add two-step draft confirmation in chat UI"
```

---

## Task 8: Performance Guards — พิสูจน์ด้วยเทสต์

**Files:**
- Test: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: เขียนเทสต์ประสิทธิภาพ (จะผ่านทันทีถ้า cache ทำงาน; ถ้าไม่ cache จะล้มเหลว)**

เพิ่มท้ายไฟล์ `tests/test_ai_assistant.py`:

```python
@tagged("post_install", "-at_install")
class TestPerformanceGuards(TransactionCase):
    def test_list_models_metadata_is_cached(self):
        tools = self.env["od19.ai.tool"]
        tools._run_list_models({"limit": 5})  # warm the ACL + tool caches
        with self.assertQueryCount(0):
            tools._run_list_models({"limit": 5})

    def test_describe_model_runs_no_query(self):
        tools = self.env["od19.ai.tool"]
        tools._run_describe_model({"model": "res.partner"})  # warm registry
        with self.assertQueryCount(0):
            tools._run_describe_model({"model": "res.partner"})

    def test_search_records_never_exceeds_cap(self):
        self.env["res.partner"].create([{"name": "cap %s" % i} for i in range(25)])
        result = self.env["od19.ai.tool"].execute(
            "search_records",
            {"model": "res.partner", "fields": ["name"], "limit": 999},
        )
        lines = [line for line in result.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(lines), 20)

    def test_prompt_index_is_bounded(self):
        tool_model = self.env["od19.ai.tool"]
        self.assertLessEqual(
            len(tool_model.prompt_index()), tool_model.MAX_INDEX_CHARS
        )
```

- [ ] **Step 2: รันเทสต์**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: PASS — 0 failed, 0 error(s)

- [ ] **Step 3: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "test(od19_ai_assistant): cover metadata caching and result caps"
```

---

## Task 9: Regression + Version Bump + Final Verification

**Files:**
- Modify: `custom_addons/od19_ai_assistant/__manifest__.py` (bump version)

- [ ] **Step 1: Bump version**

แก้ `__manifest__.py`: `"version": "19.0.1.5.0"` → `"version": "19.0.2.0.0"`

- [ ] **Step 2: ตรวจ static ทั้งโมดูล**

Run:
```powershell
venv19\Scripts\python.exe -m py_compile custom_addons/od19_ai_assistant/models/od19_ai_tool_generic.py custom_addons/od19_ai_assistant/models/od19_ai_tool_index.py custom_addons/od19_ai_assistant/models/od19_ai_capability.py custom_addons/od19_ai_assistant/models/od19_ai_tool_log.py custom_addons/od19_ai_assistant/models/od19_ai_provider.py custom_addons/od19_ai_assistant/models/res_users.py custom_addons/od19_ai_assistant/lib/orm_guard.py
```
Expected: ไม่มี output

- [ ] **Step 3: รัน Unit Test ทั้งโมดูล (เกณฑ์ผ่านขั้นสุดท้าย)**

Run: `.\run-tests.ps1 -Module od19_ai_assistant`
Expected: `0 failed, 0 error(s)` — รวมเทสต์เดิม 25 ตัว + เทสต์ใหม่ทั้งหมด

- [ ] **Step 4: Commit**

```bash
git add -- custom_addons/od19_ai_assistant/__manifest__.py
git commit -m "chore(od19_ai_assistant): bump version to 19.0.2.0.0 for AI coverage"
```

---

## Self-Review

**1. Spec coverage**

| Spec | Task ที่รองรับ |
|---|---|
| §6.1 Generic Explorer (`list_models`/`describe_model`/`search_records`/`aggregate_records`) | Task 2 |
| §6.2 Curated Fast-path (คง 11 ตัวเดิม) | Task 2 (คง `_tool_definitions` + `prompt_catalog`) |
| §6.3 Progressive Disclosure (`prompt_index` / `tool_help`) | Task 3 |
| §6.4 Domain Guard (operator/field/limit/offset) | Task 1 + Task 2 |
| §7.1 Capability Mode (read_only / read_draft) | Task 4 |
| §7.2 กฎ draft (สิทธิ์จริง/whitelist/draft/ยืนยัน 2 จังหวะ) | Task 4 + Task 7 |
| §7.3 Audit `od19.ai.tool.log` | Task 4 |
| §8 External Providers registry (ปิดดีฟอลต์) | Task 6 |
| §9 Performance Guards (cache/cap/timeout/no idle/token budget) | Task 2 (cache) + Task 3 (budget cap) + Task 8 (พิสูจน์) |
| §10.1 ฟิลด์ `res.users` / `res.config.settings` | Task 5 |
| §10.2 โมเดล `od19.ai.tool.log` + record rule | Task 4 |
| §11 Settings UI (โหมด + คงฟิลด์เดิม) | Task 5 |
| §12 Data Flow (index → tool → guard → execute → audit → loop) | Task 2/3/4/7 |
| §13 Security (ACL log, ไม่ sudo, ห้าม post/confirm/pay/approve) | Task 4 |
| §14 Testing + คำสั่งรัน | Task 1–9 (ทุก Run step) |
| §15 File Layout | ทุก Task (ตรงกับตาราง File Structure) |
| §16 Defaults (read_only, cap 20/60, whitelist, operators) | Task 1/2/4 (ค่าคงที่ตรงตามตาราง) |
| §17 Design Decisions | Task 2/3/4/6 (คำอธิบายใน docstring) |
| §18 Risks RS1–RS6 | RS1 (curated+guard) Task 1/2 · RS2 (streaming+cap) Task 8 · RS3 (สิทธิ์จริง+audit) Task 4 · RS4 (whitelist+ยืนยัน) Task 4/7 · RS5 (cache clear on reload) Task 2 · RS6 (generic เป็นหลัก) Task 2 |
| §19 เฟส 1.1–1.7 | Task 1↔1.1 · Task 2↔1.2 · Task 3↔1.3 · Task 4↔1.4 · Task 8↔1.5 · Task 5+7↔1.6 · Task 9↔1.7 |

ไม่มี requirement ที่ไม่มี task รองรับ (เฟส 2/3 เป็น out-of-scope ตาม §4.2 — เตรียมโครงไว้ใน Task 6)

**2. Placeholder scan:** ไม่มี "TBD/TODO/implement later/Add appropriate error handling/Similar to Task N" — ทุก step มีโค้ดจริงครบและ path ระบุชัด

**3. Type consistency (ตรวจชื่อเมธอด/ค่าคงที่ให้ตรงกันทุก Task)**
- `orm_guard.safe_limit(value, default=, cap=)`, `safe_offset`, `check_model`, `check_field`, `validate_fields`, `validate_order`, `validate_groupby`, `validate_aggregates`, `validate_domain`, `OrmGuardError` — ใช้ชื่อเดียวกันใน Task 1/2/4
- `od19.ai.tool.all_tools()` รวม `_tool_definitions` + `_generic_definitions` (Task 2) + `_index_definitions` (Task 3) + `_draft_definitions` (Task 4) — ชื่อเมธอดตรงกัน
- `_readable_model_names` (Task 2) ถูกใช้ใน `_run_list_models` (Task 2) และเทสต์ Task 8
- `MAX_INDEX_CHARS` (Task 3) ถูกอ้างในเทสต์ Task 3 และ Task 8
- `DRAFT_MARKER` นิยามใน `models/od19_ai_capability.py` (Task 4) และ import ใน `controllers/main.py` (Task 7)
- `capability_mode()` / `system_mode()` / `can_draft()` / `preview_draft()` / `create_draft()` / `_sanitize_values()` / `_redact_arguments()` / `log_call()` — นิยาม Task 4, เรียกใช้ Task 4/5/7
- `od19_ai_capability_mode` (res.users + res.config.settings) และ `od19_ai.capability_mode` / `od19_ai.draft_models` / `od19_ai.external_enabled` (config parameters) — สะกดตรงกันทุก Task
- `tool_help` / `full_schema` / `prompt_index` (Task 3) ตรงกับที่ `_build_system_prompt` (Task 3) เรียก

ไม่มีข้อขัดแย้ง (แก้ inline แล้ว)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-10-od19-ai-assistant-coverage.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
