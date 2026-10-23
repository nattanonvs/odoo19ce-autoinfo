# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class Od19DocumentPullWizardLine(models.TransientModel):
    _name = "od19.document.pull.wizard.line"
    _description = "OD19 Document Pull Wizard Line"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.wizard",
        string="Wizard / วิซาร์ด",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(
        string="Select / เลือก",
        default=True,
    )
    res_model = fields.Char(
        string="Source Model / โมเดลต้นทาง",
        readonly=True,
    )
    res_id = fields.Integer(
        string="Source Line ID / รหัสบรรทัดต้นทาง",
        readonly=True,
    )
    source_name = fields.Char(
        string="Source / เอกสารต้นทาง",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product / สินค้า",
        readonly=True,
    )
    name = fields.Char(
        string="Description / รายละเอียด",
        readonly=True,
    )
    qty_to_pull = fields.Float(
        string="Billable Qty / จำนวนที่วางบิลได้",
        digits="Product Unit of Measure",
        readonly=True,
    )
    price_unit = fields.Float(
        string="Unit Price / ราคาต่อหน่วย",
        digits="Product Price",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM / หน่วย",
        readonly=True,
    )

    def _od19_get_source_line(self):
        """Return the source line record this row refers to."""
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)
