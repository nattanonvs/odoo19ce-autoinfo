# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


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

    # SELF_READABLE_FIELDS / SELF_WRITEABLE_FIELDS are @property on the base
    # model in Odoo 19, so they must be extended by overriding the property
    # (the base docstring documents this override contract) rather than by
    # concatenating the base value as a class attribute.
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["od19_ai_capability_mode"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["od19_ai_capability_mode"]

    @api.model
    def _od19_ai_default_mode(self):
        mode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_ai.capability_mode")
        )
        return mode if mode in ("read_only", "read_draft") else "read_only"
