from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange("product_id", "partner_id")
    def _onchange_od19_fill_price_from_vendor(self):
        """Auto-fill the unit price from the vendor's product supplier info.

        When both the product and the vendor (partner) are set, look up the
        matching ``product.supplierinfo`` record for that vendor on the
        product and use its price as the line's unit price. The price is
        converted from the seller's unit of measure and currency into the
        line's UoM and the purchase order's currency.

        ``technical_price_unit`` is kept in sync with ``price_unit`` so that
        Odoo's standard price computation continues to treat the value as
        vendor-sourced (and will recompute it when the quantity, date, or
        seller changes) rather than as a manually overridden price.
        """
        for line in self:
            if not line.product_id or not line.partner_id or line.display_type:
                continue

            sellers = line.product_id.seller_ids.filtered(
                lambda s: s.partner_id == line.partner_id
                and (not s.product_id or s.product_id == line.product_id)
            )
            if not sellers:
                continue

            seller = sellers[0]
            price_unit = seller.price

            # Convert from the seller's UoM to the line's UoM.
            seller_uom = seller.product_uom_id or line.product_id.uom_id
            line_uom = line.product_uom_id or line.product_id.uom_id
            if seller_uom and line_uom and seller_uom != line_uom:
                price_unit = seller_uom._compute_price(price_unit, line_uom)

            # Convert from the seller's currency to the order's currency.
            if (
                seller.currency_id
                and line.currency_id
                and seller.currency_id != line.currency_id
            ):
                price_unit = seller.currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order or fields.Date.context_today(line),
                    False,
                )

            line.price_unit = price_unit
            line.technical_price_unit = price_unit
