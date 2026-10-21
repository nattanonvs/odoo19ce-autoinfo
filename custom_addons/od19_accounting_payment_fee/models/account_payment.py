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

        # Determine which line is the liquidity line and adjust it
        liquidity_account_id = self.journal_id.default_account_id.id
        for line_vals in res:
            if line_vals.get("account_id") == liquidity_account_id:
                # Adjust the liquidity amount by the fee
                amount_currency = line_vals.get("amount_currency", 0.0)
                if self.payment_type == "inbound":
                    # Customer payment: bank gets less
                    line_vals["amount_currency"] = amount_currency - fee
                    if line_vals.get("debit", 0.0) > 0:
                        line_vals["debit"] = max(0.0, line_vals["debit"] - fee_balance)
                    else:
                        line_vals["credit"] = line_vals.get("credit", 0.0) + fee_balance
                else:
                    # Vendor payment: bank pays more
                    line_vals["amount_currency"] = amount_currency - fee
                    if line_vals.get("credit", 0.0) > 0:
                        line_vals["credit"] = line_vals["credit"] + fee_balance
                    else:
                        line_vals["debit"] = max(0.0, line_vals["debit"] - fee_balance)

        # Add the fee line
        if self.payment_type == "inbound":
            # Customer payment: fee is our expense -> Debit fee account
            res.append({
                "name": _("Payment fee: %s") % self.name,
                "account_id": self.fee_account_id.id,
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "amount_currency": fee,
                "debit": fee_balance if fee_balance > 0 else 0.0,
                "credit": -fee_balance if fee_balance < 0 else 0.0,
                "date_maturity": self.date,
            })
        else:
            # Vendor payment: fee is our expense -> Debit fee account
            res.append({
                "name": _("Payment fee: %s") % self.name,
                "account_id": self.fee_account_id.id,
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "amount_currency": fee,
                "debit": fee_balance if fee_balance > 0 else 0.0,
                "credit": -fee_balance if fee_balance < 0 else 0.0,
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
