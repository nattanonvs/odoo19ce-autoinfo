# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class Od19PaymentChequeCollect(models.Model):
    _name = "od19.payment.cheque.collect"
    _description = "Payment Cheque Collect Line"
    _check_company_auto = True
    _order = "id"

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="payment_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="payment_id.currency_id",
        store=True,
        readonly=True,
    )
    name = fields.Char(
        string="เลขที่เช็ค / Cheque No",
        required=True,
    )
    bank_id = fields.Many2one(
        comodel_name="res.bank",
        string="ธนาคาร / Bank",
    )
    bank_branch = fields.Char(string="สาขา / Bank Branch")
    cheque_date = fields.Date(
        string="วันที่เช็ค / Cheque Date",
        default=fields.Date.context_today,
    )
    amount = fields.Monetary(
        string="จำนวนเช็ค / Amount",
        currency_field="currency_id",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="ช่องทางธนาคาร / Bank Journal",
        domain="[('type', '=', 'bank')]",
        check_company=True,
    )
