from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_contract_id = fields.Many2one("od19.sales.contract", tracking=True)
