# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    od19_price_unit = fields.Float(
        string="Unit Price / ราคาต่อหน่วย",
        digits="Product Price",
        default=0.0,
        help="Unit price to be propagated to the purchase order line.",
    )
    od19_discount = fields.Float(
        string="Discount (%) / ส่วนลด (%)",
        digits="Discount",
        default=0.0,
        help="Discount percentage to be propagated to the purchase order line.",
    )
    od19_taxes_id = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes / ภาษี",
        domain=[("type_tax_use", "=", "purchase")],
        help="Taxes to be propagated to the purchase order line.",
    )
