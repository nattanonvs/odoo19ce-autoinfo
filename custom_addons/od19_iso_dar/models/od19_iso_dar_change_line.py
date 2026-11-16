# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class Od19IsoDarChangeLine(models.Model):
    _name = "od19.iso.dar.change.line"
    _description = "ISO DAR Change Line"

    dar_id = fields.Many2one(
        "od19.iso.dar", string="ใบคำขอ DAR", required=True, ondelete="cascade"
    )
    field_changed = fields.Char(string="หัวข้อ/ประเด็นที่เปลี่ยน")
    before_value = fields.Char(string="ค่าเดิม")
    after_value = fields.Char(string="ค่าใหม่")
    impact = fields.Text(string="ผลกระทบ")
    note = fields.Char(string="หมายเหตุ")
