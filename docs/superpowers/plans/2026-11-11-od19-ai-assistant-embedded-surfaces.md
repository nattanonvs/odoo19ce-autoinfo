# Embedded AI Surfaces (od19_ai_assistant) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยนผู้ช่วย AI `od19_ai_assistant` จาก "แอปที่ต้องไปเปิด" ให้เป็น "ผู้ช่วยที่อยู่ตรงหน้าจอที่กำลังทำงาน" โดยแยก **สมองกลาง** (`od19.ai.assistant`) ออกจาก UI แล้วเพิ่ม 2 พื้นผิวแรก (ปุ่ม AI บน systray + แผงช่วยเหลือข้างฟอร์ม) ที่อ่านบริบทหน้าจอโดยให้ **server เป็นผู้ตรวจสิทธิ์เสมอ**

**Architecture:** `od19.ai.assistant` เป็น `models.AbstractModel` ตัวเดียวที่ประกอบ system prompt + tool loop + guard + audit (ไม่มีตาราง ไม่มี UI) — controllers เหลือหน้าที่ transport เท่านั้น. บริบทหน้าจอเป็น **optional parameter** (`model`/`res_id`/`view_type`): client ส่งขึ้นไปแค่ "ชี้เป้า" ส่วน server resolve ค่าจริงด้วยสิทธิ์ผู้ใช้ (ไม่ `sudo`) ถ้าไม่มีสิทธิ์ → คืน `None` ไม่ throw. พื้นผิวทั้งหมดใช้ OWL registry (`systray`, `main_components`, `actions`) เป็น **additive** ไม่แก้ XML view ของโมดูลอื่นแม้แต่ไฟล์เดียว

**Tech Stack:** Odoo 19 CE · Python ORM (`models.AbstractModel`, `has_access()`, `ir.model.access`) · OWL 2 (`Component`, `useState`, `useRef`, `onPatched`, `useHotkey`, `reactive`, `registry`, `rpc`) · SSE ผ่าน `fetch` + `TextDecoder` · `TransactionCase` / `HttpCase` + `unittest.mock.patch`

