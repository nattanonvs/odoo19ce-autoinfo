# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class Od19DocumentPullSource(models.TransientModel):
    """One selectable source document offered on the pull wizard.

    The rows are computed server-side from the destination document's source
    specifications, so only documents that match the partner/state and still
    have lines left to pull are ever shown.
    """

    _name = "od19.document.pull.source"
    _description = "OD19 Document Pull Source"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="od19.document.pull.wizard",
        string="Wizard / วิซาร์ด",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    selected = fields.Boolean(string="Select / เลือก")
    source_model = fields.Char(
        string="Source Model / โมเดลต้นทาง", readonly=True
    )
    source_id = fields.Integer(
        string="Source Document ID / รหัสเอกสารต้นทาง", readonly=True
    )
    source_type = fields.Char(
        string="Document Type / ประเภทเอกสาร", readonly=True
    )
    name = fields.Char(string="Source Document / เอกสารต้นทาง", readonly=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Partner / คู่ค้า", readonly=True
    )
    remaining = fields.Integer(
        string="Remaining Lines / รายการที่ดึงได้", readonly=True
    )

    def _od19_get_source(self):
        """Return the actual source document record."""
        self.ensure_one()
        return self.env[self.source_model].browse(self.source_id)
