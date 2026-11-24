# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class Od19PaymentVatLine(models.Model):
    """VAT detail line of a payment.

    The VAT amount is booked on the journal entry but, per มติ K9, it is **not**
    deducted from the net received amount. For deferred (undue) VAT the
    ``vat_date`` can be adjusted independently of the payment date.
    """

    _name = "od19.payment.vat.line"
    _description = "Payment VAT Line"
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
        comodel_name="account.tax",
        string="ภาษี / Tax",
        check_company=True,
    )
    base_amount = fields.Monetary(
        string="ฐานภาษี / Base Amount",
        currency_field="currency_id",
    )
    vat_amount = fields.Monetary(
        string="ยอดภาษีมูลค่าเพิ่ม / VAT Amount",
        currency_field="currency_id",
        compute="_compute_vat_amount",
        store=True,
        readonly=False,
        help="ยอด VAT = ฐานภาษี x อัตรา (แก้ไขได้ — มติ K4/K5).",
    )
    vat_date = fields.Date(
        string="วันที่ภาษี / VAT Date",
        default=fields.Date.context_today,
        help="วันที่ของภาษีมูลค่าเพิ่ม แก้ไขได้แยกจากวันชำระ สำหรับ "
        "ภาษีขาย/ภาษีซื้อที่ยังไม่ถึงกำหนด (undue VAT — มติ K9).",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="เอกสารอ้างอิง / Reference Document",
    )

    @api.depends("tax_id", "base_amount", "currency_id")
    def _compute_vat_amount(self):
        for line in self:
            rate = (line.tax_id.amount or 0.0) / 100.0
            amount = (line.base_amount or 0.0) * rate
            line.vat_amount = line.currency_id.round(amount)
