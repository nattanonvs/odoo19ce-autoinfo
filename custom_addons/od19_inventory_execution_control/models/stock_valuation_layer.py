# -*- coding: utf-8 -*-
# stock.valuation.layer was removed in Odoo 19. This extension is kept for
# backward compatibility but is only loaded when the model exists (e.g. when
# a third-party module re-introduces it).
from odoo import api, fields, models

try:
    from odoo.addons.stock_account.models.stock_valuation_layer import StockValuationLayer as _SVL  # noqa: F401
    _SVL_AVAILABLE = True
except Exception:
    _SVL_AVAILABLE = False

if _SVL_AVAILABLE:

    class StockValuationLayer(models.Model):
        _inherit = "stock.valuation.layer"

        lot_id = fields.Many2one(
            "stock.lot",
            string="Lot/Serial",
            readonly=True,
            help="Lot/serial number associated with this valuation layer. "
            "Populated from the originating stock move's move lines so that "
            "FIFO valuation can be analysed per lot.",
        )

        @api.model_create_multi
        def create(self, vals_list):
            for vals in vals_list:
                if not vals.get("lot_id") and vals.get("stock_move_id"):
                    move = self.env["stock.move"].browse(vals["stock_move_id"])
                    move_lines = move.move_line_ids.filtered(lambda ml: ml.lot_id)
                    if len(move_lines) == 1:
                        vals["lot_id"] = move_lines.lot_id.id
            return super().create(vals_list)

        def _get_fifo_layers_for_lot(self, product_id, lot_id, company_id=None):
            """Return FIFO valuation layers for a given product + lot."""
            domain = [
                ("product_id", "=", product_id),
                ("remaining_qty", ">", 0),
            ]
            if lot_id:
                domain.append(("lot_id", "=", lot_id))
            if company_id:
                domain.append(("company_id", "=", company_id))
            return self.search(domain, order="create_date, id")
