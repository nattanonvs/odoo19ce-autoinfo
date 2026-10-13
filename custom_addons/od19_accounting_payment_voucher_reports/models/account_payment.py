from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    pv_number = fields.Char(
        string="Voucher No.",
        copy=False,
        readonly=True,
        tracking=True,
        help="Thai payment voucher number (PV-YYYY-NNNN).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("pv_number"):
                vals["pv_number"] = self.env["ir.sequence"].next_by_code(
                    "payment.voucher"
                ) or "/"
        return super().create(vals_list)
