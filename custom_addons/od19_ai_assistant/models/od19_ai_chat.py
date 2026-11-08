# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

import logging

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

from ..lib.client import AiClientError, chat_completion

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "od19_ai"

# Used when neither ir.config_parameter nor odoo.conf provides a value.
DEFAULTS = {
    "base_url": "http://localhost:11434/v1",
    "model": "qwen2.5:7b",
    "system_prompt": (
        "You are a helpful assistant for a Thai accounting ERP (Odoo 19). "
        "Answer in Thai unless asked otherwise."
    ),
    "timeout": 60,
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

        Allows the endpoint/credentials to be supplied either from the
        Settings UI or from ``odoo.conf`` (keys ``od19_ai_base_url``,
        ``od19_ai_model``, ``od19_ai_api_key``, ``od19_ai_timeout``,
        ``od19_ai_system_prompt``) so no secret has to be hard-coded.
        """

        def resolve(key):
            param = self._get_param(key)
            if param not in (None, ""):
                return param
            return tools.config.get("%s_%s" % (PARAM_PREFIX, key))

        timeout_raw = resolve("timeout")
        try:
            timeout = int(timeout_raw) if timeout_raw else DEFAULTS["timeout"]
        except (TypeError, ValueError):
            timeout = DEFAULTS["timeout"]

        return {
            "base_url": resolve("base_url") or DEFAULTS["base_url"],
            "model": resolve("model") or DEFAULTS["model"],
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
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
        return messages

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
        """Append :attr:`prompt` to the conversation and store the answer."""
        self.ensure_one()
        question = (self.prompt or "").strip()
        if not question:
            raise UserError("กรุณากรอกคำถามก่อน")

        config = self._get_ai_config()
        self._post_message("user", question)
        self.write({"prompt": False})

        try:
            answer = chat_completion(
                config["base_url"],
                config["model"],
                self._build_messages(config["system_prompt"]),
                api_key=config["api_key"],
                timeout=config["timeout"],
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
