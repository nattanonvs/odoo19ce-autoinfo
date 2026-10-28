# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models
from odoo.exceptions import UserError


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
    od19_etax_rd_mode = fields.Selection(
        [("mock", "Mock (ทดสอบ)"), ("live", "Live (RD)")],
        string="RD Submission Channel",
        default="mock",
        required=True,
        help="Mock answers locally and is the default until the RD API contract "
        "is published. Live sends the documents to the Revenue Department "
        "sandbox or production endpoint.",
    )
    od19_etax_rd_endpoint = fields.Char(
        string="RD Submission Endpoint",
        help="Base URL of the Revenue Department e-Tax submission service.",
    )
    od19_etax_rd_provider_id = fields.Char(
        string="RD Service Provider ID",
        help="Identifier issued by the RD to the e-Tax service provider of this "
        "company.",
    )

    def _od19_etax_check_enabled(self):
        """Raise when this company has not enabled the e-Tax Invoice feature.

        ``od19_etax_enabled`` is the single switch of the module: it guards the
        creation of e-Tax documents, every step of their lifecycle and the RD
        submission, so nothing can be operated for a company that never opted
        in.
        """
        self.ensure_one()
        if not self.od19_etax_enabled:
            raise UserError(
                self.env._(
                    "e-Tax Invoice is not enabled for company %s. Enable it in "
                    "the company settings before issuing e-Tax documents.",
                    self.display_name,
                )
            )
