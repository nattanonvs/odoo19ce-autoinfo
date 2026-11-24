from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    od19_receipt_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Payment Receipt Bring Forward",
        copy=False,
    )
    od19_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Payment Send Bring Forward",
        copy=False,
    )