**อ้างอิง:** Spec `docs/superpowers/specs/2026-11-11-od19-ai-assistant-embedded-surfaces-design.md` (§5–§17) · `docs/superpowers/plans/2026-11-10-od19-ai-assistant-coverage.md` (แม่แบบรูปแบบ) · AGENTS.md (ห้ามแตะ core · Conventional Commits · ห้าม `git add -A` · 1 commit = 1 โดเมน)

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_ai_assistant/models/od19_ai_assistant.py` | สมองกลาง Shared Brain (context + config + prompt + tool loop) | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/models/__init__.py` | import โมเดลใหม่ | แก้ |
| `custom_addons/od19_ai_assistant/models/od19_ai_chat.py` | บางลง — เก็บ persistence + delegate ไปสมองกลาง | แก้ |
| `custom_addons/od19_ai_assistant/models/res_config_settings.py` | import `PROVIDER_PRESETS` จากที่ใหม่ | แก้ |
| `custom_addons/od19_ai_assistant/controllers/main.py` | เหลือ transport + เพิ่ม `/od19_ai/ask` + `/od19_ai/suggest` | แก้ |
| `custom_addons/od19_ai_assistant/static/src/js/ai_context.js` | อ่านบริบทหน้าจอจาก web client | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/static/src/js/ai_panel.js` | แผงแชทใช้ร่วม + state + docking | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/static/src/js/systray_item.js` | ปุ่ม AI บน systray | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml` | เทมเพลตแผง | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/static/src/xml/systray_item.xml` | เทมเพลตปุ่ม systray | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/static/src/scss/od19_ai_panel.scss` | สไตล์แผง + docking | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/__manifest__.py` | เพิ่ม assets + bump `19.0.3.0.0` | แก้ |
| `custom_addons/od19_ai_assistant/tests/test_ai_assistant_service.py` | เทสต์สมองกลาง (ask/stream/suggest/confirm) | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/tests/test_ai_context.py` | เทสต์ `build_context` / `context_brief` | **สร้างใหม่** |
| `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py` | อัปเดต patch target + เพิ่มเทสต์ HTTP `ask` | แก้ |
| `custom_addons/od19_ai_assistant/tests/__init__.py` | import เทสต์ใหม่ 2 ตัว | แก้ |

> **ไม่แตะ:** `models/od19_ai_tool.py`, `models/od19_ai_tool_generic.py`, `models/od19_ai_tool_index.py`, `models/od19_ai_capability.py`, `models/od19_ai_tool_log.py`, `models/od19_ai_provider.py`, `lib/orm_guard.py`, `lib/client.py`, `static/src/js/od19_ai_chat.js`, `static/src/xml/od19_ai_chat.xml`, `security/*`, `views/*`

---

## Decisions (locked — อย่าเปลี่ยนระหว่างลงมือ)

1. **ย้าย symbol ไปสมองกลางจริง ไม่ทำ shim** — `PARAM_PREFIX`, `MAX_TOOL_ROUNDS`, `TOOL_PROTOCOL`, `DEFAULTS`, `PROVIDER_PRESETS` ถูกประกาศที่ `models/od19_ai_assistant.py` เพียงที่เดียว แล้ว **อัปเดต import** ที่ `res_config_settings.py` (`from .od19_ai_assistant import PROVIDER_PRESETS`) ให้ชี้ที่ใหม่
2. **`od19.ai.chat` เก็บ thin delegate ไว้** เพื่อคง surface ที่เทสต์เดิมเรียกอยู่ (`_get_param`, `_get_ai_config`, `_build_system_prompt`, `_parse_tool_call`, `_build_messages`) — delegate ไปสมองกลางทุกตัว; `_post_message` ยังเป็นของจริงบน `od19.ai.chat` (มันคือ persistence ของข้อความ)
3. **อัปเดต patch target ในเทสต์เดิม** — เพราะ `chat_completion` / `chat_completion_stream` ถูกเรียกจาก `models/od19_ai_assistant.py` แล้ว ค่าคงที่ต้องเปลี่ยนเป็น
   `CHAT_COMPLETION = "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion"`
   `STREAM_COMPLETION = "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion_stream"`
   (`AI_CLIENT_ERROR` คงเดิม) — ห้ามลบ/เปลี่ยนชื่อเทสต์ใดใน `test_ai_assistant.py`
4. **`assistant.ask()` คืน `dict`** `{"answer": str|None, "error": str|None, "chat_id": int|None}` แทนการ raise — เพื่อให้ทั้ง JSON transport และ legacy `action_ask()` แสดงผลได้ในสำนวนของตัวเอง และทำให้ write ของ `chat` **ไม่ถูก rollback** (พฤติกรรมเดิมของ `action_ask` ที่เขียน `state=error` แล้ว commit)
5. **`assistant.stream()` เป็น generator ที่ yield `dict`** (ไม่เปิด cursor เอง) — controller ยังคงเป็นเจ้าของ `registry.cursor()` + `Environment` ตามเดิม เพราะ cursor ของ request ถูกปิดก่อน WSGI consume generator
6. **`chat.action_ask()` ยังคง signature + return เดิม** — สำเร็จคืน `True`, error คืน action `display_notification` (เทสต์เดิม `test_action_ask_records_error` ตรวจ `result.get("tag")`)
7. **ตรวจสิทธิ์ด้วย `has_access("read")`** ทั้งระดับโมเดลและระดับเรกคอร์ด — `check_access_rights()` / `check_access_rule()` เป็น `@api.deprecated` ตั้งแต่ 18.0 (`odoo/orm/models.py:4166-4189`) จึง **ห้ามใช้**; ตรวจโมเดลติดตั้งด้วย membership `model_name in self.env` (ไม่แตะ `ir.model` เพื่อเลี่ยง ACL)
8. **`DEFAULTS["timeout"]` คงเป็น 60** — `test_config_falls_back_to_defaults` assert `timeout == 60`
9. **คีย์ลัดเปิด/ปิดแผง = `Alt+Shift+P`** (ไม่ใช่ `Alt+Shift+A`) — ยืนยันแล้วว่า `alt+shift+a` ถูกใช้โดยเมนูกิจกรรมของ mail (`addons/mail/static/src/core/web/activity_menu.js:28`); `alt+shift` ที่ถูกใช้แล้วคือ `a,i,u,t,v,x` จึงเลือก `p` (P = Panel) ซึ่งว่าง
10. **`/od19_ai/ask` เป็น JSON-RPC (ไม่สตรีม) ตามสเปก §6/§11/§12** — เป็น API  synchronous ที่เทสต์ครอบคลุมและพร้อมให้พื้นผิวอนาคต (mobile/CLI) ใช้; แผง UI ใช้เส้นทางสตรีม `/od19_ai/chat/stream` (รับ `model`/`res_id`/`view_type` เพิ่ม) เพื่อ UX ที่ดีกว่า — ไม่เพิ่ม fallback อัตโนมัติ
11. **บริบทเพดาน** `max_chars = 800`, ฟิลด์ที่ส่ง ≤ 30, snippet ≤ 500 ตัวอักษร, ชิป ≤ 4 (`CHIP_LIMIT = 4`), systray `sequence = 50`
12. **ไม่เพิ่ม cron/worker/ir.cron** และ **ไม่เพิ่มตาราง/ACL ใหม่** (`od19.ai.assistant` เป็น AbstractModel)
13. **ห้าม post/confirm/pay/approve** — `confirm_draft()` delegate ไป `od19.ai.capability.create_draft()` เดิม (บังคับ draft + ยืนยัน 2 จังหวะ)

## Test-Run Convention

- รัน Unit Test (ตาม AGENTS.md §6 — DB ทดสอบส่วนตัว): `.\run-tests.ps1 -Module od19_ai_assistant` → เป้าหมาย **0 failed / 0 error(s)**
- ตรวจไวยากรณ์เร็วระหว่างทาง: `venv19\Scripts\python.exe -m py_compile <path>` → ไม่มี output
- ตรวจ XML well-formed: `venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('<path>')"` → ไม่มี output
- ตรวจ JS ไวยากรณ์เร็ว: `node --check <path>` (ถ้ามี node) มิฉะนั้นพึ่งการโหลด asset ตอน manual test
- **ห้าม commit จนกว่าเทสต์ทั้งโมดูลจะผ่าน** (AGENTS.md §4)
- ทุก commit ใช้ `git add -- <path>` เจาะจงไฟล์ ห้าม `git add -A`

---

## Task 1: สมองกลาง `od19.ai.assistant` (Shared Brain)

**Files:**
- Create: `custom_addons/od19_ai_assistant/models/od19_ai_assistant.py`
- Modify: `custom_addons/od19_ai_assistant/models/__init__.py`
- Create: `custom_addons/od19_ai_assistant/tests/test_ai_assistant_service.py`
- Modify: `custom_addons/od19_ai_assistant/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

สร้างไฟล์ `tests/test_ai_assistant_service.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

CHAT_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion"
)
STREAM_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion_stream"
)


@tagged("post_install", "-at_install")
class TestOd19AiAssistantService(TransactionCase):
    def _brain(self):
        return self.env["od19.ai.assistant"]

    # ------------------------------------------------------------------
    # Config / prompt / parse (ย้ายมาแล้วยังให้ผลเหมือนเดิม)
    # ------------------------------------------------------------------
    def test_config_defaults_unchanged(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=like", "od19_ai.%")]
        ).unlink()
        config = self._brain()._get_ai_config()
        self.assertEqual(config["provider"], "ollama")
        self.assertEqual(config["timeout"], 60)

    def test_parse_tool_call_delegated(self):
        self.assertEqual(
            self._brain()._parse_tool_call(
                '{"tool": "search_partners", "arguments": {"keyword": "x"}}'
            ),
            ("search_partners", {"keyword": "x"}),
        )
        self.assertIsNone(self._brain()._parse_tool_call("สวัสดีครับ"))

    # ------------------------------------------------------------------
    # ask()
    # ------------------------------------------------------------------
    def test_ask_without_chat_returns_answer(self):
        with patch(CHAT_COMPLETION, return_value="สวัสดีครับ"):
            result = self._brain().ask("สวัสดี")
        self.assertEqual(result["answer"], "สวัสดีครับ")
        self.assertIsNone(result["error"])

    def test_ask_empty_question_raises(self):
        with self.assertRaises(UserError):
            self._brain().ask("   ")

    def test_ask_with_chat_persists_history(self):
        chat = self.env["od19.ai.chat"].create({})
        with patch(CHAT_COMPLETION, return_value="ตอบ"):
            self._brain().ask("คำถาม", chat=chat)
        self.assertEqual(chat.state, "done")
        self.assertEqual(len(chat.message_ids), 2)

    def test_ask_runs_tool_once_then_answers(self):
        self.env["res.partner"].create({"name": "บริษัท ทดสอบ จำกัด"})
        calls = {"n": 0}

        def fake(base_url, model, messages, api_key=None, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return '{"tool": "search_partners", "arguments": {"keyword": "ทดสอบ"}}'
            return "พบ บริษัท ทดสอบ จำกัด"

        with patch(CHAT_COMPLETION, side_effect=fake):
            result = self._brain().ask("หาคู่ค้าทดสอบ")
        self.assertEqual(calls["n"], 2)
        self.assertIn("บริษัท ทดสอบ จำกัด", result["answer"])

    def test_ask_exceeding_rounds_returns_fallback(self):
        def always_tool(base_url, model, messages, api_key=None, timeout=None):
            return '{"tool": "search_partners", "arguments": {}}'

        with patch(CHAT_COMPLETION, side_effect=always_tool):
            result = self._brain().ask("ถาม")
        self.assertIn("หลายรอบเกินไป", result["answer"])

    def test_ask_error_marks_chat_and_returns_error(self):
        from odoo.addons.od19_ai_assistant.lib.client import AiClientError

        chat = self.env["od19.ai.chat"].create({})
        with patch(CHAT_COMPLETION, side_effect=AiClientError("boom")):
            result = self._brain().ask("test", chat=chat)
        self.assertEqual(chat.state, "error")
        self.assertEqual(result["error"], "boom")
        self.assertIsNone(result["answer"])

    # ------------------------------------------------------------------
    # stream()
    # ------------------------------------------------------------------
    def test_stream_yields_delta_then_done(self):
        chat = self.env["od19.ai.chat"].create({})

        def fake_stream(base_url, model, messages, api_key=None, timeout=None):
            for token in ("สวัสดี", "ครับ"):
                yield token

        with patch(STREAM_COMPLETION, side_effect=fake_stream):
            events = list(self._brain().stream("สวัสดี", chat=chat))
        types = [e["type"] for e in events]
        self.assertIn("delta", types)
        self.assertEqual(types[-1], "done")
        self.assertEqual(chat.state, "done")

    # ------------------------------------------------------------------
    # suggest_actions() / confirm_draft()
    # ------------------------------------------------------------------
    def test_suggest_actions_known_model(self):
        chips = self._brain().suggest_actions({"model": "sale.order"})
        self.assertTrue(chips)
        self.assertLessEqual(len(chips), 4)

    def test_suggest_actions_unknown_model_falls_back(self):
        chips = self._brain().suggest_actions({"model": "no.such.model"})
        self.assertTrue(chips)

    def test_suggest_actions_empty_context(self):
        self.assertTrue(self._brain().suggest_actions(None))

    def test_confirm_draft_delegates(self):
        record = self._brain().confirm_draft("res.partner", {"name": "ร่างใหม่"})
        self.assertTrue(record.exists())
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: FAIL — `od19.ai.assistant` ไม่มีในระบบ (`KeyError` / `AttributeError`)

- [ ] **Step 3: สร้าง `models/od19_ai_assistant.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Shared Brain for the OD19 AI assistant.

A single, UI-free service that owns: configuration resolution, system-prompt
assembly, the (prompt-based) tool loop, page-context resolution and the
convenience endpoints every surface calls. Surfaces (full-page chat, systray
panel, form help panel) only supply a question plus an *optional* page context
and render whatever comes back — they never touch the loop.
"""

import json
import logging
import re

from odoo import api, models, tools
from odoo.exceptions import UserError

from ..lib.client import AiClientError, chat_completion, chat_completion_stream
from .od19_ai_capability import DRAFT_MARKER

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "od19_ai"

# Maximum number of tool-call round-trips before we force a plain answer.
MAX_TOOL_ROUNDS = 5

# Upper bound for the page-context payload (privacy + prompt budget).
CONTEXT_MAX_FIELDS = 30
CONTEXT_SNIPPET_CHARS = 500
CONTEXT_BRIEF_CHARS = 800
CHIP_LIMIT = 4

# Appended to the system prompt when tools are available. The assistant is
# asked to answer with a single JSON object to request data, which keeps the
# protocol model-agnostic (Ollama/Qwen and any OpenAI-compatible endpoint).
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

# Used when neither ir.config_parameter nor odoo.conf provides a value.
DEFAULTS = {
    "provider": "ollama",
    "base_url": "http://localhost:11434/v1",
    "model": "qwen2.5:7b",
    "system_prompt": (
        "You are a helpful assistant for a Thai accounting ERP (Odoo 19). "
        "Answer in Thai unless asked otherwise."
    ),
    "timeout": 60,
}

PROVIDER_PRESETS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
}

# Fields worth mentioning in a brief, in priority order. Only names are sent
# (no values), which keeps the payload small and privacy-friendly.
CONTEXT_PREFERRED_FIELDS = (
    "name",
    "state",
    "partner_id",
    "date",
    "date_order",
    "invoice_date",
    "reference",
    "amount_total",
    "amount_untaxed",
    "amount_residual",
    "currency_id",
    "user_id",
)

# Cheap contextual quick-commands per model, plus a neutral fallback.
SUGGESTIONS = {
    "sale.order": [
        "สรุปออร์เดอร์นี้",
        "ลูกค้ารายนี้ซื้ออะไรบ้าง",
        "ทำไมสถานะยังไม่ยืนยัน",
    ],
    "purchase.order": [
        "สรุปใบสั่งซื้อนี้",
        "ผู้ขายรายนี้เป็นใคร",
        "สถานะการรับสินค้าเป็นอย่างไร",
    ],
    "account.move": [
        "สรุปใบแจ้งหนี้นี้",
        "ยอดคงค้างเท่าไร",
        "ภาษีในเอกสารนี้เท่าไร",
    ],
    "res.partner": [
        "คู่ค้ารายนี้เป็นใคร",
        "ยอดค้างชำระเท่าไร",
        "เอกสารล่าสุดมีอะไร",
    ],
    "product.template": [
        "สินค้านี้คงเหลือเท่าไร",
        "ราคาขายเท่าไร",
    ],
    "project.task": [
        "งานนี้คืออะไร",
        "กำหนดเสร็จเมื่อไร",
    ],
}
DEFAULT_SUGGESTIONS = ("ค้นหาข้อมูลที่เกี่ยวข้อง", "สรุปภาพรวมที่ฉันควรรู้")


class Od19AiAssistant(models.AbstractModel):
    _name = "od19.ai.assistant"
    _description = "สมองกลางของผู้ช่วย AI (OD19)"

    # ------------------------------------------------------------------
    # Configuration resolution
    # ------------------------------------------------------------------
    @api.model
    def _get_param(self, key, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("%s.%s" % (PARAM_PREFIX, key), default)
        )

    @api.model
    def _get_ai_config(self):
        """Resolve AI settings: ir.config_parameter -> odoo.conf -> default."""

        def resolve(key):
            param = self._get_param(key)
            if param not in (None, ""):
                return param
            return tools.config.get("%s_%s" % (PARAM_PREFIX, key))

        provider = resolve("provider") or DEFAULTS["provider"]
        preset = PROVIDER_PRESETS.get(provider, {})

        timeout_raw = resolve("timeout")
        try:
            timeout = int(timeout_raw) if timeout_raw else DEFAULTS["timeout"]
        except (TypeError, ValueError):
            timeout = DEFAULTS["timeout"]

        return {
            "provider": provider,
            "base_url": resolve("base_url")
            or preset.get("base_url")
            or DEFAULTS["base_url"],
            "model": resolve("model") or preset.get("model") or DEFAULTS["model"],
            "api_key": resolve("api_key") or "",
            "system_prompt": resolve("system_prompt") or DEFAULTS["system_prompt"],
            "timeout": timeout,
        }

    # ------------------------------------------------------------------
    # Prompt / message helpers
    # ------------------------------------------------------------------
    @api.model
    def _build_messages(self, chat, system_prompt, question=None):
        """Return the OpenAI-style message list.

        With ``chat`` the full stored history is replayed; without it a
        one-shot ``system + user`` pair is produced (stateless surfaces).
        """
        messages = [{"role": "system", "content": system_prompt}]
        if chat:
            for msg in chat.message_ids.sorted("id"):
                if msg.role == "tool":
                    messages.append(
                        {
                            "role": "user",
                            "content": "[ผลลัพธ์จากเครื่องมือ]\n%s" % msg.content,
                        }
                    )
                elif msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
        elif question:
            messages.append({"role": "user", "content": question})
        return messages

    @api.model
    def _build_system_prompt(self, base_prompt, ctx=None):
        """Append the compact tool index (and optional page brief)."""
        prompt = base_prompt
        index = self.env["od19.ai.tool"].prompt_index()
        if index:
            prompt = prompt + TOOL_PROTOCOL % index
        brief = self.context_brief(ctx) if ctx else ""
        if brief:
            prompt = prompt + "\n\n" + brief
        return prompt

    @api.model
    def _parse_tool_call(self, text):
        """Return ``(name, arguments)`` if ``text`` requests a tool call."""
        if not text:
            return None
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`").strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
        data = None
        try:
            data = json.loads(candidate)
        except (TypeError, ValueError):
            match = re.search(r"\{.*\}", candidate, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except (TypeError, ValueError):
                    data = None
        if isinstance(data, dict) and data.get("tool"):
            return data["tool"], data.get("arguments") or {}
        return None

    # ------------------------------------------------------------------
    # Page context
    # ------------------------------------------------------------------
    @api.model
    def _context_fields(self, model_name):
        fields_ = self.env[model_name]._fields
        return [name for name in CONTEXT_PREFERRED_FIELDS if name in fields_][
            :CONTEXT_MAX_FIELDS
        ]

    @api.model
    def build_context(self, model, res_id, view_type, snippet=None):
        """Resolve page context with the *current user's* rights.

        Returns a small dict, or ``None`` when the target is unknown or not
        readable — never raises, never leaks.
        """
        if not model or model not in self.env:
            return None
        model_obj = self.env[model]
        if not model_obj.has_access("read"):
            return None
        base = {
            "model": model,
            "res_id": False,
            "view_type": view_type or "list",
            "display_name": "",
            "fields": self._context_fields(model),
            "snippet": (snippet or "")[:CONTEXT_SNIPPET_CHARS],
        }
        if not res_id:
            return base
        record = model_obj.browse(int(res_id))
        if not record.exists() or not record.has_access("read"):
            return None
        base["res_id"] = record.id
        base["view_type"] = view_type or "form"
        base["display_name"] = record.display_name or ""
        return base

    @api.model
    def context_brief(self, ctx, max_chars=CONTEXT_BRIEF_CHARS):
        """Render a context dict as a short prompt suffix."""
        if not ctx:
            return ""
        lines = [
            "[บริบทหน้าจอปัจจุบัน]",
            "โมเดล: %s" % ctx.get("model", ""),
            "มุมมอง: %s" % ctx.get("view_type", ""),
        ]
        if ctx.get("res_id"):
            lines.append("รหัสเอกสาร: %s" % ctx["res_id"])
        if ctx.get("display_name"):
            lines.append("เอกสารที่เปิดอยู่: %s" % ctx["display_name"])
        if ctx.get("fields"):
            lines.append("ฟิลด์ที่สนใจ: %s" % ", ".join(ctx["fields"]))
        if ctx.get("snippet"):
            lines.append("เนื้อหาโดยย่อ: %s" % ctx["snippet"])
        return "\n".join(lines)[:max_chars]

    # ------------------------------------------------------------------
    # Quick commands
    # ------------------------------------------------------------------
    @api.model
    def suggest_actions(self, ctx):
        """Return model-aware quick-command chips (bounded)."""
        model = (ctx or {}).get("model")
        chips = SUGGESTIONS.get(model) or list(DEFAULT_SUGGESTIONS)
        return list(chips)[:CHIP_LIMIT]

    # ------------------------------------------------------------------
    # Answering
    # ------------------------------------------------------------------
    @api.model
    def ask(self, question, ctx=None, chat=None):
        """Run the tool loop once and return a structured result dict."""
        question = (question or "").strip()
        if not question:
            raise UserError("กรุณากรอกคำถามก่อน")

        config = self._get_ai_config()
        system_prompt = self._build_system_prompt(config["system_prompt"], ctx=ctx)
        tool_model = self.env["od19.ai.tool"]

        if chat:
            chat._post_message("user", question)
        messages = self._build_messages(chat, system_prompt, question=question)

        answer = None
        try:
            for _round in range(MAX_TOOL_ROUNDS):
                raw = chat_completion(
                    config["base_url"],
                    config["model"],
                    messages,
                    api_key=config["api_key"],
                    timeout=config["timeout"],
                )
                call = self._parse_tool_call(raw)
                if not call:
                    answer = raw
                    break
                name, arguments = call
                if chat:
                    chat._post_message("assistant", raw)
                result = tool_model.execute(name, arguments)
                if chat:
                    chat._post_message("tool", result)
                messages.append(
                    {
                        "role": "user",
                        "content": "[ผลลัพธ์จากเครื่องมือ]\n%s" % result,
                    }
                )
            else:
                answer = (
                    "ขออภัย ระบบเรียกใช้เครื่องมือหลายรอบเกินไป "
                    "กรุณาตั้งคำถามให้เฉพาะเจาะจงมากขึ้น"
                )
        except AiClientError as exc:
            if chat:
                chat.write({"state": "error"})
                chat._post_message("system", "เกิดข้อผิดพลาด: %s" % exc)
            return {
                "answer": None,
                "error": str(exc),
                "chat_id": chat.id if chat else None,
            }

        if chat:
            chat._post_message("assistant", answer)
            chat.write({"state": "done", "model_used": config["model"]})
        return {
            "answer": answer,
            "error": None,
            "chat_id": chat.id if chat else None,
        }

    @api.model
    def stream(self, question, ctx=None, chat=None):
        """Yield SSE-ready event dicts for one answer.

        The caller owns the database cursor (see ``controllers/main.py``):
        Odoo closes the request cursor before the WSGI server consumes the
        generator, so the generator must run inside its own cursor.
        """
        question = (question or "").strip()
        if not question:
            yield {"type": "error", "message": "กรุณากรอกคำถามก่อน"}
            return

        config = self._get_ai_config()
        system_prompt = self._build_system_prompt(config["system_prompt"], ctx=ctx)
        tool_model = self.env["od19.ai.tool"]

        if chat:
            chat.write({"state": "draft", "prompt": False})
            chat._post_message("user", question)
        messages = self._build_messages(chat, system_prompt, question=question)

        try:
            answer = None
            for _round in range(MAX_TOOL_ROUNDS):
                buffer = []
                for token in chat_completion_stream(
                    config["base_url"],
                    config["model"],
                    messages,
                    api_key=config["api_key"],
                    timeout=config["timeout"],
                ):
                    buffer.append(token)
                    yield {"type": "delta", "content": token}

                raw = "".join(buffer)
                call = self._parse_tool_call(raw)
                if not call:
                    answer = raw
                    yield {"type": "round_end", "kind": "answer"}
                    break

                yield {"type": "round_end", "kind": "tool"}
                name, arguments = call
                if chat:
                    chat._post_message("assistant", raw)
                yield {"type": "tool", "name": name, "status": "running"}
                result = tool_model.execute(name, arguments)
                if result.startswith(DRAFT_MARKER):
                    draft = json.loads(result[len(DRAFT_MARKER):])
                    if chat:
                        chat._post_message(
                            "tool",
                            "เสนอร่างเอกสาร: %s" % draft.get("model_label", ""),
                        )
                    yield {"type": "draft", "draft": draft}
                elif chat:
                    chat._post_message("tool", result)
                messages.append(
                    {
                        "role": "user",
                        "content": "[ผลลัพธ์จากเครื่องมือ]\n%s" % result,
                    }
                )
                yield {"type": "tool", "name": name, "status": "done"}
            else:
                answer = (
                    "ขออภัย ระบบเรียกใช้เครื่องมือหลายรอบเกินไป "
                    "กรุณาตั้งคำถามให้เฉพาะเจาะจงมากขึ้น"
                )
                yield {"type": "round_end", "kind": "answer"}
                yield {"type": "delta", "content": answer}

            if chat:
                chat._post_message("assistant", answer)
                chat.write({"state": "done", "model_used": config["model"]})
            yield {
                "type": "done",
                "chat_id": chat.id if chat else None,
                "model": config["model"],
            }
        except AiClientError as exc:
            if chat:
                chat._post_message("system", "เกิดข้อผิดพลาด: %s" % exc)
                chat.write({"state": "error"})
            yield {"type": "error", "message": str(exc)}
        except Exception as exc:  # noqa: BLE001 - keep the stream alive
            _logger.exception("OD19 AI stream failed")
            if chat:
                try:
                    chat._post_message("system", "เกิดข้อผิดพลาด: %s" % exc)
                    chat.write({"state": "error"})
                except Exception:  # noqa: BLE001
                    pass
            yield {"type": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Draft confirmation (2-step, human-in-the-loop)
    # ------------------------------------------------------------------
    @api.model
    def confirm_draft(self, model, values):
        return self.env["od19.ai.capability"].create_draft(
            (model or "").strip(), values or {}
        )
```

- [ ] **Step 4: เพิ่ม import ใน `models/__init__.py`**

วาง `from . import od19_ai_assistant` **หลัง** `from . import od19_ai_capability` (เพราะสมองกลางใช้ `DRAFT_MARKER` จาก capability):

```python
from . import od19_ai_tool
from . import od19_ai_tool_generic
from . import od19_ai_tool_index
from . import od19_ai_message
from . import od19_ai_chat
from . import od19_ai_tool_log
from . import od19_ai_capability
from . import od19_ai_assistant
from . import od19_ai_provider
from . import res_config_settings
from . import res_users
```

- [ ] **Step 5: เพิ่ม import เทสต์ใน `tests/__init__.py`**

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import test_ai_assistant
from . import test_ai_assistant_service
from . import test_ai_context
```

> `test_ai_context.py` ยังไม่มีใน Task นี้ — สร้างไฟล์ว่างชั่วคราว (มีแค่ header comment) เพื่อให้ import ผ่าน แล้วเติมใน Task 3

- [ ] **Step 6: ตรวจไวยากรณ์ + รันเทสต์**

รัน: `venv19\Scripts\python.exe -m py_compile custom_addons\od19_ai_assistant\models\od19_ai_assistant.py`
จากนั้น: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: PASS — `test_ai_assistant_service` ผ่านครบ; เทสต์เดิมใน `test_ai_assistant.py` **ยังล้มเหลว** (คาดไว้ จะแก้ใน Task 2)

- [ ] **Step 7: Commit**

```
git add -- custom_addons/od19_ai_assistant/models/od19_ai_assistant.py custom_addons/od19_ai_assistant/models/__init__.py custom_addons/od19_ai_assistant/tests/test_ai_assistant_service.py custom_addons/od19_ai_assistant/tests/test_ai_context.py custom_addons/od19_ai_assistant/tests/__init__.py
git commit -m "feat(od19_ai_assistant): add shared AI brain model"
```

---

## Task 2: เปลี่ยน `od19.ai.chat` + controller ให้เรียกสมองกลาง (regression)

**Files:**
- Modify: `custom_addons/od19_ai_assistant/models/od19_ai_chat.py`
- Modify: `custom_addons/od19_ai_assistant/models/res_config_settings.py`
- Modify: `custom_addons/od19_ai_assistant/controllers/main.py`
- Modify: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py`

- [ ] **Step 1: อัปเดต patch target ในเทสต์เดิม (ทำให้เทสต์ใหม่ยังอ้างตำแหน่งจริง)**

แก้ค่าคงที่ 3 ตัวท้ายหัวไฟล์ `tests/test_ai_assistant.py` (บรรทัด 15–21) — **ห้ามแก้ชื่อ/เนื้อหาเทสต์**:

```python
CHAT_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion"
)
STREAM_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion_stream"
)
AI_CLIENT_ERROR = "odoo.addons.od19_ai_assistant.lib.client.AiClientError"
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: FAIL — `test_ai_assistant` ล้มที่ `AssertionError`/patch ไม่ทำงาน (เพราะ `action_ask` ยังเรียก `chat_completion` ใน `od19_ai_chat` ที่ถูกแทนค่าไว้)

- [ ] **Step 3: ทำให้ `od19_ai_chat.py` บางลง (เก็บ persistence + delegate)**

ลบ import ที่ไม่ใช้ (`json`, `re`, `chat_completion`, `AiClientError`) และลบ const ที่ย้ายไปแล้ว (`PARAM_PREFIX`, `MAX_TOOL_ROUNDS`, `TOOL_PROTOCOL`, `DEFAULTS`, `PROVIDER_PRESETS`) แล้วแทนส่วน config/helper/action ด้วย:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Conversation persistence for the OD19 AI assistant.

The actual thinking (config, prompt, tool loop) lives in the shared brain
``od19.ai.assistant``. This model only stores the messages and forwards the
legacy entry points, so behaviour of the existing UI is unchanged.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Od19AiChat(models.Model):
    _name = "od19.ai.chat"
    _description = "บทสนทนาผู้ช่วย AI (OD19)"
    _order = "create_date desc"

    name = fields.Char(compute="_compute_name", store=True)
    state = fields.Selection(
        [("draft", "ฉบับร่าง"), ("done", "สำเร็จ"), ("error", "ผิดพลาด")],
        default="draft",
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="ผู้ถาม",
        default=lambda self: self.env.user,
        readonly=True,
    )
    model_used = fields.Char(string="โมเดลที่ใช้", readonly=True)
    message_ids = fields.One2many("od19.ai.message", "chat_id", string="ข้อความ")
    message_count = fields.Integer(
        string="จำนวนข้อความ", compute="_compute_message_count"
    )
    prompt = fields.Text(string="คำถามถัดไป")

    @api.depends("message_ids.role", "message_ids.content")
    def _compute_name(self):
        for rec in self:
            first = rec.message_ids.filtered(lambda m: m.role == "user")[:1]
            lines = (first.content or "").strip().splitlines() if first else []
            rec.name = (lines[0][:60] if lines else "") or "บทสนทนาใหม่"

    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    # ------------------------------------------------------------------
    # Backward-compatible delegates to the shared brain
    # ------------------------------------------------------------------
    @api.model
    def _brain(self):
        return self.env["od19.ai.assistant"]

    @api.model
    def _get_param(self, key, default=None):
        return self._brain()._get_param(key, default)

    @api.model
    def _get_ai_config(self):
        return self._brain()._get_ai_config()

    @api.model
    def _build_system_prompt(self, base_prompt):
        return self._brain()._build_system_prompt(base_prompt)

    @api.model
    def _parse_tool_call(self, text):
        return self._brain()._parse_tool_call(text)

    def _build_messages(self, system_prompt):
        self.ensure_one()
        return self._brain()._build_messages(self, system_prompt)

    def _post_message(self, role, content):
        """Append a message to the conversation."""
        self.ensure_one()
        return self.env["od19.ai.message"].create(
            {"chat_id": self.id, "role": role, "content": content}
        )

    # ------------------------------------------------------------------
    # Legacy action (thin: delegates to the shared brain)
    # ------------------------------------------------------------------
    def action_ask(self):
        """Append :attr:`prompt` to the conversation and store the answer."""
        self.ensure_one()
        question = (self.prompt or "").strip()
        if not question:
            raise UserError("กรุณากรอกคำถามก่อน")
        self.write({"prompt": False})
        result = self._brain().ask(question, chat=self)
        if result.get("error"):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ผู้ช่วย AI",
                    "message": result["error"],
                    "type": "danger",
                    "sticky": False,
                },
            }
        return True
```

- [ ] **Step 4: อัปเดต import ใน `res_config_settings.py`**

แก้บรรทัดที่ 6:

```python
from .od19_ai_assistant import PROVIDER_PRESETS
```

- [ ] **Step 5: ทำให้ `controllers/main.py` เหลือ transport**

แทน import และ `_stream_answer` ด้วย:

```python
import json
import logging

import odoo
from odoo import fields, http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def _sse(payload):
    """Format ``payload`` as a single server-sent event."""
    return "data: %s\n\n" % json.dumps(payload, ensure_ascii=False)


def _page_context(env, payload):
    """Resolve the (optional) page context carried by a request payload."""
    model = payload.get("model")
    res_id = payload.get("res_id")
    if not model or not res_id:
        return None
    return env["od19.ai.assistant"].build_context(
        model, int(res_id), payload.get("view_type") or "form"
    )


def _stream_answer(registry, uid, context, chat_id, question, payload=None):
    """Generator yielding SSE events for one assistant answer."""
    payload = payload or {}
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, uid, context)
        chat = None
        try:
            chat = env["od19.ai.chat"].browse(chat_id)
            if not chat.exists() or chat.user_id.id != uid:
                yield _sse({"type": "error", "message": "ไม่พบบทสนทนานี้"})
                return
            page_ctx = _page_context(env, payload)
            for event in env["od19.ai.assistant"].stream(
                question, ctx=page_ctx, chat=chat
            ):
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - keep the stream alive
            _logger.exception("OD19 AI stream failed")
            yield _sse({"type": "error", "message": str(exc)})
```

- [ ] **Step 6: อัปเดต route `chat_stream` ให้ส่ง payload ต่อ + เพิ่ม route ใหม่**

แก้ `chat_stream` ให้ส่ง `payload` เข้า `_stream_answer` และคง header เดิม:

```python
    @http.route(
        "/od19_ai/chat/stream",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def chat_stream(self, **kwargs):
        raw = request.httprequest.get_data(as_text=True)
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {}

        registry = request.registry
        uid = request.env.uid
        context = dict(request.env.context)

        generator = _stream_answer(
            registry,
            uid,
            context,
            int(payload.get("chat_id") or 0),
            (payload.get("message") or "").strip(),
            payload,
        )
        headers = [
            ("Content-Type", "text/event-stream; charset=utf-8"),
            ("Cache-Control", "no-cache"),
            ("X-Accel-Buffering", "no"),
        ]
        return request.make_response(generator, headers=headers)
```

เพิ่ม route ใหม่ 2 ตัวในคลาส `Od19AiChatController` (ก่อน `chat_stream`):

```python
    @http.route("/od19_ai/ask", type="jsonrpc", auth="user")
    def ask(self, question=None, model=None, res_id=None,
            view_type=None, chat_id=None, **kwargs):
        assistant = request.env["od19.ai.assistant"]
        ctx = None
        if model and res_id:
            ctx = assistant.build_context(model, int(res_id), view_type or "form")
        chat = None
        if chat_id:
            candidate = request.env["od19.ai.chat"].browse(int(chat_id))
            if candidate.exists() and candidate.user_id.id == request.env.uid:
                chat = candidate
        return assistant.ask(question or "", ctx=ctx, chat=chat)

    @http.route("/od19_ai/suggest", type="jsonrpc", auth="user")
    def suggest(self, model=None, res_id=None, view_type=None, **kwargs):
        assistant = request.env["od19.ai.assistant"]
        ctx = None
        if model and res_id:
            ctx = assistant.build_context(model, int(res_id), view_type or "form")
        elif model:
            ctx = {"model": model, "view_type": view_type or "list"}
        return {"chips": assistant.suggest_actions(ctx)}
```

- [ ] **Step 7: รันเทสต์ทั้งโมดูล**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: **PASS ทั้งหมด** — `test_ai_assistant.py` (regression) + `test_ai_assistant_service.py`; ยืนยัน `test_stream_endpoint_emits_sse` ผ่าน (patch `STREAM_COMPLETION` ที่ใหม่)
หากล้ม ให้ตรวจว่า (ก) `_stream_answer` ยังเปิด `registry.cursor()` เอง (ข) `od19.ai.chat._parse_tool_call` delegate ถูกเรียกจริง

- [ ] **Step 8: Commit**

```
git add -- custom_addons/od19_ai_assistant/models/od19_ai_chat.py custom_addons/od19_ai_assistant/models/res_config_settings.py custom_addons/od19_ai_assistant/controllers/main.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "refactor(od19_ai_assistant): route chat and controllers through shared brain"
```

---

## Task 3: บริบทหน้าจอฝั่ง server (`build_context`) + endpoint

**Files:**
- Create/Replace: `custom_addons/od19_ai_assistant/tests/test_ai_context.py`
- Modify: `custom_addons/od19_ai_assistant/tests/test_ai_assistant.py` (เพิ่ม HttpCase)

> `build_context` / `context_brief` / `suggest_actions` ถูก implement แล้วใน Task 1 — Task นี้คือ **ทดสอบ** ให้ครบตามสเปก §13 และทดสอบ endpoint `/od19_ai/ask` / `/od19_ai/suggest`

- [ ] **Step 1: เขียนเทสต์บริบทที่จะล้มเหลว (กรณีที่ยังไม่ครอบคลุม)**

เขียนทับ `tests/test_ai_context.py`:

```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestOd19AiContext(TransactionCase):
    def _brain(self):
        return self.env["od19.ai.assistant"]

    def test_build_context_readable_record(self):
        partner = self.env["res.partner"].create({"name": "บริษัท บริบท จำกัด"})
        ctx = self._brain().build_context("res.partner", partner.id, "form")
        self.assertEqual(ctx["model"], "res.partner")
        self.assertEqual(ctx["res_id"], partner.id)
        self.assertEqual(ctx["display_name"], "บริษัท บริบท จำกัด")
        self.assertEqual(ctx["view_type"], "form")
        self.assertLessEqual(len(ctx["fields"]), 30)

    def test_build_context_list_without_res_id(self):
        ctx = self._brain().build_context("res.partner", False, "list")
        self.assertEqual(ctx["model"], "res.partner")
        self.assertFalse(ctx["res_id"])
        self.assertEqual(ctx["view_type"], "list")

    def test_build_context_unknown_model_is_none(self):
        self.assertIsNone(self._brain().build_context("no.such.model", 1, "form"))

    def test_build_context_missing_record_is_none(self):
        self.assertIsNone(
            self._brain().build_context("res.partner", 99999999, "form")
        )

    def test_build_context_denied_by_record_rule_is_none(self):
        partner = self.env["res.partner"].create({"name": "ลับสุดยอด"})
        user = new_test_user(
            self.env, login="od19_ctx_denied", groups="base.group_user"
        )
        self.env["ir.rule"].create(
            {
                "name": "OD19 ctx deny rule",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": "[('id', '=', 0)]",
                "groups": [(6, 0, [user.groups_id.id])],
            }
        )
        self.assertIsNone(
            self.env["od19.ai.assistant"]
            .with_user(user)
            .build_context("res.partner", partner.id, "form")
        )

    def test_context_brief_is_truncated(self):
        ctx = {
            "model": "res.partner",
            "res_id": 1,
            "view_type": "form",
            "display_name": "ก" * 2000,
            "fields": ["name"],
            "snippet": "ข" * 2000,
        }
        brief = self._brain().context_brief(ctx)
        self.assertLessEqual(len(brief), 800)
        self.assertIn("res.partner", brief)

    def test_context_brief_empty(self):
        self.assertEqual(self._brain().context_brief(None), "")

    def test_suggest_actions_capped_at_four(self):
        for model in ("sale.order", "account.move", "res.partner"):
            self.assertLessEqual(len(self._brain().suggest_actions({"model": model})), 4)
```

- [ ] **Step 2: รันเทสต์ให้เห็นผล**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: ถ้า implement ครบแล้ว **PASS** ทันที — ถ้าล้มที่ `test_build_context_denied_by_record_rule_is_none` ให้ตรวจว่า `build_context` ใช้ `record.has_access("read")` (ไม่ใช้ `check_access_rule`)

- [ ] **Step 3: เพิ่ม HttpCase ทดสอบ endpoint (ท้ายไฟล์ `tests/test_ai_assistant.py`)**

```python
@tagged("post_install", "-at_install")
class TestOd19AiAskHttp(HttpCase):
    def test_ask_endpoint_returns_answer(self):
        partner = self.env["res.partner"].create({"name": "บริษัท ถาม จำกัด"})
        with patch(CHAT_COMPLETION, return_value="นี่คือบริษัท ถาม จำกัด"):
            result = self.url_open(
                "/od19_ai/ask",
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "question": "เอกสารนี้คืออะไร",
                        "model": "res.partner",
                        "res_id": partner.id,
                        "view_type": "form",
                    },
                },
            ).json()["result"]
        self.assertEqual(result["answer"], "นี่คือบริษัท ถาม จำกัด")
        self.assertIsNone(result["error"])

    def test_suggest_endpoint_returns_chips(self):
        partner = self.env["res.partner"].create({"name": "บริษัท ชิป จำกัด"})
        result = self.url_open(
            "/od19_ai/suggest",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "res.partner",
                    "res_id": partner.id,
                    "view_type": "form",
                },
            },
        ).json()["result"]
        self.assertTrue(result["chips"])
```

- [ ] **Step 4: รันเทสต์ทั้งโมดูล**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: **PASS ทั้งหมด** (0 failed / 0 error)

- [ ] **Step 5: Commit**

```
git add -- custom_addons/od19_ai_assistant/tests/test_ai_context.py custom_addons/od19_ai_assistant/tests/test_ai_assistant.py
git commit -m "test(od19_ai_assistant): cover page context and ask/suggest endpoints"
```

---

## Task 4: แผง UI ที่ใช้ร่วม (`ai_panel.js` + `ai_panel.xml` + scss)

**Files:**
- Create: `custom_addons/od19_ai_assistant/static/src/js/ai_context.js`
- Create: `custom_addons/od19_ai_assistant/static/src/js/ai_panel.js`
- Create: `custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml`
- Create: `custom_addons/od19_ai_assistant/static/src/scss/od19_ai_panel.scss`
- Modify: `custom_addons/od19_ai_assistant/__manifest__.py` (เพิ่ม assets)

- [ ] **Step 1: สร้าง `static/src/js/ai_context.js`**

```javascript
/** @odoo-module **/

