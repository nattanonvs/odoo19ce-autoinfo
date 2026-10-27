# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_enforce_86_4_validation = fields.Boolean(
        related="company_id.od19_enforce_86_4_validation",
        readonly=False,
        string="ตรวจสอบรายการใบกำกับภาษีเต็มรูป (ม.86/4)",
    )
