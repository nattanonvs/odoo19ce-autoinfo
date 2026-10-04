from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_revision_bridge_ready = fields.Boolean(
        string="Required-Now: Revision Bridge Ready",
        compute="_compute_od19_required_now_bridge_state",
        readonly=True,
        help="Indicates that the required-now revision bridge is active through OCA revision capabilities on sale orders.",
    )
    od19_exception_bridge_ready = fields.Boolean(
        string="Required-Now: Exception Bridge Ready",
        compute="_compute_od19_required_now_bridge_state",
        readonly=True,
        help="Indicates that the required-now exception bridge is active through OCA exception capabilities on sale orders.",
    )
    od19_blanket_bridge_ready = fields.Boolean(
        string="Required-Now: Blanket Bridge Ready",
        compute="_compute_od19_required_now_bridge_state",
        readonly=True,
        help="Indicates that the required-now blanket bridge is active through OCA blanket-order capabilities on sale orders.",
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

    @api.model
    def _od19_required_now_bridge_capabilities(self):
        order_model = self.env["sale.order"]
        order_class = type(order_model)
        return {
            "revision": (
                "current_revision_id" in order_model._fields
                and "old_revision_ids" in order_model._fields
                and hasattr(order_class, "create_revision")
            ),
            "exception": (
                "exception_ids" in order_model._fields
                and "ignore_exception" in order_model._fields
                and hasattr(order_class, "detect_exceptions")
            ),
            "blanket": "blanket_order_id" in order_model._fields,
        }

    @api.depends()
    def _compute_od19_required_now_bridge_state(self):
        capabilities = self._od19_required_now_bridge_capabilities()
        for order in self:
            order.od19_revision_bridge_ready = capabilities["revision"]
            order.od19_exception_bridge_ready = capabilities["exception"]
            order.od19_blanket_bridge_ready = capabilities["blanket"]
