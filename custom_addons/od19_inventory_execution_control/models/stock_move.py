from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    od19_reference_document = fields.Char(
        compute="_compute_od19_reference_document",
        store=True,
        readonly=True,
    )

    @api.depends("origin", "picking_id.origin")
    def _compute_od19_reference_document(self):
        for move in self:
            move.od19_reference_document = move.origin or move.picking_id.origin or False
