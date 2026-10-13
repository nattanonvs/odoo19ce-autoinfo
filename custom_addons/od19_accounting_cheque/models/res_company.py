# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cheque_received_account_id = fields.Many2one(
        "account.account",
        string="Cheque Received Account",
    )
    cheque_paid_account_id = fields.Many2one(
        "account.account",
        string="Cheque Paid Account",
    )
    cheque_return_account_id = fields.Many2one(
        "account.account",
        string="Cheque Return Account",
    )
    show_ac_payee = fields.Boolean(
        string="Default A/C Payee",
        default=False,
    )
