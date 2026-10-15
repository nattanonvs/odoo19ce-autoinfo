# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


WHT_RATE_SELECTION = [
    ("1", "1%"),
    ("1.5", "1.5%"),
    ("2", "2%"),
    ("3", "3%"),
    ("5", "5%"),
]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------------------------------------------------------
    # Feature 2: Payer / Payee (also available on payments)
    # ------------------------------------------------------------------
    od19_payer_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จ่ายเงิน / Payer",
        help="Partner who actually pays.",
    )
    od19_payee_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้รับเงิน / Payee",
        help="Partner who actually receives the payment.",
    )

    # ------------------------------------------------------------------
    # Feature 6: WHT base computed from selected invoices
    # ------------------------------------------------------------------
    od19_wht_base_amount = fields.Monetary(
        string="WHT Base Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_base_amount",
        store=True,
        help="Sum of the untaxed amounts of the invoices reconciled "
        "with this payment.",
    )
    od19_wht_rate = fields.Selection(
        selection=WHT_RATE_SELECTION,
        string="WHT Rate",
        default="1",
        help="Withholding tax rate applied to the base amount.",
    )
    od19_wht_type_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="WHT Type",
        help="Withholding tax type (OCA l10n_th_account_tax).",
    )
    od19_wht_amount = fields.Monetary(
        string="WHT Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_amount",
        store=True,
        help="Withholding tax amount = base amount x rate.",
    )

    @api.depends(
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
        "reconciled_invoice_ids.amount_untaxed",
        "reconciled_bill_ids.amount_untaxed",
    )
    def _compute_od19_wht_base_amount(self):
        for payment in self:
            invoices = payment.reconciled_invoice_ids | payment.reconciled_bill_ids
            if not invoices:
                # Fallback: lines tagged with WHT on the payment move.
                wht_lines = payment.move_id.line_ids.filtered("wht_tax_id")
                base = 0.0
                for line in wht_lines:
                    base += abs(line.balance)
                payment.od19_wht_base_amount = base
            else:
                payment.od19_wht_base_amount = sum(
                    invoices.mapped("amount_untaxed")
                )

    @api.depends("od19_wht_base_amount", "od19_wht_rate")
    def _compute_od19_wht_amount(self):
        for payment in self:
            try:
                rate = float(payment.od19_wht_rate or 0.0)
            except (TypeError, ValueError):
                rate = 0.0
            payment.od19_wht_amount = payment.od19_wht_base_amount * rate / 100.0
