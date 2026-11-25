# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_logo_iso = fields.Binary(
        string="ISO Logo (โลโก้ ISO)",
        help="ISO certification logo to be displayed on reports and documents.",
        attachment=True,
    )
    od19_email_sales = fields.Char(
        string="Document E-mail: Sales (อีเมลเอกสารฝ่ายขาย)",
        default="sales@auto-info.co.th",
        help="E-mail address printed on documents coming from sales (e.g. quotations, sales orders).",
    )
    od19_email_accounts = fields.Char(
        string="Document E-mail: Accounting (อีเมลเอกสารฝ่ายบัญชี)",
        default="accounts@auto-info.co.th",
        help="E-mail address printed on documents coming from purchase, inventory and accounting.",
    )

    @api.model
    def _od19_ensure_document_emails(self):
        """Fill the document e-mail fields for existing companies (idempotent).

        Only empty values are set, so user changes are never overwritten.
        """
        for company in self.search([]):
            vals = {}
            if not company.od19_email_sales:
                vals["od19_email_sales"] = "sales@auto-info.co.th"
            if not company.od19_email_accounts:
                vals["od19_email_accounts"] = "accounts@auto-info.co.th"
            if vals:
                company.write(vals)
