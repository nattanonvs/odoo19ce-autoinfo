from odoo import fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    od19_justification = fields.Text(
        string="เหตุผลรายการ / Line Justification",
    )
    od19_asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Asset ที่เกี่ยวข้อง / Related Asset",
        ondelete="set null",
        help="ถ้ารายการนี้เกี่ยวข้องกับ asset ที่มีอยู่",
    )
