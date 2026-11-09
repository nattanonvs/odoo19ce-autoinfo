# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

import json
import logging
import re

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

from ..lib.client import AiClientError, chat_completion

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "od19_ai"

# Maximum number of tool-call round-trips before we force a plain answer.
MAX_TOOL_ROUNDS = 5

# Appended to the system prompt when tools are available. The assistant is
# asked to answer with a single JSON object to request data, which keeps the
# protocol model-agnostic (works with Ollama/Qwen and any OpenAI-compatible
# endpoint without relying on native function-calling support).
TOOL_PROTOCOL = (
    "\n\nคุณสามารถเรียกใช้เครื่องมือเพื่ออ่านข้อมูลจริงจากระบบ Odoo ได้ "
    "เมื่อต้องการข้อมูล ให้ตอบกลับเป็น JSON เท่านั้นในรูปแบบ:\n"
    '{{"tool": "<ชื่อเครื่องมือ>", "arguments": {{<พารามิเตอร์>}}}}\n'
    "เครื่องมือที่มี:\n%s\n"
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

# Per-provider endpoint/model presets. Ollama (local, free) stays the
# default; Groq (free cloud tier) is the ready-made alternative. Selecting a
# provider in Settings fills the endpoint fields, and these presets also act
# as the fallback when only the provider is configured.
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
    message_ids = fields.One2many(
        "od19.ai.message", "chat_id", string="ข้อความ"
    )
    message_count = fields.Integer(
        string="จำนวนข้อความ", compute="_compute_message_count"
    )
    # Transient input box: the next question to send.
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
        """Resolve AI settings: ir.config_parameter -> odoo.conf -> default.

        Allows the provider/endpoint/credentials to be supplied either from
        the Settings UI or from ``odoo.conf`` (keys ``od19_ai_provider``,
        ``od19_ai_base_url``, ``od19_ai_model``, ``od19_ai_api_key``,
        ``od19_ai_timeout``, ``od19_ai_system_prompt``) so no secret has to
        be hard-coded. When the provider is set but the endpoint is not, the
        provider preset is used (Ollama by default, Groq as the alternative).
        """

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
    # Helpers
    # ------------------------------------------------------------------
    def _build_messages(self, system_prompt):
        """Return the OpenAI-style message list including full history."""
        self.ensure_one()
        messages = [{"role": "system", "content": system_prompt}]
        for msg in self.message_ids.sorted("id"):
            if msg.role == "tool":
                # Prompt-based protocol: feed tool output back as an
                # observation the model can read.
                messages.append(
                    {
                        "role": "user",
                        "content": "[ผลลัพธ์จากเครื่องมือ]\n%s" % msg.content,
                    }
                )
            elif msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
        return messages

    @api.model
    def _build_system_prompt(self, base_prompt):
        """Append the tool catalog to the base system prompt."""
        catalog = self.env["od19.ai.tool"].prompt_catalog()
        if not catalog:
            return base_prompt
        return base_prompt + TOOL_PROTOCOL % catalog

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

    def _post_message(self, role, content):
        """Append a message to the conversation."""
        self.ensure_one()
        return self.env["od19.ai.message"].create(
            {"chat_id": self.id, "role": role, "content": content}
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_ask(self):
        """Append :attr:`prompt` to the conversation and store the answer.

        The assistant may call read-only Odoo tools before answering: each
        round re-sends the whole history (including tool observations)
        until the model replies with plain text or :data:`MAX_TOOL_ROUNDS`
        is reached.
        """
        self.ensure_one()
        question = (self.prompt or "").strip()
        if not question:
            raise UserError("กรุณากรอกคำถามก่อน")

        config = self._get_ai_config()
        system_prompt = self._build_system_prompt(config["system_prompt"])
        tool_model = self.env["od19.ai.tool"]
        self._post_message("user", question)
        self.write({"prompt": False})

        answer = None
        try:
            for _round in range(MAX_TOOL_ROUNDS):
                raw = chat_completion(
                    config["base_url"],
                    config["model"],
                    self._build_messages(system_prompt),
                    api_key=config["api_key"],
                    timeout=config["timeout"],
                )
                call = self._parse_tool_call(raw)
                if not call:
                    answer = raw
                    break
                name, arguments = call
                self._post_message("assistant", raw)
                self._post_message("tool", tool_model.execute(name, arguments))
            else:
                answer = (
                    "ขออภัย ระบบเรียกใช้เครื่องมือหลายรอบเกินไป "
                    "กรุณาตั้งคำถามให้เฉพาะเจาะจงมากขึ้น"
                )
        except AiClientError as exc:
            # Persist the failure (a raise would roll the write back) and
            # surface it to the user with a notification instead.
            self.write({"state": "error"})
            self._post_message("system", "เกิดข้อผิดพลาด: %s" % exc)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ผู้ช่วย AI",
                    "message": str(exc),
                    "type": "danger",
                    "sticky": False,
                },
            }

        self._post_message("assistant", answer)
        self.write({"state": "done", "model_used": config["model"]})
        return True
