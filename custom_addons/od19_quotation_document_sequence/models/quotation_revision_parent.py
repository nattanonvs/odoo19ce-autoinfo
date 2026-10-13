from odoo import fields, models


class QuotationRevisionParent(models.Model):
    _name = "quotation.revision.parent"
    _description = "Quotation Revision Parent"

    parent_id = fields.Many2one("sale.order", string="Parent Revision")
    sale_order_id = fields.Many2one("sale.order", string="Current Revision", readonly=True)
    name = fields.Char(related="sale_order_id.name", string="Name")
