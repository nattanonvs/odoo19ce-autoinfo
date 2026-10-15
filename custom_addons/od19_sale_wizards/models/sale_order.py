# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Sale.order extension: change delivery date wizard button and downpayment
invoice linking.

Also extends ``sale.advance.payment.inv`` (sale downpayment wizard) and
``purchase.order`` so that downpayment invoices carry the originating SO/PO
name in the ``od19_downpayment_origin`` fields.
"""
from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_open_change_delivery_date(self):
        """Open the Change Delivery Date wizard for the current sale order."""
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            raise UserError(_(
                "You can only change the delivery date on quotations "
                "(draft or sent state)."
            ))
        return {
            "type": "ir.actions.act_window",
            "name": _("Change Delivery Date / เปลี่ยนวันที่จัดส่ง"),
            "res_model": "od19.sale.change.delivery.date",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_id": self.id,
                "active_id": self.id,
                "active_ids": self.ids,
                "active_model": "sale.order",
            },
        }


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_down_payment_invoice_values(self, order, so_lines):
        """Stamp the originating SO name onto the downpayment invoice."""
        res = super()._prepare_down_payment_invoice_values(order, so_lines)
        res.update({
            "od19_downpayment_origin": order.name,
            "od19_downpayment_source": "sale",
        })
        return res


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_invoice(self):
        """Stamp the originating PO name onto downpayment invoices."""
        res = super()._prepare_invoice()
        if any(line.is_downpayment for line in self.order_line):
            res.update({
                "od19_downpayment_origin": self.name,
                "od19_downpayment_source": "purchase",
                "od19_source_po_name": self.name,
            })
        return res
