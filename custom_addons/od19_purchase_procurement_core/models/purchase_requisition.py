from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="requisition",
        required=True,
        tracking=True,
    )
