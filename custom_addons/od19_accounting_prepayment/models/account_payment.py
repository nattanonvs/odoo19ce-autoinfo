# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------------------------------------------------------
    # Prepare Payment link (OCA ``account.billing``).
    #
    # Works for both directions:
    #   * ``in_invoice``  -> vendor bills      (pay)
    #   * ``out_invoice`` -> customer invoices (receive)
    # ------------------------------------------------------------------
    od19_prepayment_id = fields.Many2one(
        comodel_name="account.billing",
        string="Prepare Payment",
        domain="[('bill_type', '=', od19_prepayment_bill_type),"
        " ('state', '=', 'billed'),"
        " ('company_id', '=', company_id)]",
        check_company=True,
        copy=False,
        groups="account.group_account_invoice",
        help="Select a validated Prepare Payment document to pull its partner, "
        "direction, amount and invoices into this payment.",
    )
    od19_prepayment_bill_type = fields.Selection(
        selection=[("out_invoice", "Customer Invoice"), ("in_invoice", "Vendor Bill")],
        compute="_compute_od19_prepayment_bill_type",
        groups="account.group_account_invoice",
    )
    od19_prepayment_count = fields.Integer(
        string="Prepare Payment count",
        compute="_compute_od19_prepayment_count",
        groups="account.group_account_invoice",
    )

    @api.depends("partner_type")
    def _compute_od19_prepayment_bill_type(self):
        for payment in self:
            payment.od19_prepayment_bill_type = (
                "in_invoice" if payment.partner_type == "supplier" else "out_invoice"
            )

    @api.onchange("od19_prepayment_id")
    def _onchange_od19_prepayment_id(self):
        """Pull the Prepare Payment content into the (draft) payment."""
        for payment in self:
            billing = payment.od19_prepayment_id
            if not billing:
                continue
            is_customer = billing.bill_type == "out_invoice"
            payment.partner_type = "customer" if is_customer else "supplier"
            payment.payment_type = "inbound" if is_customer else "outbound"
            payment.partner_id = billing.partner_id
            payment.currency_id = billing.currency_id
            payment.amount = billing.amount_due or billing.amount_total
            payment.invoice_ids = [Command.set(billing.billing_line_ids.move_id.ids)]

    def _compute_od19_prepayment_count(self):
        for payment in self:
            payment.od19_prepayment_count = len(payment._od19_prepayments())

    def _od19_prepayments(self):
        """All Prepare Payment documents (both directions) linked to this payment."""
        self.ensure_one()
        moves = self.invoice_ids | self.reconciled_bill_ids | self.reconciled_invoice_ids
        prepayments = moves.billing_ids | self.od19_prepayment_id
        return prepayments.filtered(
            lambda billing: billing.bill_type in ("in_invoice", "out_invoice")
        )

    def action_od19_open_prepayments(self):
        """Open the Prepare Payment documents linked to this payment."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Prepare Payments"),
            "res_model": "account.billing",
            "view_mode": "list,form",
            "domain": [("id", "in", self._od19_prepayments().ids)],
            "context": {"create": False},
        }

    def action_od19_register_payment(self):
        """Open the Register Payment wizard for the selected Prepare Payment.

        This is the reliable Odoo 19 way to actually reconcile the pulled
        invoices against the payment.
        """
        self.ensure_one()
        moves = self.od19_prepayment_id.billing_line_ids.move_id.filtered(
            lambda move: move.state == "posted"
        )
        if not moves:
            raise UserError(
                _("The selected Prepare Payment has no posted invoice to pay.")
            )
        return moves.action_register_payment()
