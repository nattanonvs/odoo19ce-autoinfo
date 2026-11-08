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
    _description = "ข้อความผู้ช่วย AI (OD19)"
    _order = "create_date desc"

    name = fields.Char(compute="_compute_name", store=True)
    prompt = fields.Text(string="คำถาม", required=True)
    response = fields.Text(string="คำตอบ", readonly=True)
    error_message = fields.Text(string="ข้อความผิดพลาด", readonly=True)
    model_used = fields.Char(string="โมเดลที่ใช้", readonly=True)
    state = fields.Selection(
        [("draft", "ฉบับร่าง"), ("done", "สำเร็จ"), ("error", "ผิดพลาด")],
        default="draft",
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users", string="ผู้ถาม", default=lambda self: self.env.user,
        readonly=True,
    )

    @api.depends("prompt")
    def _compute_name(self):
        for rec in self:
            lines = (rec.prompt or "").strip().splitlines()
            rec.name = (lines[0][:60] if lines else "") or "คำถามใหม่"

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
    # Actions
    # ------------------------------------------------------------------
    def action_ask(self):
        """Send :attr:`prompt` to the configured endpoint and store the answer."""
        self.ensure_one()
        if not (self.prompt or "").strip():
            raise UserError("กรุณากรอกคำถามก่อน")

        config = self._get_ai_config()
        messages = [
            {"role": "system", "content": config["system_prompt"]},
            {"role": "user", "content": self.prompt},
        ]
        try:
            answer = chat_completion(
                config["base_url"],
                config["model"],
                messages,
                api_key=config["api_key"],
                timeout=config["timeout"],
            )
        except AiClientError as exc:
            # Persist the failure (a raise would roll the write back) and
            # surface it to the user with a notification instead.
            self.write({"state": "error", "response": False, "error_message": str(exc)})
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

        self.write(
            {
                "response": answer,
                "state": "done",
                "error_message": False,
                "model_used": config["model"],
            }
        )
        return True
