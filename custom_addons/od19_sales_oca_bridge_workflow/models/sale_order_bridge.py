from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_enable_revision = fields.Boolean(
        string="Enable Revision Tracking",
        default=False,
        help="Marks orders that should use the required-now OCA revision baseline.",
    )
    od19_use_exception_rules = fields.Boolean(
        string="Use Exception Rules",
        default=False,
        help="Marks orders that should use the required-now OCA sale exception baseline.",
    )
    od19_use_blanket_order = fields.Boolean(
        string="Use Blanket Orders",
        default=False,
        help="Marks orders that should use the required-now OCA blanket order baseline.",
    )
    od19_requires_tier_validation = fields.Boolean(
        string="Deferred: Tier Validation",
        default=False,
        help="Reserved for a deferred OCA tier-validation integration, not the required-now baseline.",
    )
    od19_invoice_plan_mode = fields.Selection(
        [("none", "None"), ("event", "Event-based"), ("schedule", "Scheduled")],
        string="Deferred: Invoice Plan Mode",
        default="none",
        help="Reserved for a deferred OCA invoice-plan integration, not the required-now baseline.",
    )
