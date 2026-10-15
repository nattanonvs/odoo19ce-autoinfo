# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_bot_url = fields.Char(
        string="BOT URL (รายการภาษี)",
        default="https://www.rd.go.th/",
        help="Base URL of the Revenue Department (BOT) e-Tax invoice lookup. "
        "The invoice number is appended as ?id=<invoice_name>.",
    )
