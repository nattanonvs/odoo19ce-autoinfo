# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    od19_vendor_ref = fields.Char(
        string="Vendor Reference / เลขที่อ้างอิงผู้ขาย",
        help="Reference number provided by the vendor for this purchase request.",
    )
    od19_your_ref = fields.Char(
        string="Your Reference / เลขที่อ้างอิงของคุณ",
        help="Your reference number for this purchase request.",
    )
