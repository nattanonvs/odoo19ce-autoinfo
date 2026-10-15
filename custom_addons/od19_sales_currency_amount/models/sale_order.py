from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    amount_untaxed_curr = fields.Monetary(
        string="Untaxed Amount (Company Currency)",
        compute="_compute_amount_company",
        currency_field="company_currency_id",
        store=True,
        help="Untaxed amount converted to the company currency with the order exchange rate.",
    )

    @api.depends(
        "amount_untaxed",
        "amount_total",
        "currency_rate",
        "currency_id",
        "company_id",
    )
    def _compute_amount_company(self):
        """Amounts in the company currency.

        Odoo 19 defines ``sale.order.currency_rate`` as
        ``res.currency._get_conversion_rate(company_currency -> order_currency)``
        (see ``_compute_currency_rate`` and the credit-limit check that divides by
        it). To go from the order currency back to the company currency we must
        therefore divide by ``currency_rate``, not multiply as OCA
        ``sale_company_currency`` currently does.
        """
        for order in self:
            order.amount_untaxed_curr = order._od19_to_company_currency(
                order.amount_untaxed
            )
            order.amount_total_curr = order._od19_to_company_currency(
                order.amount_total
            )

    def _od19_to_company_currency(self, amount):
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if not self.currency_id or self.currency_id == company_currency:
            return amount
        if self.currency_rate:
            return company_currency.round(amount / self.currency_rate)
        return self.currency_id._convert(
            amount,
            company_currency,
            self.company_id,
            (self.date_order or fields.Datetime.now()).date(),
        )
