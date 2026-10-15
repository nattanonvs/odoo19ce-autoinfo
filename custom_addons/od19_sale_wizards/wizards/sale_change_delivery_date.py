# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Change Delivery Date wizard for sale orders.

Updates the commitment date of the sale order, which in turn recomputes the
scheduled date of every order line.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Od19SaleChangeDeliveryDate(models.TransientModel):
    _name = "od19.sale.change.delivery.date"
    _description = "Change Delivery Date / เปลี่ยนวันที่จัดส่ง"

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order / ใบสั่งขาย",
        required=True,
        readonly=True,
    )
    new_delivery_date = fields.Date(
        string="New Delivery Date / วันที่จัดส่งใหม่",
        required=True,
        help="The new commitment/delivery date applied to all order lines.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_model == "sale.order" and active_id:
            res["sale_order_id"] = active_id
            order = self.env["sale.order"].browse(active_id)
            if order.commitment_date:
                res["new_delivery_date"] = order.commitment_date.date()
        return res

    def action_apply(self):
        """Apply the new delivery date to the sale order and its lines."""
        self.ensure_one()
        order = self.sale_order_id
        if not order:
            raise UserError(_("No sale order selected."))
        if order.state not in ("draft", "sent"):
            raise UserError(_(
                "You can only change the delivery date on quotations "
                "(draft or sent state)."
            ))

        # commitment_date is a Datetime; convert the chosen Date to midnight
        # in the company's (or user's) timezone.
        new_datetime = fields.Datetime.to_datetime(self.new_delivery_date)

        order.write({"commitment_date": new_datetime})

        # Recompute every line's scheduled_date (and related forecast fields).
        # scheduled_date is a computed field (from sale_stock) depending on
        # order_id.commitment_date, so the write above triggers recompute.
        # We explicitly invalidate + recompute to be safe when sale_stock
        # is installed.
        lines = order.order_line
        if "scheduled_date" in lines._fields:
            lines.invalidate_model(["scheduled_date"])
        if hasattr(lines, "_compute_qty_at_date"):
            lines._compute_qty_at_date()

        return {"type": "ir.actions.act_window_close"}
