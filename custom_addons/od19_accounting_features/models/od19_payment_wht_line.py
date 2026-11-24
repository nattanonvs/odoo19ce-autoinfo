# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class Od19PaymentWhtLine(models.Model):
    """Withholding tax detail line of a payment (มติ K2/K3).

    Replaces the single ``od19_wht_invoice_amount`` field by an editable list
    of lines, each one targeting a WHT type (``account.withholding.tax`` from
    the OCA ``l10n_th_account_tax`` module). The journal entry is built from
    these lines by ``account.payment._prepare_move_withholding_lines``.
    """

    _name = "od19.payment.wht.line"
    _description = "Payment Withholding Tax Line"
    _check_company_auto = True

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="ชำระเงิน / Payment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="payment_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="payment_id.currency_id",
        store=True,
        readonly=True,
    )
    tax_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="ประเภทหัก ณ ที่จ่าย / WHT Type",
        check_company=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        related="tax_id.account_id",
        string="บัญชีหัก ณ ที่จ่าย / WHT Account",
        store=True,
        readonly=True,
    )
    income_type = fields.Selection(
        related="tax_id.wht_cert_income_type",
        string="ประเภทเงินได้ / Type of Income",
        store=True,
        readonly=False,
    )
    pay_amount = fields.Monetary(
        string="ยอดเงินได้ / Income Amount",
        currency_field="currency_id",
        help="ฐานเงินได้ที่นำมาหักภาษี ณ ที่จ่าย.",
    )
    wht_amount = fields.Monetary(
        string="ยอดหัก ณ ที่จ่าย / WHT Amount",
        currency_field="currency_id",
        compute="_compute_wht_amount",
        store=True,
        readonly=False,
        help="ยอดภาษีหัก ณ ที่จ่าย (แก้ไขได้ — มติ K4/K5).",
    )

    @api.depends("tax_id", "pay_amount", "currency_id")
    def _compute_wht_amount(self):
        for line in self:
            rate = (line.tax_id.amount or 0.0) / 100.0
            amount = (line.pay_amount or 0.0) * rate
            line.wht_amount = line.currency_id.round(amount)
