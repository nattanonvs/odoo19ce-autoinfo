from odoo import fields, models, tools


class ReportInventoryMovementBacklog(models.Model):
    _name = "od19.report.inventory.movement.backlog"
    _description = "OD19 Inventory Movement Backlog"
    _auto = False

    picking_id = fields.Many2one("stock.picking", readonly=True)
    flow_class = fields.Selection(
        selection=[
            ("receipt", "Receipt"),
            ("delivery", "Delivery"),
            ("transfer", "Transfer"),
            ("return", "Return"),
        ],
        readonly=True,
    )
    execution_state = fields.Selection(
        selection=[
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("done", "Done"),
            ("exception", "Exception"),
        ],
        readonly=True,
    )
    reference_document = fields.Char(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["stock.picking"].flush_model(
            ["state", "origin", "return_id", "picking_type_id"]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    sp.id AS id,
                    sp.id AS picking_id,
                    CASE
                        WHEN sp.return_id IS NOT NULL THEN 'return'
                        WHEN spt.code = 'incoming' THEN 'receipt'
                        WHEN spt.code = 'outgoing' THEN 'delivery'
                        WHEN spt.code = 'internal' THEN 'transfer'
                        ELSE NULL
                    END AS flow_class,
                    CASE
                        WHEN sp.state = 'assigned' THEN 'ready'
                        WHEN sp.state = 'done' THEN 'done'
                        WHEN sp.state = 'cancel' THEN 'exception'
                        ELSE 'waiting'
                    END AS execution_state,
                    sp.origin AS reference_document
                FROM stock_picking sp
                JOIN stock_picking_type spt
                    ON spt.id = sp.picking_type_id
                WHERE sp.state NOT IN ('done', 'cancel')
                    AND (
                        sp.return_id IS NOT NULL
                        OR spt.code IN ('incoming', 'outgoing', 'internal')
                    )
            )
            """
        )
