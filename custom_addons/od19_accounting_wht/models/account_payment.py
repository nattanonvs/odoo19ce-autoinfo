from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    wht_type_id = fields.Many2one(
        "wht.type",
        string="WHT Type",
        tracking=True,
    )
    wht_base_amount = fields.Monetary(
        string="WHT Base Amount",
        currency_field="currency_id",
        help="Base amount used to compute withholding tax.",
    )
    wht_amount = fields.Monetary(
        string="WHT Amount",
        currency_field="currency_id",
        compute="_compute_wht_amount",
        store=True,
        readonly=True,
    )
    wht_net_amount = fields.Monetary(
        string="Net Amount After WHT",
        currency_field="currency_id",
        compute="_compute_wht_net_amount",
        store=True,
        readonly=True,
    )

    @api.depends("wht_base_amount", "wht_type_id")
    def _compute_wht_amount(self):
        for payment in self:
            if payment.wht_type_id and payment.wht_base_amount:
                payment.wht_amount = (
                    payment.wht_base_amount * payment.wht_type_id.percent / 100.0
                )
            else:
                payment.wht_amount = 0.0

    @api.depends("wht_base_amount", "wht_amount")
    def _compute_wht_net_amount(self):
        for payment in self:
            payment.wht_net_amount = (
                payment.wht_base_amount - payment.wht_amount
            )
