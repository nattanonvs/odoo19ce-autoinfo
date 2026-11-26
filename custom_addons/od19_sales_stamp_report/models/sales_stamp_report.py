from odoo import fields, models, tools


class Od19SalesStampReport(models.Model):
    """Read-only SQL view over confirmed sale orders, keyed by stamp date.

    ``stamp_date`` is filled in by ``od19_sales_confirm_stamp`` when a
    quotation is confirmed, so this view only contains confirmed orders
    (``state in ('sale', 'done')``) that carry a stamp date.
    """

    _name = "od19.sales.stamp.report"
    _description = "Sales Stamp Date Analysis"
    _auto = False
    _order = "stamp_date desc, id desc"

    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    stamp_date = fields.Date(string="Stamp Date", readonly=True)
    department_id = fields.Many2one(
        "hr.department", string="Department", readonly=True
    )
    sale_mode = fields.Selection(
        [("one_time", "One-time"), ("contract", "Contract-based")],
        string="Sale Mode",
        readonly=True,
    )
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    project_owner_id = fields.Many2one(
        "res.partner", string="Project Owner", readonly=True
    )
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    user_id = fields.Many2one("res.users", string="Salesperson", readonly=True)
    team_id = fields.Many2one("crm.team", string="Sales Team", readonly=True)
    confirmed_by_id = fields.Many2one(
        "res.users", string="Confirmed By", readonly=True
    )
    order_count = fields.Integer(string="Orders", readonly=True)
    amount_untaxed = fields.Float(string="Untaxed Amount", readonly=True)
    amount_total = fields.Float(string="Total Amount", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(so.id) AS id,
                    so.company_id AS company_id,
                    so.currency_id AS currency_id,
                    so.stamp_date AS stamp_date,
                    so.department_id AS department_id,
                    so.od19_sale_mode AS sale_mode,
                    so.od19_project_id AS project_id,
                    so.od19_project_owner_id AS project_owner_id,
                    so.partner_id AS partner_id,
                    so.user_id AS user_id,
                    so.team_id AS team_id,
                    so.confirmed_by_id AS confirmed_by_id,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(so.amount_untaxed), 0.0) AS amount_untaxed,
                    COALESCE(SUM(so.amount_total), 0.0) AS amount_total
                FROM sale_order so
                WHERE so.state IN ('sale', 'done')
                  AND so.stamp_date IS NOT NULL
                GROUP BY
                    so.company_id, so.currency_id, so.stamp_date,
                    so.department_id, so.od19_sale_mode, so.od19_project_id,
                    so.od19_project_owner_id, so.partner_id,
                    so.user_id, so.team_id,
                    so.confirmed_by_id
            )
            """
        )
