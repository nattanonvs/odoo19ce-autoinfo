# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_bot_url = fields.Char(
        related="company_id.od19_bot_url",
        readonly=False,
        string="BOT URL (รายการภาษี)",
        help="Base URL of the Revenue Department (BOT) e-Tax invoice lookup. "
        "The invoice number is appended as ?id=<invoice_name>.",
    )
