from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="direct",
        required=True,
        tracking=True,
    )
