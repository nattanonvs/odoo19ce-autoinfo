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
