# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

# Sequence code used to draw the Thai document number shown on the
# payment voucher / payment receipt, keyed by the Odoo payment direction.
VOUCHER_SEQUENCE_BY_PAYMENT_TYPE = {
    "outbound": "account.voucher.vendor.payment",
    "inbound": "account.voucher.customer.payment",
}


class AccountPayment(models.Model):
    _inherit = "account.payment"

    od19_voucher_no = fields.Char(
        string="เลขที่ใบสำคัญ / Voucher No.",
        copy=False,
        readonly=True,
        help="เลขที่ใบสำคัญจ่าย (PV) หรือใบสำคัญรับเงิน (RV) ที่รันจาก ir.sequence",
    )

    def _od19_voucher_sequence_code(self):
        self.ensure_one()
        return VOUCHER_SEQUENCE_BY_PAYMENT_TYPE.get(self.payment_type)

    def _od19_assign_voucher_number(self):
        """Assign the Thai document number once, based on the payment direction."""
        for payment in self:
            if payment.od19_voucher_no:
                continue
            sequence_code = payment._od19_voucher_sequence_code()
            if not sequence_code:
                continue
            number = self.env["ir.sequence"].next_by_code(sequence_code)
            if number:
                payment.od19_voucher_no = number
        return True

    def action_post(self):
        res = super().action_post()
        self._od19_assign_voucher_number()
        return res
