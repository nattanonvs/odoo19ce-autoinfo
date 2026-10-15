# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, company, origin):
        """Propagate vendor_ref and your_ref from PR to PO.

        The origin parameter is the PR origin string. We look up the
        purchase request from the first item to read the vendor/your
        reference fields.
        """
        data = super()._prepare_purchase_order(picking_type, company, origin)
        request = self.item_ids.mapped("request_id")[:1]
        if request:
            if request.od19_vendor_ref:
                data["partner_ref"] = request.od19_vendor_ref
            if request.od19_your_ref:
                data["od19_your_ref"] = request.od19_your_ref
        return data

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        """Propagate price_unit, discount and taxes_id from PR line to PO line."""
        vals = super()._prepare_purchase_order_line(po, item)
        line = item.line_id
        if line.od19_price_unit:
            vals["price_unit"] = line.od19_price_unit
        if line.od19_discount:
            vals["discount"] = line.od19_discount
        if line.od19_taxes_id:
            vals["taxes_id"] = [(6, 0, line.od19_taxes_id.ids)]
        return vals
