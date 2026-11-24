from odoo import fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    od19_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Bring Forward",
        copy=False,
    )