/**
 * Read the page context of the currently open view.
 *
 * This is the ONLY place bound to the web-client internals: if Odoo changes
 * `env.services.action.currentController` in the future, fixing this file is
 * enough. Always returns a plain object or null — never throws.
 */
export function getPageContext(env) {
    try {
        const controller = env.services.action.currentController;
        const props = controller && controller.props;
        if (!props || !props.resModel) {
            return null;
        }
        const viewType = props.type;
        if (viewType !== "form" && viewType !== "list") {
            return null;
        }
        let resId = props.resId;
        if (!resId && controller.model && controller.model.root) {
            resId = controller.model.root.resId;
        }
        return {
            model: props.resModel,
            res_id: resId || false,
            view_type: viewType,
        };
    } catch {
        return null;
    }
}
```

- [ ] **Step 2: สร้าง `static/src/js/ai_panel.js`**

```javascript
/** @odoo-module **/

import { Component, onPatched, reactive, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { getPageContext } from "./ai_context";

/** Shared open/close state (systray button and the panel both read it). */
export const aiPanelState = reactive({ open: false });

export function toggleAiPanel() {
    aiPanelState.open = !aiPanelState.open;
}

/**
 * The single chat panel reused by every surface.
 *
 * It reads the current page context on open/send so the assistant already
 * knows which document the user is looking at, and streams the answer from
 * ``/od19_ai/chat/stream`` (the same route the full-page chat uses).
 */
export class AiPanel extends Component {
    static template = "od19_ai_assistant.AiPanel";
    static props = {};

    setup() {
        this.notification = useService("notification");
        this.messagesRef = useRef("messages");
        this.state = useState({
            chats: [],
            activeChatId: false,
            messages: [],
            draft: "",
            streaming: false,
            streamText: "",
            toolChips: [],
            error: "",
            pendingDraft: null,
            chips: [],
        });
        onPatched(() => {
            if (this.state.streaming) {
                this.scrollToBottom();
            }
        });
        this.loadChips();
    }

    get isOpen() {
        return aiPanelState.open;
    }

    async loadChips() {
        const ctx = getPageContext(this.env);
        try {
            const data = await rpc("/od19_ai/suggest", ctx || {});
            this.state.chips = data.chips || [];
        } catch {
            this.state.chips = [];
        }
    }

    close() {
        aiPanelState.open = false;
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.send();
        }
    }

    useChip(chip) {
        this.state.draft = chip;
        this.send();
    }

    async ensureChat() {
        if (this.state.activeChatId) {
            return this.state.activeChatId;
        }
        const [id] = await rpc("/od19_ai/chat/create", {});
        this.state.activeChatId = id;
        return id;
    }

    async send() {
        const text = this.state.draft.trim();
        if (!text || this.state.streaming) {
            return;
        }
        const chatId = await this.ensureChat();
        const ctx = getPageContext(this.env);
        this.state.draft = "";
        this.state.error = "";
        this.state.streamText = "";
        this.state.toolChips = [];
        this.state.messages.push({ id: -Date.now(), role: "user", content: text });
        this.state.streaming = true;
        this.scrollToBottom();
        try {
            await this.streamChat(chatId, text, ctx);
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.streaming = false;
            this.state.streamText = "";
            this.state.toolChips = [];
            await this.loadMessages(chatId);
        }
    }

    async loadMessages(chatId) {
        const data = await rpc("/od19_ai/chat/messages", { chat_id: chatId });
        this.state.messages = data.messages;
        this.scrollToBottom();
    }

    async streamChat(chatId, message, ctx) {
        const body = { chat_id: chatId, message };
        if (ctx) {
            body.model = ctx.model;
            body.res_id = ctx.res_id;
            body.view_type = ctx.view_type;
        }
        const response = await fetch("/od19_ai/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!response.ok || !response.body) {
            throw new Error("เชื่อมต่อผู้ช่วย AI ไม่สำเร็จ (HTTP " + response.status + ")");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            let sep;
            while ((sep = buffer.indexOf("\n\n")) >= 0) {
                this.handleEventBlock(buffer.slice(0, sep));
                buffer = buffer.slice(sep + 2);
            }
        }
        if (buffer.trim()) {
            this.handleEventBlock(buffer);
        }
    }

    handleEventBlock(block) {
        for (const line of block.split("\n")) {
            if (!line.startsWith("data:")) {
                continue;
            }
            try {
                this.onStreamEvent(JSON.parse(line.slice(5).trim()));
            } catch {
                continue;
            }
        }
    }

    onStreamEvent(event) {
        switch (event.type) {
            case "delta":
                this.state.streamText += event.content;
                break;
            case "round_end":
                if (event.kind === "tool") {
                    this.state.streamText = "";
                }
                break;
            case "tool":
                if (event.status === "done") {
                    this.state.toolChips.push(event.name);
                }
                break;
            case "draft":
                this.state.pendingDraft = event.draft;
                this.state.streamText = "";
                break;
            case "error":
                this.state.error = event.message;
                this.state.streamText = "";
                break;
        }
    }

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

    scrollToBottom() {
        const el = this.messagesRef.el;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }
}

