# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_logo_iso = fields.Binary(
        related="company_id.od19_logo_iso",
        readonly=False,
        string="ISO Logo (โลโก้ ISO)",
    )
