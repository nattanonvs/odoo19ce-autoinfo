from odoo import fields, models, tools


class ReportAfterSalesTicket(models.Model):
    _name = "od19.report.after.sales.ticket"
    _description = "After-Sales Ticket KPI"
    _auto = False

    team_id = fields.Many2one("helpdesk.ticket.team", readonly=True)
    team_type = fields.Selection(
        selection=[
            ("internal", "Internal"),
            ("customer_service", "Customer Service"),
        ],
        readonly=True,
    )
    service_type = fields.Selection(
        selection=[
            ("repair", "Repair"),
            ("installation", "Installation"),
            ("maintenance", "Maintenance"),
            ("warranty", "Warranty"),
            ("inspection", "Inspection"),
            ("other", "Other"),
        ],
        readonly=True,
    )
    stage_id = fields.Many2one("helpdesk.ticket.stage", readonly=True)
    closed = fields.Boolean(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    ticket_count = fields.Integer(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["helpdesk.ticket"].flush_model(
            [
                "team_id",
                "team_type",
                "service_type",
                "stage_id",
                "closed",
                "company_id",
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
                    MIN(ticket.id) AS id,
                    ticket.team_id AS team_id,
                    ticket.team_type AS team_type,
                    ticket.service_type AS service_type,
                    ticket.stage_id AS stage_id,
                    COALESCE(stage.closed, FALSE) AS closed,
                    ticket.company_id AS company_id,
                    COUNT(*) AS ticket_count
                FROM helpdesk_ticket ticket
                LEFT JOIN helpdesk_ticket_stage stage ON stage.id = ticket.stage_id
                WHERE COALESCE(ticket.active, TRUE)
                GROUP BY
                    ticket.team_id,
                    ticket.team_type,
                    ticket.service_type,
                    ticket.stage_id,
                    stage.closed,
                    ticket.company_id
            )
            """
        )
