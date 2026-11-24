# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------------------------------------------------------
    # Legacy single fee (kept as a fallback for existing records)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Fee detail lines (K2/K3): several fees, each posted on its own account
    # ------------------------------------------------------------------
    od19_fee_ids = fields.One2many(
        comodel_name="od19.payment.fee.line",
        inverse_name="payment_id",
        string="ค่าธรรมเนียม / Fees",
        copy=True,
    )
    od19_fee_amount = fields.Monetary(
        string="ค่าธรรมเนียมรวม / Total Fees",
        currency_field="currency_id",
        compute="_compute_od19_fee_amount",
        store=True,
        help="ผลรวมค่าธรรมเนียมจาก od19_fee_ids "
        "(ถ้าไม่มีบรรทัด ใช้ค่าเดิม fee_amount).",
    )

    @api.depends("od19_fee_ids.amount", "fee_amount")
    def _compute_od19_fee_amount(self):
        for payment in self:
            if payment.od19_fee_ids:
                payment.od19_fee_amount = sum(
                    payment.od19_fee_ids.mapped("amount")
                )
            else:
                payment.od19_fee_amount = payment.fee_amount

    @api.constrains("fee_amount")
    def _check_fee_amount(self):
        for pay in self:
            if pay.fee_amount < 0:
                raise ValidationError(_("Payment fee cannot be negative."))

    @api.depends(
        "amount",
        "od19_wht_amount",
        "payment_type",
        "od19_fee_ids.amount",
        "od19_fee_ids.is_profit",
        "fee_amount",
    )
    def _compute_od19_amount_net(self):
        # EXTENDS 'od19_accounting_features' — subtract the fees from the net.
        # Inbound: a normal fee reduces what we receive, a "profit" fee adds to
        # it. Outbound: a normal fee increases what we pay, a "profit" fee
        # reduces it.
        super()._compute_od19_amount_net()
        for payment in self:
            net = payment.od19_amount_net
            fees = [(fee.amount, fee.is_profit) for fee in payment.od19_fee_ids]
            if not fees and payment.fee_amount:
                # Fallback: the legacy single-field fee is always a normal fee.
                fees = [(payment.fee_amount, False)]
            for amount, is_profit in fees:
                if payment.payment_type == "outbound":
                    net += amount if not is_profit else -amount
                else:
                    net += -amount if not is_profit else amount
            payment.od19_amount_net = net

    # ------------------------------------------------------------------
    # Journal preparation helpers
    # ------------------------------------------------------------------
    def _od19_get_fee_move_lines(self):
        """Journal items for the fee lines (one per detail line).

        Each fee is always booked on its own account. A normal fee is a
        positive amount (debit expense for the payer side), a "profit" fee is
        negative (credit income). The liquidity line is adjusted by the exact
        opposite, so the entry stays balanced.
        """
        self.ensure_one()
        lines = []
        for fee in self.od19_fee_ids:
            if not fee.account_id or not fee.amount:
                continue
            amount_currency = -abs(fee.amount) if fee.is_profit else abs(fee.amount)
            lines.append({
                "name": _("Fee: %s") % (fee.name or self.name),
                "account_id": fee.account_id.id,
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "amount_currency": amount_currency,
                "balance": self._od19_convert_amount(amount_currency),
                "date_maturity": self.date,
                "analytic_distribution": fee.analytic_distribution,
            })
        # Fallback: the legacy single-field fee when no detail line is set.
        if not lines and self.fee_amount and self.fee_account_id:
            amount_currency = abs(self.fee_amount)
            lines.append({
                "name": _("Payment fee: %s") % self.name,
                "account_id": self.fee_account_id.id,
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "amount_currency": amount_currency,
                "balance": self._od19_convert_amount(amount_currency),
                "date_maturity": self.date,
            })
        return lines

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        """Override to inject fee lines and adjust the liquidity amount.

        For a customer payment with fee: the bank receives (amount - fee)
        for a normal fee, or (amount + fee) for a "profit" fee. For a vendor
        payment with a normal fee the bank pays (amount + fee).
        """
        res = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )
        fee_lines = self._od19_get_fee_move_lines()
        if not fee_lines:
            return res

        # The liquidity line moves by the exact opposite of the fee lines.
        liquidity_account_id = self.outstanding_account_id.id
        for line_vals in res:
            if line_vals.get("account_id") == liquidity_account_id:
                for fee_vals in fee_lines:
                    line_vals["amount_currency"] = (
                        line_vals.get("amount_currency", 0.0)
                        - fee_vals["amount_currency"]
                    )
                    line_vals["balance"] = (
                        line_vals.get("balance", 0.0) - fee_vals["balance"]
                    )
        res.extend(fee_lines)
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