registry.category("main_components").add("od19_ai_assistant.AiPanel", {
    Component: AiPanel,
});
```

- [ ] **Step 3: สร้าง `static/src/xml/ai_panel.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<templates xml:space="preserve">

    <t t-name="od19_ai_assistant.AiPanel">
        <div t-if="isOpen" class="o_od19_ai_panel">
            <div class="o_od19_ai_panel_head">
                <span class="o_od19_ai_panel_title">
                    <i class="fa fa-magic me-1"/> ผู้ช่วย AI
                </span>
                <button type="button" class="o_od19_ai_panel_close"
                        title="ปิด" t-on-click="close">
                    <i class="fa fa-times"/>
                </button>
            </div>

            <div class="o_od19_ai_panel_chips" t-if="state.chips.length">
                <button type="button" class="o_od19_ai_chip"
                        t-foreach="state.chips" t-as="chip" t-key="chip_index"
                        t-out="chip" t-on-click="() => this.useChip(chip)"/>
            </div>

            <div class="o_od19_ai_panel_messages" t-ref="messages">
                <t t-foreach="state.messages" t-as="msg" t-key="msg.id">
                    <div class="o_od19_ai_msg" t-att-class="'role-' + msg.role"
                         t-out="msg.content"/>
                </t>
                <t t-foreach="state.toolChips" t-as="chip" t-key="chip_index">
                    <div class="o_od19_ai_toolchip">
                        <i class="fa fa-wrench"/> <span t-out="chip"/>
                    </div>
                </t>
                <div class="o_od19_ai_msg role-assistant" t-if="state.streamText"
                     t-out="state.streamText"/>
                <div class="o_od19_ai_typing" t-if="state.streaming and !state.streamText">
                    กำลังคิด ...
                </div>
                <div class="o_od19_ai_msg role-system" t-if="state.error"
                     t-out="state.error"/>
                <div class="o_od19_ai_draft" t-if="state.pendingDraft">
                    <div class="o_od19_ai_draft_title">
                        <i class="fa fa-file-text-o me-1"/>
                        ขอสร้างเอกสารร่าง:
                        <t t-out="state.pendingDraft.model_label"/>
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
            </div>

            <div class="o_od19_ai_panel_composer">
                <textarea t-model="state.draft"
                          placeholder="ถามเกี่ยวกับเอกสารนี้ ... (Enter = ส่ง)"
                          t-on-keydown="onKeydown"
                          t-att-disabled="state.streaming"/>
                <button type="button" class="btn btn-primary"
                        t-on-click="send"
                        t-att-disabled="state.streaming or !state.draft.trim()">
                    <i class="fa fa-paper-plane"/>
                </button>
            </div>
        </div>
    </t>

