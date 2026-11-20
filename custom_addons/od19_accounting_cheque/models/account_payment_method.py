# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        # Cheque received from a customer. Available on every bank/cash journal
        # so a payment method line is auto-created for each of them.
        res["od19_cheque"] = {"mode": "multi", "type": ("bank", "cash")}
        return res
