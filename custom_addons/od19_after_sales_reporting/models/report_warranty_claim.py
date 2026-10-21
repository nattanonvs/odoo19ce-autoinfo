from odoo import fields, models, tools


class ReportAfterSalesWarrantyClaim(models.Model):
    _name = "od19.report.after.sales.warranty.claim"
    _description = "After-Sales Warranty Claim KPI"
    _auto = False

    claim_type = fields.Selection(
        selection=[
            ("warranty", "Warranty"),
            ("rma", "RMA (Return Merchandise)"),
            ("repair", "Repair"),
        ],
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        readonly=True,
    )
    under_warranty = fields.Boolean(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    claim_count = fields.Integer(readonly=True)
    avg_turnaround_days = fields.Float(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["od19.warranty.claim"].flush_model(
            ["claim_type", "state", "under_warranty", "company_id", "claim_date"]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(claim.id) AS id,
                    claim.claim_type AS claim_type,
                    claim.state AS state,
                    claim.under_warranty AS under_warranty,
                    claim.company_id AS company_id,
                    COUNT(*) AS claim_count,
                    COALESCE(
                        AVG(
                            CASE WHEN claim.state = 'done' THEN
                                EXTRACT(
                                    EPOCH FROM (claim.write_date - claim.create_date)
                                ) / 86400.0
                            END
                        ),
                        0.0
                    ) AS avg_turnaround_days
                FROM od19_warranty_claim claim
                GROUP BY
                    claim.claim_type,
                    claim.state,
                    claim.under_warranty,
                    claim.company_id
            )
            """
        )
