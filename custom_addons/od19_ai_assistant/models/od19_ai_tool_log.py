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
        [
            ("read", "อ่าน"),
            ("draft", "ร่าง"),
            ("external", "ภายนอก"),
            ("meta", "เมตา"),
        ],
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
