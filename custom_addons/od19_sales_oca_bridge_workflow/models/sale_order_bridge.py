from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_requires_tier_validation = fields.Boolean(
        string="Requires Commercial Approval",
        default=False,
        help="Flags sale orders that should enter the OCA approval flow before confirmation.",
    )
    od19_invoice_plan_mode = fields.Selection(
        [("none", "None"), ("event", "Event-based"), ("schedule", "Scheduled")],
        default="none",
    )