</templates>
```

- [ ] **Step 4: สร้าง `static/src/scss/od19_ai_panel.scss`**

```scss
.o_od19_ai_panel {
    position: fixed;
    right: 16px;
    bottom: 16px;
    width: 380px;
    max-height: 70vh;
    display: flex;
    flex-direction: column;
    z-index: 1050;
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
    overflow: hidden;

    .o_od19_ai_panel_head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        background: #9e2424;
        color: #fff;
        font-weight: 600;
    }

    .o_od19_ai_panel_close {
        background: none;
        border: none;
        color: #fff;
    }

    .o_od19_ai_panel_chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        padding: 8px 12px;
        border-bottom: 1px solid #f0f0f0;

        .o_od19_ai_chip {
            border: 1px solid #9e2424;
            color: #9e2424;
            background: #fff;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.8rem;
        }
    }

    .o_od19_ai_panel_messages {
        flex: 1 1 auto;
        overflow-y: auto;
        padding: 12px;
        min-height: 120px;
    }

    .o_od19_ai_panel_composer {
        display: flex;
        gap: 6px;
        padding: 8px 12px;
        border-top: 1px solid #f0f0f0;

        textarea {
            flex: 1 1 auto;
            resize: none;
            min-height: 44px;
        }
    }
}
```

- [ ] **Step 5: เพิ่ม assets ใน `__manifest__.py`**

```python
{
    "name": "OD19 AI Assistant",
    "version": "19.0.3.0.0",
    ...
    "assets": {
        "web.assets_backend": [
            "od19_ai_assistant/static/src/scss/od19_ai_chat.scss",
            "od19_ai_assistant/static/src/scss/od19_ai_panel.scss",
            "od19_ai_assistant/static/src/xml/od19_ai_chat.xml",
            "od19_ai_assistant/static/src/xml/ai_panel.xml",
            "od19_ai_assistant/static/src/xml/systray_item.xml",
            "od19_ai_assistant/static/src/js/od19_ai_chat.js",
            "od19_ai_assistant/static/src/js/ai_context.js",
            "od19_ai_assistant/static/src/js/ai_panel.js",
            "od19_ai_assistant/static/src/js/systray_item.js",
        ],
    },
    ...
}
```

> `systray_item.xml` / `systray_item.js` จะสร้างใน Task 5 — ถ้ารัน asset ก่อน Task 5 จะ error 404; ให้ commit Task 4 + Task 5 ต่อเนื่องกันก่อน manual test

- [ ] **Step 6: ตรวจไวยากรณ์ XML/JS**

รัน: `venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse(r'custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml')"`
Expected: ไม่มี output

