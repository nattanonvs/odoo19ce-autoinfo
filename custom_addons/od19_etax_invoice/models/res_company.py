# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_etax_enabled = fields.Boolean(
        string="e-Tax Invoice (RD)",
        help="Issue Thai e-Tax Invoice & e-Receipt (ขมธอ.3-2560) for customer "
        "invoices of this company.",
    )
    od19_etax_certificate_id = fields.Many2one(
        "od19.etax.certificate",
        string="e-Tax Signing Certificate",
        domain="[('company_id', '=', id)]",
        help="Default certificate used to sign the e-Tax documents of this "
        "company.",
    )
