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
