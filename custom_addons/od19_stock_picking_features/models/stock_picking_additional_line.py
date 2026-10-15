# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockPickingAdditionalLine(models.Model):
    _name = "od19.stock.picking.additional.line"
    _description = "Additional Print Line for Stock Picking"
    _order = "sequence, id"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfer / ใบโอนสินค้า",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(
        string="Description / คำอธิบาย",
        required=True,
    )
    quantity = fields.Float(
        string="Quantity / จำนวน",
        default=1.0,
        digits="Product Unit of Measure",
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure / หน่วยนับ",
    )
    sequence = fields.Integer(
        string="Sequence / ลำดับ",
        default=10,
        help="Determines the display order of the additional lines.",
    )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def _get_display_qty_uom(self):
        """Return a human-readable ``quantity UoM`` string for reports."""
        self.ensure_one()
        parts = [str(self.quantity)]
        if self.product_uom_id:
            parts.append(self.product_uom_id.name)
        return " ".join(parts)
