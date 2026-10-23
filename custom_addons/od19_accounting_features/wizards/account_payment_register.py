# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        # The "Register Payment" wizard always starts from an existing
        # invoice/bill, so the Vendor Bill (ตั้งหนี้) is already present and the
        # AP bill-first rule is satisfied. Mark the context so
        # ``account.payment.action_post`` does not block these payments (the
        # bill link is only materialised after reconciliation).
        self = self.with_context(od19_skip_vendor_bill_check=True)
        return super()._create_payments()
