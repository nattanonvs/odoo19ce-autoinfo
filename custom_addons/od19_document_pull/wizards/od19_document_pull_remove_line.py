# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class Od19DocumentPullRemoveSource(models.TransientModel):
    """Selectable row: one source document currently bound to the target."""

    _name = "od19.document.pull.remove.source"
    _description = "OD19 Document Pull Remove Source"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.remove.wizard",
        string="Wizard / วิซาร์ด",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="Select / เลือก")
    source_ref = fields.Char(
        string="Source Reference / อ้างอิงเอกสารต้นทาง", readonly=True
    )
    name = fields.Char(string="Source Document / เอกสารต้นทาง", readonly=True)

    def _od19_get_source(self):
        """Return the referenced source document record."""
        self.ensure_one()
        model_name, res_id = self.source_ref.split(",")
        return self.env[model_name].browse(int(res_id))


class Od19DocumentPullRemoveLine(models.TransientModel):
    _name = "od19.document.pull.remove.line"
    _description = "OD19 Document Pull Remove Line"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.remove.wizard",
        string="Wizard / วิซาร์ด",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Line / รายการ", readonly=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product / สินค้า",
        readonly=True,
    )
    quantity = fields.Float(
        string="Quantity / จำนวน",
        digits="Product Unit of Measure",
        readonly=True,
    )
