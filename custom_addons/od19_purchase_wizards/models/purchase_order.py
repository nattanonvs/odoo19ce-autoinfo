# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_your_ref = fields.Char(
        string="Your Reference / เลขที่อ้างอิงของคุณ",
        help="Your reference number propagated from the purchase request.",
    )

    def action_od19_trade_discount(self):
        """Open the Trade Discount wizard for the current purchase order."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                _("Trade discount can only be applied on draft purchase orders.")
            )
        return {
            "name": _("Trade Discount / ส่วนลดพิเศษ"),
            "type": "ir.actions.act_window",
            "res_model": "od19.purchase.trade.discount",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_purchase_order_id": self.id,
                "active_id": self.id,
                "active_ids": self.ids,
                "active_model": "purchase.order",
            },
        }

    def action_od19_create_vendor_bill(self):
        """Open the Create Vendor Bill wizard for the current purchase order."""
        self.ensure_one()
        if self.state not in ("purchase", "done"):
            raise UserError(
                _(
                    "Vendor bill can only be created from confirmed "
                    "purchase orders."
                )
            )
        return {
            "name": _("Create Vendor Bill / สร้างใบแจ้งหนี้ผู้ขาย"),
            "type": "ir.actions.act_window",
            "res_model": "od19.purchase.create.vendor.bill",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_purchase_order_id": self.id,
                "active_id": self.id,
                "active_ids": self.ids,
                "active_model": "purchase.order",
            },
        }
