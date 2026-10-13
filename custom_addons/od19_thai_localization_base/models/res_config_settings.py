# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_th_buddhist_year = fields.Boolean(
        related="company_id.l10n_th_buddhist_year",
        readonly=False,
        string="Use Buddhist Year (พ.ศ.)",
    )