- [ ] **Step 7: Commit**

```
git add -- custom_addons/od19_ai_assistant/static/src/js/ai_context.js custom_addons/od19_ai_assistant/static/src/js/ai_panel.js custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml custom_addons/od19_ai_assistant/static/src/scss/od19_ai_panel.scss custom_addons/od19_ai_assistant/__manifest__.py
git commit -m "feat(od19_ai_assistant): add shared context-aware AI panel"
```

---

## Task 5: ปุ่ม AI บน systray (`systray_item.js` + `systray_item.xml`)

**Files:**
- Create: `custom_addons/od19_ai_assistant/static/src/js/systray_item.js`
- Create: `custom_addons/od19_ai_assistant/static/src/xml/systray_item.xml`

- [ ] **Step 1: สร้าง `static/src/xml/systray_item.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<templates xml:space="preserve">

    <t t-name="od19_ai_assistant.SystrayItem">
        <button type="button" class="o_od19_ai_systray"
                title="ผู้ช่วย AI (Alt+Shift+P)"
                t-att-class="{ active: isOpen }"
                t-on-click="toggle">
            <i class="fa fa-magic"/>
        </button>
    </t>

</templates>
```

- [ ] **Step 2: สร้าง `static/src/js/systray_item.js`**

```javascript
/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { aiPanelState, toggleAiPanel } from "./ai_panel";

/**
 * Systray button that opens/closes the shared AI panel on every page.
 *
 * Hotkey ``alt+shift+p`` — chosen because ``alt+shift+a`` is already taken by
 * the mail activities menu (addons/mail/.../activity_menu.js:28).
 */
export class Od19AiSystrayItem extends Component {
    static template = "od19_ai_assistant.SystrayItem";
    static props = {};

    setup() {
        this.aiPanelState = aiPanelState;
        useHotkey("alt+shift+p", () => toggleAiPanel());
    }

    get isOpen() {
        return this.aiPanelState.open;
    }

    toggle() {
        toggleAiPanel();
    }
}

registry
    .category("systray")
    .add("od19_ai_assistant.ai_button", { Component: Od19AiSystrayItem }, { sequence: 50 });
```

