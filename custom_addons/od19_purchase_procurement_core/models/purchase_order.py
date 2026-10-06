from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        compute="_compute_od19_entry_mode",
        store=True,
        readonly=True,
        precompute=True,
    )

    @api.depends("requisition_id")
    def _compute_od19_entry_mode(self):
        for order in self:
            order.od19_entry_mode = (
                "requisition" if order.requisition_id else "direct"
            )
