# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_enforce_86_4_validation = fields.Boolean(
        related="company_id.od19_enforce_86_4_validation",
        readonly=False,
        string="ตรวจสอบรายการใบกำกับภาษีเต็มรูป (ม.86/4)",
    )
    od19_ewht_enabled = fields.Boolean(
        related="company_id.od19_ewht_enabled",
        readonly=False,
        string="e-Withholding Tax (e-WHT)",
    )
    od19_ewht_mode = fields.Selection(
        related="company_id.od19_ewht_mode",
        readonly=False,
        string="e-WHT Submission Channel",
    )
    od19_ewht_endpoint = fields.Char(
        related="company_id.od19_ewht_endpoint",
        readonly=False,
        string="e-WHT Bank Endpoint",
    )
    od19_ewht_provider_id = fields.Char(
        related="company_id.od19_ewht_provider_id",
        readonly=False,
        string="e-WHT Service Provider ID",
    )
