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

    od19_require_vendor_bill_for_payment = fields.Boolean(
        string="บังคับตั้งหนี้ก่อนจ่าย (AP)",
        default=True,
        help="When enabled, an outbound (vendor) payment cannot be posted unless "
        "it is generated from a Vendor Bill (ตั้งหนี้). Standalone vendor "
        "payments that are not linked to any bill are blocked.",
    )
