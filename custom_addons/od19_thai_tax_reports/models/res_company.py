# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_enforce_86_4_validation = fields.Boolean(
        string="ตรวจสอบรายการใบกำกับภาษีเต็มรูป (ม.86/4)",
        default=True,
        help="เมื่อเปิดใช้งาน ระบบจะตรวจสอบว่าใบกำกับภาษีขายเต็มรูป "
        "(ขายให้นิติบุคคลที่มีเลขประจำตัวผู้เสียภาษี) มีรายการครบทั้ง 8 ข้อ "
        "ตามมาตรา 86/4 แห่งประมวลรัษฎากร ก่อนอนุญาตให้ Post เอกสาร",
    )
