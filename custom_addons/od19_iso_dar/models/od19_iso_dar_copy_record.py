# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class Od19IsoDarCopyRecord(models.Model):
    _name = "od19.iso.dar.copy.record"
    _description = "ISO DAR Copy Record"
    _order = "id desc"

    dar_id = fields.Many2one(
        "od19.iso.dar", string="ใบคำขอ DAR", required=True, ondelete="cascade"
    )
    copy_type = fields.Selection(
        [("controlled", "สำเนาควบคุม"), ("uncontrolled", "สำเนาไม่ควบคุม")],
        string="ประเภทสำเนา",
        default="controlled",
        required=True,
    )
    recipient_id = fields.Many2one("res.users", string="ผู้รับสำเนา")
    copy_number = fields.Char(string="เลขที่สำเนา")
    issued_date = fields.Date(string="วันที่จ่ายสำเนา", default=fields.Date.today)
    note = fields.Char(string="หมายเหตุ")
