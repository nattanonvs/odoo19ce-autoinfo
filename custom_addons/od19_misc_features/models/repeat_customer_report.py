# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Enhanced repeat customer report SQL view.

Since ``od19_sales_reporting`` (which owns ``od19.sales.repeat.business.report``)
is not a hard dependency of this module, we ship our own SQL view
``od19_repeat_customer_enhanced`` that extends the reporting data with:

* ``actual_partner_id``  -> ``partner_shipping_id`` when set, else ``partner_id``
* ``last_order_date``     -> most recent ``date_order`` for that partner

The view aggregates confirmed sale orders so that 30-day and 90-day recency
filters can be applied in the tree view.
"""

from odoo import fields, models, tools


class Od19RepeatCustomerEnhanced(models.Model):
    _name = "od19.repeat.customer.enhanced"
    _description = "OD19 Repeat Customer Enhanced Report"
    _auto = False

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        readonly=True,
    )
    actual_partner_id = fields.Many2one(
        "res.partner",
        string="Actual Partner (Thai: คู่ค้าที่ใช้จริง)",
        readonly=True,
    )
    last_order_date = fields.Datetime(
        string="Last Order Date",
        readonly=True,
    )
    order_count = fields.Integer(
        string="Order Count",
        readonly=True,
    )
    total_amount = fields.Float(
        string="Total Amount",
        readonly=True,
        digits=(16, 2),
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    so.partner_id AS partner_id,
                    COALESCE(so.partner_shipping_id, so.partner_id) AS actual_partner_id,
                    MAX(so.date_order) AS last_order_date,
                    COUNT(so.id) AS order_count,
                    SUM(so.amount_total) AS total_amount
                FROM sale_order so
                WHERE so.state IN ('sale', 'done')
                GROUP BY
                    so.partner_id,
                    COALESCE(so.partner_shipping_id, so.partner_id)
            )
            """
        )
