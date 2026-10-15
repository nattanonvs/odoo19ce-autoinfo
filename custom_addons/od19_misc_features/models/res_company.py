# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_logo_iso = fields.Binary(
        string="ISO Logo (โลโก้ ISO)",
        help="ISO certification logo to be displayed on reports and documents.",
        attachment=True,
    )
