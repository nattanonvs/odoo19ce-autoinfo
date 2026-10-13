# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    enable_supplier_quality_block = fields.Boolean(
        string="บล็อก PO จากผู้จำหน่ายที่ไม่ผ่านเกณฑ์",
        default=True,
        help="ถ้าเปิดใช้งาน ระบบจะไม่อนุญาตให้สร้าง PO "
        "กับผู้จำหน่ายที่สถานะเป็น disqualified, suspended หรือ rejected "
        "เว้นแต่ผู้จัดการจะยืนยัน override พร้อมเหตุผล",
    )
