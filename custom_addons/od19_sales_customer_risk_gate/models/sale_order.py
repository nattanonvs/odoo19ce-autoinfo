import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_is_credit_sale = fields.Boolean(
        string="Credit Sale",
        compute="_compute_od19_is_credit_sale",
        store=True,
        copy=False,
        help="This order uses a credit payment term.",
    )
    od19_risk_status_snapshot = fields.Selection(
        selection=[("normal", "Normal"), ("blacklisted", "Blacklisted")],
        string="Risk Snapshot",
        copy=False,
        readonly=True,
    )
    od19_credit_state_snapshot = fields.Selection(
        selection=[
            ("not_requested", "Not Requested"),
            ("pending", "Pending Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Credit Snapshot",
        copy=False,
        readonly=True,
    )
    od19_gate_blocked_reason = fields.Char(
        string="Gate Blocked Reason",
        compute="_compute_od19_gate_blocked_reason",
    )

    @api.depends("payment_term_id.od19_is_credit_term")
    def _compute_od19_is_credit_sale(self):
        for order in self:
            order.od19_is_credit_sale = bool(
                order.payment_term_id and order.payment_term_id.od19_is_credit_term
            )

    def _compute_od19_gate_blocked_reason(self):
        for order in self:
            _reason, message = order._od19_check_customer_gate("read")
            order.od19_gate_blocked_reason = message or ""

    def _od19_check_customer_gate(self, stage):
        self.ensure_one()
        commercial = self.partner_id.commercial_partner_id
        if commercial.od19_blacklist_status == "blacklisted":
            return (
                "blacklist",
                _("Blacklist: customer %s is blacklisted and cannot be sold to.")
                % commercial.display_name,
            )
        if self.od19_is_credit_sale and not commercial.od19_credit_sale_allowed:
            return (
                "credit",
                _(
                    "credit: customer %s is not approved for credit sales. "
                    "Request credit approval or use a cash payment term."
                )
                % commercial.display_name,
            )
        return (None, None)

    def _od19_log_gate_event(self, reason_code, stage):
        self.ensure_one()
        _logger.info(
            "od19 credit gate blocked [stage=%s reason=%s] order=%s partner=%s",
            stage,
            reason_code,
            self.display_name,
            self.partner_id.display_name,
        )

    def _od19_raise_if_blocked(self, stage):
        reason_code, message = self._od19_check_customer_gate(stage)
        if reason_code:
            self._od19_log_gate_event(reason_code, stage)
            raise UserError(message)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.state in ("draft", "sent"):
                order._od19_raise_if_blocked("quotation_create")
        return orders

    def write(self, vals):
        res = super().write(vals)
        gate_fields = {"partner_id", "payment_term_id"}
        if gate_fields.intersection(vals):
            for order in self:
                if order.state in ("draft", "sent"):
                    order._od19_raise_if_blocked("quotation_write")
        return res

    def action_confirm(self):
        for order in self:
            order._od19_raise_if_blocked("order_confirm")
        res = super().action_confirm()
        for order in self:
            commercial = order.partner_id.commercial_partner_id
            order.write(
                {
                    "od19_risk_status_snapshot": commercial.od19_blacklist_status,
                    "od19_credit_state_snapshot": commercial.od19_credit_request_state,
                }
            )
        return res
