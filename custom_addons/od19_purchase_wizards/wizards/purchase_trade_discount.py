# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Od19PurchaseTradeDiscount(models.TransientModel):
    _name = "od19.purchase.trade.discount"
    _description = "OD19 Purchase Trade Discount Wizard"

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order / ใบสั่งซื้อ",
        required=True,
        readonly=True,
    )
    discount_type = fields.Selection(
        selection=[
            ("percent", "Percent / เปอร์เซ็นต์"),
            ("fixed", "Fixed Amount / จำนวนเงิน"),
        ],
        string="Discount Type / ประเภทส่วนลด",
        default="percent",
        required=True,
    )
    discount_value = fields.Float(
        string="Discount Value / มูลค่าส่วนลด",
        required=True,
        default=0.0,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_model == "purchase.order" and active_id:
            res["purchase_order_id"] = active_id
        return res

    def action_apply_discount(self):
        """Apply the trade discount to all lines of the purchase order."""
        self.ensure_one()
        po = self.purchase_order_id
        if not po or po.state != "draft":
            raise UserError(
                _("Trade discount can only be applied on draft purchase orders.")
            )

        lines = po.order_line.filtered(
            lambda l: l.display_type
            not in ("line_section", "line_subsection", "line_note")
        )
        if not lines:
            raise UserError(
                _("There are no product lines to apply the discount to.")
            )

        if self.discount_type == "percent":
            if self.discount_value < 0 or self.discount_value > 100:
                raise UserError(
                    _("Percent discount must be between 0 and 100.")
                )
            factor = 1 - self.discount_value / 100.0
            for line in lines:
                current = line.discount or 0.0
                new_discount = (1 - (1 - current / 100.0) * factor) * 100.0
                line.discount = new_discount
        else:
            # Fixed amount: distribute proportionally by line subtotal.
            if self.discount_value <= 0:
                raise UserError(
                    _("Fixed discount value must be greater than zero.")
                )
            subtotal_map = {}
            total_subtotal = 0.0
            for line in lines:
                price_subtotal = (
                    line.price_unit
                    * line.product_qty
                    * (1 - (line.discount or 0.0) / 100.0)
                )
                subtotal_map[line] = price_subtotal
                total_subtotal += price_subtotal

            if total_subtotal <= 0:
                raise UserError(
                    _(
                        "Cannot distribute a fixed discount when the total "
                        "subtotal is zero."
                    )
                )

            for line in lines:
                share = self.discount_value * (
                    subtotal_map[line] / total_subtotal
                )
                base = line.price_unit * line.product_qty
                if base <= 0:
                    continue
                current = line.discount or 0.0
                additional_discount = (share / base) * 100.0
                line.discount = current + additional_discount

        return {"type": "ir.actions.act_window_close"}
