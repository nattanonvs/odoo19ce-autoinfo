import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    """Vendor-side risk gate.

    A partner flagged as ``blacklisted`` is cut off from every purchase
    activity: no new RFQ can be created, an existing RFQ cannot be switched
    to another vendor, and the RFQ can no longer be confirmed into a
    purchase order.
    """

    _inherit = "purchase.order"

    od19_risk_status_snapshot = fields.Selection(
        selection=[("normal", "Normal"), ("blacklisted", "Blacklisted")],
        string="Risk Snapshot",
        copy=False,
        readonly=True,
    )
    od19_gate_blocked_reason = fields.Char(
        string="Gate Blocked Reason",
        compute="_compute_od19_gate_blocked_reason",
    )

    def _compute_od19_gate_blocked_reason(self):
        for order in self:
            _reason, message = order._od19_check_partner_gate("read")
            order.od19_gate_blocked_reason = message or ""

    def _od19_check_partner_gate(self, stage):
        self.ensure_one()
        # The blacklist field is restricted to credit reviewers / partner
        # managers, but the gate must run for every purchase user.  Read it
        # with sudo() so the check raises the intended UserError.
        commercial = self.partner_id.commercial_partner_id.sudo()
        if commercial.od19_blacklist_status == "blacklisted":
            return (
                "blacklist",
                _("Blacklist: vendor %s is blacklisted and cannot be purchased from.")
                % commercial.display_name,
            )
        return (None, None)

    def _od19_log_gate_event(self, partner, reason_code, stage, order_ref=False):
        """Log a blocked purchase document on the shared gate-event model."""
        order_ref = order_ref or (self.display_name if self else "")
        self.env["od19.credit.gate.event"].sudo().create(
            {
                "partner_id": partner.id,
                "reason_code": reason_code,
                "stage": stage,
                "order_ref": order_ref,
            }
        )
        _logger.info(
            "od19 risk gate blocked [stage=%s reason=%s] document=%s partner=%s",
            stage,
            reason_code,
            order_ref,
            partner.display_name,
        )

    def _od19_raise_if_blocked(self, stage):
        reason_code, message = self._od19_check_partner_gate(stage)
        if reason_code:
            self._od19_log_gate_event(
                self.partner_id.commercial_partner_id, reason_code, stage
            )
            raise UserError(message)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.state in ("draft", "sent"):
                order._od19_raise_if_blocked("rfq_create")
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "partner_id" in vals:
            for order in self:
                if order.state in ("draft", "sent"):
                    order._od19_raise_if_blocked("rfq_write")
        return res

    def button_confirm(self):
        for order in self:
            order._od19_raise_if_blocked("purchase_confirm")
        res = super().button_confirm()
        for order in self:
            commercial = order.partner_id.commercial_partner_id.sudo()
            order.write(
                {"od19_risk_status_snapshot": commercial.od19_blacklist_status}
            )
        return res

    def button_approve(self, force=False):
        for order in self:
            order._od19_raise_if_blocked("purchase_confirm")
        return super().button_approve(force=force)
