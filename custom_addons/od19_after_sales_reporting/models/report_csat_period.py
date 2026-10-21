from odoo import fields, models, tools


class ReportAfterSalesCsatPeriod(models.Model):
    _name = "od19.report.after.sales.csat.period"
    _description = "After-Sales Customer Satisfaction KPI"
    _auto = False

    period = fields.Char(readonly=True)
    survey_count = fields.Integer(readonly=True)
    completed_count = fields.Integer(readonly=True)
    avg_score = fields.Float(readonly=True)
    avg_csat = fields.Float(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["od19.iso.customer.satisfaction"].flush_model(
            ["period", "status", "overall_score", "overall_csat"]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(survey.id) AS id,
                    COALESCE(survey.period, 'Unassigned') AS period,
                    COUNT(*) AS survey_count,
                    COUNT(*) FILTER (
                        WHERE survey.status = 'completed'
                    ) AS completed_count,
                    COALESCE(AVG(survey.overall_score), 0.0) AS avg_score,
                    COALESCE(
                        AVG(NULLIF(survey.overall_csat, '')::integer),
                        0.0
                    ) AS avg_csat
                FROM od19_iso_customer_satisfaction survey
                GROUP BY COALESCE(survey.period, 'Unassigned')
            )
            """
        )
