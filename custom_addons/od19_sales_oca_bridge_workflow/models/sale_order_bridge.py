from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "tier.validation"]

    _state_from = ["draft", "sent", "waiting_approval"]
    _state_to = ["sale"]
    _tier_validation_manual_config = False

    state = fields.Selection(
        selection_add=[("waiting_approval", "Waiting Approval")],
        ondelete={"waiting_approval": "set default"},
    )

    od19_delivery_state_bridge_ready = fields.Boolean(
        string="Required-Now: Delivery State Bridge Ready",
        compute="_compute_od19_required_now_bridge_state",
        readonly=True,
        help="Indicates that the required-now delivery-state bridge is active through OCA delivery status capabilities on sale orders.",
    )
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
        string="Requires Tier Validation",
        compute="_compute_od19_requires_tier_validation",
        help="Indicates that this sale order requires tier validation before it can be confirmed.",
    )
    od19_invoice_plan_mode = fields.Selection(
        [("none", "None"), ("event", "Event-based"), ("schedule", "Scheduled")],
        string="Deferred: Invoice Plan Mode",
        default="none",
        help="Reserved for a deferred OCA invoice-plan integration, not the required-now baseline.",
    )

    @api.depends("need_validation", "review_ids")
    def _compute_od19_requires_tier_validation(self):
        for order in self:
            order.od19_requires_tier_validation = bool(order.need_validation) or bool(
                order.review_ids
            )

    @api.model
    def _od19_required_now_bridge_capabilities(self):
        order_model = self.env["sale.order"]
        order_class = type(order_model)
        return {
            "delivery": (
                "delivery_status" in order_model._fields
                and "force_delivery_state" in order_model._fields
                and hasattr(order_class, "action_force_delivery_state")
            ),
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
            order.od19_delivery_state_bridge_ready = capabilities["delivery"]
            order.od19_revision_bridge_ready = capabilities["revision"]
            order.od19_exception_bridge_ready = capabilities["exception"]
            order.od19_blanket_bridge_ready = capabilities["blanket"]

    def action_confirm(self):
        """Confirm sale orders, routing through tier validation when needed.

        Orders that require tier validation are moved to the
        ``waiting_approval`` state and a validation request is created
        instead of being confirmed directly. Orders already waiting for
        approval can only be confirmed once every tier has been
        validated.
        """
        awaiting_approval = self.browse()
        for order in self:
            # ``need_validation`` is a non-stored computed field, so its cached
            # value may still be the one computed before a review was created
            # or validated. Drop it so the checks below see the current state.
            order.invalidate_recordset(["need_validation"])
            if order.state == "waiting_approval":
                if order.validation_status != "validated":
                    raise ValidationError(
                        _(
                            "This sale order is waiting for tier validation "
                            "before it can be confirmed."
                        )
                    )
            elif order.state in ("draft", "sent") and order.need_validation:
                awaiting_approval |= order
        if awaiting_approval:
            awaiting_approval.write({"state": "waiting_approval"})
            awaiting_approval.request_validation()
        remaining = self - awaiting_approval
        if remaining:
            return super(SaleOrder, remaining).action_confirm()
        return True

    def _confirmation_error_message(self):
        """Let a fully validated order leave the ``waiting_approval`` state.

        The tier validation engine already blocks the ``state = 'sale'``
        write while a review is still open, so only the standard
        draft/sent guard needs to be relaxed for validated orders.
        """
        self.ensure_one()
        if self.state == "waiting_approval" and self.validation_status == "validated":
            return False
        return super()._confirmation_error_message()
