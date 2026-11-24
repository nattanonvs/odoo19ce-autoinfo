from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    od19_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Bring Forward",
        copy=False,
    )
