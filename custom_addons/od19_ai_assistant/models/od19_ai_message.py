# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class Od19AiMessage(models.Model):
    _name = "od19.ai.message"
    _description = "ข้อความในบทสนทนา AI (OD19)"
    _order = "id asc"

    chat_id = fields.Many2one(
        "od19.ai.chat",
        string="บทสนทนา",
        required=True,
        ondelete="cascade",
        index=True,
    )
    role = fields.Selection(
        [("user", "ผู้ใช้"), ("assistant", "ผู้ช่วย"), ("system", "ระบบ")],
        string="บทบาท",
        required=True,
        default="user",
    )
    content = fields.Text(string="เนื้อหา", required=True)
    author_id = fields.Many2one(
        "res.users",
        string="ผู้ส่ง",
        default=lambda self: self.env.user,
        readonly=True,
    )
