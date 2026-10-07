from odoo import fields, models, tools


class ReportInventoryAccuracy(models.Model):
    _name = "od19.report.inventory.accuracy"
    _description = "OD19 Inventory Accuracy"
    _auto = False

    session_id = fields.Many2one("od19.stock.count.session", readonly=True)
    location_id = fields.Many2one("stock.location", readonly=True)
    state = fields.Selection(
        selection=[
            ("scheduled", "Scheduled"),
            ("counted", "Counted"),
            ("variance", "Variance"),
            ("adjusted", "Adjusted"),
            ("reviewed", "Reviewed"),
        ],
        readonly=True,
    )
    line_count = fields.Integer(readonly=True)
    variance_line_count = fields.Integer(readonly=True)
    total_variance_qty = fields.Float(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["od19.stock.count.session"].flush_model(["location_id", "state"])
        self.env["od19.stock.count.line"].flush_model(
            ["session_id", "system_qty", "counted_qty"]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    session.id AS id,
                    session.id AS session_id,
                    session.location_id AS location_id,
                    session.state AS state,
                    COUNT(line.id) AS line_count,
                    COUNT(*) FILTER (
                        WHERE COALESCE(line.counted_qty - line.system_qty, 0.0) != 0.0
                    ) AS variance_line_count,
                    COALESCE(SUM(line.counted_qty - line.system_qty), 0.0) AS total_variance_qty
                FROM od19_stock_count_session session
                LEFT JOIN od19_stock_count_line line
                    ON line.session_id = session.id
                GROUP BY session.id, session.location_id, session.state
            )
            """
        )
