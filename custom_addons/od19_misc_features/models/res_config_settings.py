# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_logo_iso = fields.Binary(
        related="company_id.od19_logo_iso",
        readonly=False,
        string="ISO Logo (โลโก้ ISO)",
    )
    od19_email_sales = fields.Char(
        related="company_id.od19_email_sales",
        readonly=False,
        string="Document E-mail: Sales (อีเมลเอกสารฝ่ายขาย)",
    )
    od19_email_accounts = fields.Char(
        related="company_id.od19_email_accounts",
        readonly=False,
        string="Document E-mail: Accounting (อีเมลเอกสารฝ่ายบัญชี)",
    )
