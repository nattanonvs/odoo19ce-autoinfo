# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _od19_apply_scanned_quantity(self, quantity, lot_id=False):
        """Mark a scanned quantity (and optional lot) as picked on this line.

        Kept as a small helper so both the scanner service and future
        integrations reuse the same write semantics.
        """
        for line in self:
            vals = {"picked": True, "quantity": float(quantity)}
            if lot_id:
                vals["lot_id"] = lot_id
            line.write(vals)
