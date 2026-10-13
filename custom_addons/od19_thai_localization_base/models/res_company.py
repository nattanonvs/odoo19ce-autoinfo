# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Add Sarabun font option and set as default
    font = fields.Selection(
        selection_add=[("Sarabun", "Sarabun")],
        default="Sarabun",
    )

    # Thai Buddhist Era (BE) year flag for reports
    l10n_th_buddhist_year = fields.Boolean(
        string="Use Buddhist Year (พ.ศ.)",
        default=True,
        help="If enabled, dates in Thai reports will use the Buddhist Era year "
        "(e.g., 2568 instead of 2025).",
    )
