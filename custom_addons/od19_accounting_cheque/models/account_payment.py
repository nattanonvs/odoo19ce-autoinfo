# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    cheque_id = fields.Many2one(
        "account.cheque",
        string="Cheque",
        copy=False,
    )
    cheque_paid_id = fields.Many2one(
        "account.cheque",
        string="Paid Cheque",
        copy=False,
    )
    pay_to = fields.Char(string="Pay To")

    def action_post(self):
        res = super().action_post()
        for rec in self:
            if rec.cheque_paid_id:
                vals = {
                    "pay_to": rec.pay_to or rec.partner_id.name,
                    "cheque_date": rec.date,
                    "due_date": rec.date,
                    "amount": rec.amount,
                    "state": "confirmed",
                    "partner_id": rec.partner_id.id,
                    "journal_id": rec.journal_id.id,
                    "currency_id": rec.currency_id.id,
                }
                rec.cheque_paid_id.write(vals)
        return res
