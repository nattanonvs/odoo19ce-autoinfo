from odoo import api, fields, models, tools


class ReportAfterSalesQcInspection(models.Model):
    _name = "od19.report.after.sales.qc.inspection"
    _description = "After-Sales QC Inspection KPI"
    _auto = False

    inspection_type = fields.Selection(
        selection=[
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
            ("in_process", "In-Process"),
        ],
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        readonly=True,
    )
    result = fields.Selection(
        selection=[
            ("pass", "Pass"),
            ("fail", "Fail"),
        ],
        readonly=True,
    )
    company_id = fields.Many2one("res.company", readonly=True)
    inspection_count = fields.Integer(readonly=True)
    pass_count = fields.Integer(readonly=True)
    fail_count = fields.Integer(readonly=True)
    nc_count = fields.Integer(readonly=True)
    tested_qty = fields.Float(readonly=True)
    accepted_qty = fields.Float(readonly=True)
    rejected_qty = fields.Float(readonly=True)
    pass_rate = fields.Float(compute="_compute_pass_rate", digits=(5, 2))

    @api.depends("pass_count", "inspection_count")
    def _compute_pass_rate(self):
        for record in self:
            record.pass_rate = (
                record.pass_count / record.inspection_count * 100.0
                if record.inspection_count
                else 0.0
            )

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["od19.qc.inspection"].flush_model(
            [
                "inspection_type",
                "state",
                "result",
                "company_id",
                "qty_tested",
                "qty_accepted",
                "qty_rejected",
                "nc_id",
            ]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(inspection.id) AS id,
                    inspection.inspection_type AS inspection_type,
                    inspection.state AS state,
                    inspection.result AS result,
                    inspection.company_id AS company_id,
                    COUNT(*) AS inspection_count,
                    COUNT(*) FILTER (
                        WHERE inspection.result = 'pass'
                    ) AS pass_count,
                    COUNT(*) FILTER (
                        WHERE inspection.result = 'fail'
                    ) AS fail_count,
                    COUNT(*) FILTER (
                        WHERE inspection.nc_id IS NOT NULL
                    ) AS nc_count,
                    COALESCE(SUM(inspection.qty_tested), 0.0) AS tested_qty,
                    COALESCE(SUM(inspection.qty_accepted), 0.0) AS accepted_qty,
                    COALESCE(SUM(inspection.qty_rejected), 0.0) AS rejected_qty
                FROM od19_qc_inspection inspection
                GROUP BY
                    inspection.inspection_type,
                    inspection.state,
                    inspection.result,
                    inspection.company_id
            )
            """
        )
