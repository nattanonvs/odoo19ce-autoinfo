from odoo import fields, models, tools


class ReportSalesProjectRevenue(models.Model):
    _name = "od19.sales.project.revenue.report"
    _description = "Sales Project Revenue Report"
    _auto = False

    project_id = fields.Many2one("od19.sales.project", readonly=True)
    commercial_customer_id = fields.Many2one("res.partner", readonly=True)
    project_owner_id = fields.Many2one("res.partner", readonly=True)
    order_count = fields.Integer(readonly=True)
    amount_untaxed = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(so.id) AS id,
                    so.od19_project_id AS project_id,
                    so.partner_id AS commercial_customer_id,
                    so.od19_project_owner_id AS project_owner_id,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(so.amount_untaxed), 0.0) AS amount_untaxed
                FROM sale_order so
                WHERE so.od19_project_id IS NOT NULL
                GROUP BY so.od19_project_id, so.partner_id, so.od19_project_owner_id
            )
            """
        )
