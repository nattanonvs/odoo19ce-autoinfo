from odoo import fields, models, tools


class ReportSalesRepeatBusiness(models.Model):
    _name = "od19.sales.repeat.business.report"
    _description = "Sales Repeat Business Report"
    _auto = False

    company_id = fields.Many2one("res.company", readonly=True)
    commercial_customer_id = fields.Many2one("res.partner", readonly=True)
    project_owner_id = fields.Many2one("res.partner", readonly=True)
    project_count = fields.Integer(readonly=True)
    sale_order_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(so.id) AS id,
                    so.company_id AS company_id,
                    so.partner_id AS commercial_customer_id,
                    so.od19_project_owner_id AS project_owner_id,
                    COUNT(DISTINCT so.od19_project_id) AS project_count,
                    COUNT(*) AS sale_order_count
                FROM sale_order so
                WHERE so.od19_project_id IS NOT NULL
                GROUP BY so.company_id, so.partner_id, so.od19_project_owner_id
            )
            """
        )
