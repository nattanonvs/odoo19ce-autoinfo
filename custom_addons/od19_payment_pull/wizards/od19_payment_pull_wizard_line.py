# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


class Od19PaymentPullWizardLine(models.TransientModel):
    _name = "od19.payment.pull.wizard.line"
    _description = "OD19 Payment Pull Wizard Line"

    wizard_id = fields.Many2one(
        "od19.payment.pull.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="เลือก / Select", default=True)
    move_id = fields.Many2one(
        "account.move",
        string="เอกสาร / Document",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    ref = fields.Char(
        string="เลขที่ / Number",
        related="move_id.name",
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="คู่ค้า / Partner",
        related="move_id.partner_id",
        readonly=True,
    )
    invoice_date = fields.Date(
        string="วันที่เอกสาร / Invoice date",
        related="move_id.invoice_date",
        readonly=True,
    )
    date_due = fields.Date(
        string="กำหนดชำระ / Due date",
        related="move_id.invoice_date_due",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน / Currency",
        related="move_id.currency_id",
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="ยอดรวม / Total",
        related="move_id.amount_total",
        currency_field="currency_id",
        readonly=True,
    )
    # Residual expressed in the document currency so it matches the payment.
    amount_residual = fields.Monetary(
        string="ยอดค้าง (สกุลเอกสาร) / Residual",
        related="move_id.amount_residual",
        currency_field="currency_id",
        readonly=True,
    )
    amount_to_pay = fields.Monetary(
        string="ยอดจ่ายครั้งนี้ / Amount to pay",
        currency_field="currency_id",
        default=0.0,
    )
    is_partial = fields.Boolean(
        string="จ่ายบางส่วน / Partial",
        compute="_compute_is_partial",
        store=True,
    )

    @api.depends("amount_to_pay", "amount_residual")
    def _compute_is_partial(self):
        for line in self:
            line.is_partial = (
                line.currency_id.compare_amounts(line.amount_to_pay, line.amount_residual)
                < 0
            )
