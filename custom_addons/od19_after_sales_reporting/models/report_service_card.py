from odoo import fields, models, tools


class ReportAfterSalesServiceCard(models.Model):
    _name = "od19.report.after.sales.service.card"
    _description = "After-Sales Service Card KPI"
    _auto = False

    service_type = fields.Selection(
        selection=[
            ("preventive", "Preventive Maintenance"),
            ("corrective", "Corrective Repair"),
            ("inspection", "Inspection"),
            ("installation", "Installation"),
            ("other", "Other"),
        ],
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        readonly=True,
    )
    team_id = fields.Many2one("hr.department", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    card_count = fields.Integer(readonly=True)
    sla_breach_count = fields.Integer(readonly=True)
    due_count = fields.Integer(readonly=True)
    overdue_count = fields.Integer(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["od19.service.card"].flush_model(
            [
                "service_type",
                "state",
                "team_id",
                "company_id",
                "is_sla_breached",
                "next_service_date",
                "active",
            ]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(card.id) AS id,
                    card.service_type AS service_type,
                    card.state AS state,
                    card.team_id AS team_id,
                    card.company_id AS company_id,
                    COUNT(*) AS card_count,
                    COUNT(*) FILTER (
                        WHERE COALESCE(card.is_sla_breached, FALSE)
                    ) AS sla_breach_count,
                    COUNT(*) FILTER (
                        WHERE card.next_service_date IS NOT NULL
                            AND card.next_service_date <= CURRENT_DATE
                            AND card.state NOT IN ('done', 'cancelled')
                    ) AS due_count,
                    COUNT(*) FILTER (
                        WHERE card.next_service_date IS NOT NULL
                            AND card.next_service_date < CURRENT_DATE
                            AND card.state NOT IN ('done', 'cancelled')
                    ) AS overdue_count
                FROM od19_service_card card
                WHERE COALESCE(card.active, TRUE)
                GROUP BY
                    card.service_type,
                    card.state,
                    card.team_id,
                    card.company_id
            )
            """
        )