- [ ] **Step 3: อัปเดตโมดูล (อัปเกรด/รีสตาร์ท) และทดสอบมือ**

รัน: รีสตาร์ท Odoo แล้วอัปเกรดโมดูล `od19_ai_assistant` (`-u od19_ai_assistant` บน DB ทดสอบของตัวเอง)
จากนั้นเปิดเบราว์เซอร์:
- เห็นไอคอน `fa-magic` บน systray ทุกหน้า → คลิกเปิด/ปิดแผงได้
- กด `Alt+Shift+P` → แผงเปิด/ปิด (ไม่ชนเมนูกิจกรรมของ mail)
- ไม่มี error ใน console (F12)

Expected: แผงเปิดได้, ชิปแสดง, ไม่มี JS error

- [ ] **Step 4: Commit**

```
git add -- custom_addons/od19_ai_assistant/static/src/js/systray_item.js custom_addons/od19_ai_assistant/static/src/xml/systray_item.xml
git commit -m "feat(od19_ai_assistant): add systray AI launcher button"
```

---

## Task 6: Form Help Panel — docking + auto-show บนมุมมองฟอร์ม

**Files:**
- Modify: `custom_addons/od19_ai_assistant/static/src/js/ai_panel.js`
- Modify: `custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml`
- Modify: `custom_addons/od19_ai_assistant/static/src/scss/od19_ai_panel.scss`

> ใช้ `main_components` (ลงทะเบียนใน Task 4 แล้ว) → ครอบทุกฟอร์มของทุกโมดูลโดย **ไม่แก้ XML view ของโมดูลอื่น** (R9) Task นี้เพิ่มพฤติกรรม "เกาะข้างฟอร์ม" เมื่ออยู่ในมุมมองฟอร์มที่มีเอกสารจริง และเปลี่ยนชิปตามบริบทเมื่อสลับหน้า

- [ ] **Step 1: เพิ่มการอ่านบริบทซ้ำเมื่อ route/action เปลี่ยน**

ใน `AiPanel.setup()` เพิ่มการเฝ้าดู `env.services.action` เพื่อโหลดชิปใหม่เมื่อผู้ใช้สลับหน้า:

```javascript
import { useBus } from "@web/core/utils/hooks";
...
    setup() {
        ...
        useBus(this.env.services.action, "ACTION_MANAGER:UPDATE", () => {
            this.loadChips();
        });
    }
```

