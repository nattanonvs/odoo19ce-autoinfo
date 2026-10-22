# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    fee_amount = fields.Monetary(
        string="Payment Fee",
        currency_field="currency_id",
        help="Bank fee or service charge deducted from this payment.",
    )
    fee_account_id = fields.Many2one(
        "account.account",
        string="Fee Account",
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost'))]",
        help="Account to post the payment fee to (e.g., Bank Charges).",
    )

    @api.constrains("fee_amount")
    def _check_fee_amount(self):
        for pay in self:
            if pay.fee_amount < 0:
                raise ValidationError(_("Payment fee cannot be negative."))

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        """Override to inject fee line and adjust liquidity amount.

        For customer payment with fee: bank receives (amount - fee)
        For vendor payment with fee: bank pays (amount + fee)
        The fee is posted to fee_account_id.

        Odoo 19 prepares the payment journal items with ``balance`` and
        ``amount_currency`` keys (the ``debit`` / ``credit`` keys used by
        earlier versions no longer exist), and the liquidity line is booked on
        the journal's outstanding account rather than its default account.
        """
        res = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )
        if not self.fee_amount or not self.fee_account_id:
            return res

        fee = self.fee_amount
        company_currency = self.company_id.currency_id
        fee_balance = self.currency_id._convert(
            fee, company_currency, self.company_id, self.date
        )

        # Adjust the liquidity line: the bank receives less for an inbound
        # payment and pays more for an outbound payment, so in both cases the
        # liquidity balance is reduced by the fee.
        liquidity_account_id = self.outstanding_account_id.id
        for line_vals in res:
            if line_vals.get("account_id") == liquidity_account_id:
                line_vals["amount_currency"] = line_vals.get("amount_currency", 0.0) - fee
                line_vals["balance"] = line_vals.get("balance", 0.0) - fee_balance

        # Add the fee expense line (debit) so the journal entry stays balanced.
        res.append({
            "name": _("Payment fee: %s") % self.name,
            "account_id": self.fee_account_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "amount_currency": fee,
            "balance": fee_balance,
            "date_maturity": self.date,
        })

        return res

    def action_post(self):
        """Validate fee configuration before posting."""
        for pay in self:
            if pay.fee_amount and not pay.fee_account_id:
                raise ValidationError(_(
                    "Payment fee is set but no fee account is selected. "
                    "Please choose a fee account before posting."
                ))
        return super().action_post()