- [ ] **Step 2: เพิ่ม getter ตัดสินใจโหมดวาง (dock vs float)**

ในคลาส `AiPanel` เพิ่ม:

```javascript
    get pageContext() {
        return getPageContext(this.env);
    }

    get isDocked() {
        const ctx = this.pageContext;
        return Boolean(ctx && ctx.view_type === "form" && ctx.res_id);
    }

    get panelClass() {
        return this.isDocked ? "o_od19_ai_panel o_od19_ai_docked" : "o_od19_ai_panel";
    }
```

- [ ] **Step 3: ผูกคลาสกับเทมเพลต**

ใน `static/src/xml/ai_panel.xml` แก้ root `div`:

```xml
        <div t-if="isOpen" t-att-class="panelClass">
```

- [ ] **Step 4: เพิ่มสไตล์ docking**

เพิ่มท้าย `static/src/scss/od19_ai_panel.scss`:

```scss
.o_od19_ai_panel.o_od19_ai_docked {
    top: 60px;
    bottom: 16px;
    max-height: none;
    width: 360px;
}
```

- [ ] **Step 5: ทดสอบมือ**

- เปิดฟอร์มลูกค้า (`res.partner`) → เปิดแผง → แผงเกาะด้านขวา และชิปเป็นชุดของ `res.partner`
- ไปหน้ารายการ (list) → แผงกลับมาเป็นแบบลอยมุมขวาล่าง และชิปเปลี่ยนตามโมเดลของลิสต์
- ไปหน้า Settings (ไม่ใช่มุมมองข้อมูล) → แผงยังเปิดได้ แต่ไม่มีชิปเฉพาะโมเดล

Expected: พฤติกรรมถูกต้อง ไม่มี JS error

- [ ] **Step 6: Commit**

```
git add -- custom_addons/od19_ai_assistant/static/src/js/ai_panel.js custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml custom_addons/od19_ai_assistant/static/src/scss/od19_ai_panel.scss
git commit -m "feat(od19_ai_assistant): dock AI panel beside form views"
```

---

## Task 7: ชิปคำสั่งด่วนตามบริบท (`suggest_actions` + UI wiring)

**Files:**
- Modify: `custom_addons/od19_ai_assistant/static/src/js/ai_panel.js`
- Modify: `custom_addons/od19_ai_assistant/static/src/xml/ai_panel.xml`
- Modify: `custom_addons/od19_ai_assistant/tests/test_ai_assistant_service.py`

> `suggest_actions()` + route `/od19_ai/suggest` implement แล้วใน Task 1/2 และมีเทสต์ใน Task 1 แล้ว — Task นี้คือทำให้ **ครบ + ตรวจว่าใช้ได้จริง** ตามสเปก §8.4

- [ ] **Step 1: เพิ่มเทสต์กรณีชิปตามบริบทของโมเดลที่ใช้บ่อย**

เพิ่มใน `TestOd19AiAssistantService` (ท้ายคลาส):

```python
    def test_suggest_actions_all_known_models_non_empty(self):
        for model in ("sale.order", "purchase.order", "account.move",
                      "res.partner", "product.template", "project.task"):
            chips = self._brain().suggest_actions({"model": model})
            self.assertTrue(chips, "no chips for %s" % model)
            self.assertLessEqual(len(chips), 4)
```

- [ ] **Step 2: ยืนยันว่า UI ใช้ chip แล้วส่งคำถามทันที**

ตรวจใน `ai_panel.js` ว่า `useChip(chip)` ตั้ง `state.draft = chip` แล้วเรียก `send()` และใน `ai_panel.xml` ปุ่มชิปใช้ `t-on-click="() => this.useChip(chip)"` (มีแล้วใน Task 4 — ยืนยันว่าไม่ถูกถอด)

- [ ] **Step 3: รันเทสต์ทั้งโมดูล**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: **PASS ทั้งหมด** (0 failed / 0 error)

- [ ] **Step 4: ทดสอบมือ: กดชิปต้องส่งคำถามทันที**

- เปิดฟอร์มใบสั่งขาย → เปิดแผง → เห็นชิป (เช่น "สรุปออร์เดอร์นี้") → กดชิป → คำถามถูกส่งทันทีและได้คำตอบอ้างถึงเอกสารที่เปิดอยู่

Expected: คำตอบอ้างถึงเอกสารจริง (สอดคล้อง §11)

- [ ] **Step 5: Commit**

```
git add -- custom_addons/od19_ai_assistant/tests/test_ai_assistant_service.py custom_addons/od19_ai_assistant/static/src/js/ai_panel.js
git commit -m "feat(od19_ai_assistant): wire context-aware quick command chips"
```

---

## Task 8: ตรวจสอบรอบสุดท้าย (ทั้งชุด + ไม่แตะโมดูลอื่น)

**Files:** (ไม่สร้างไฟล์ใหม่ — ตรวจสอบเท่านั้น)

- [ ] **Step 1: รันเทสต์ทั้งโมดูลหนึ่งครั้งสุดท้าย**

รัน: `.\run-tests.ps1 -Module od19_ai_assistant -Database odoo19_t_trae-od19_ai_embed`
Expected: **0 failed / 0 error(s)**

- [ ] **Step 2: ยืนยันว่าไม่แตะ view ของโมดูลอื่นและไม่แตะ core**

รัน: `git diff --stat 412ef81e030 -- custom_addons addons odoo`
Expected: มีเฉพาะไฟล์ภายใต้ `custom_addons/od19_ai_assistant/` และ `docs/superpowers/` — **ไม่มี** `addons/**` หรือ `odoo/**`

- [ ] **Step 3: ยืนยันว่าไฟล์ที่แตะตรงตาม File Structure**

รัน: `git diff --name-only 412ef81e030`
Expected: เฉพาะไฟล์ที่ระบุในตาราง File Structure (บวกไฟล์ docs ของสเปก/แผน)

- [ ] **Step 4: ทดสอบมือรอบเต็ม (ตามสเปก §13)**

- เปิดฟอร์มลูกค้า → กดปุ่ม AI บน systray → ถาม "ลูกค้ารายนี้เป็นใคร" → คำตอบต้องอ้างถึงเอกสารที่เปิดอยู่จริง
- แชทหน้าเต็มเดิม (เมนู "แชทผู้ช่วย AI") ยังใช้งานได้ปกติ: สร้างบทสนทนาใหม่, ส่งคำถาม, สตรีมคำตอบ, ลบบทสนทนา
- ตรวจ `Settings > Technical > AI Assistant` ยังแสดงค่า provider/model/timeout เดิม
- ตรวจ audit log `od19.ai.tool.log` ยังถูกเขียนเมื่อมีการเรียกเครื่องมือ

Expected: ผ่านทุกข้อ

- [ ] **Step 5: ตรวจ Conventional Commits + ส่งงาน**

รัน: `git log --oneline 412ef81e030..HEAD`
Expected: ข้อความ commit ขึ้นต้นด้วย `feat(od19_ai_assistant):` / `refactor(od19_ai_assistant):` / `test(od19_ai_assistant):` ทุกตัว ยาว ≤ 72 ตัวอักษร

รายงานผลตาม AGENTS.md §10: AGENT_ID, commit SHA, ไฟล์ที่แตะ, lease ที่จับ/ปล่อย, คำสั่งที่รันจริง, ผลลัพธ์จริง

```
git add -- docs/superpowers/plans/2026-11-11-od19-ai-assistant-embedded-surfaces.md
git commit -m "docs(od19_ai_assistant): add embedded surfaces implementation plan"
```

---

## Self-Review Checklist (ตรวจก่อนเริ่มลงมือ)

- [ ] **Spec coverage** — §6 API ครบ (`build_context`/`context_brief`/`ask`/`stream`/`confirm_draft`/`suggest_actions`) · §7.3 ลำดับตรวจสิทธิ์ครบ · §8.1 systray sequence 50 · §8.2 main_components · §8.3 แผงใช้ร่วม · §8.4 ชิป · §12 ไฟล์ตรง · §14 defaults ตรง
- [ ] **Placeholder scan** — ไม่มี "TODO"/"TBD"/"implement later" ในทุก Task
- [ ] **Type consistency** — `ask()` คืน `dict` ทุกที่ · `stream()` yield `dict` · `build_context()` คืน `dict|None` · `_build_messages(chat, system_prompt, question=None)` signature เดียวกันทุกจุดเรียก
- [ ] **Regression guard** — patch target ใหม่ตรงกับที่ import จริง · `_stream_answer` ยังเป็นเจ้าของ cursor · `DEFAULTS["timeout"] == 60` ไม่ถูกแก้
- [ ] **Hotkey** — ยืนยัน `alt+shift+p` ไม่ชน (alt+shift ถูกใช้: a,i,u,t,v,x)
- [ ] **No core / no other views** — ไม่มีการแก้ `addons/**`, `odoo/**`, XML view ของโมดูลอื่น
