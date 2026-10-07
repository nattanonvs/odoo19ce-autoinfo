from odoo import fields, models, tools


class ReportAccountingOperationalClosure(models.Model):
    _name = "od19.report.accounting.operational.closure"
    _description = "OD19 Accounting Operational Closure"
    _auto = False

    company_id = fields.Many2one("res.company", readonly=True)
    billable_backlog = fields.Float(readonly=True)
    open_receivable = fields.Float(readonly=True)
    open_payable = fields.Float(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["sale.order"].flush_model(
            [
                "company_id",
                "state",
                "amount_total",
                "od19_billing_readiness_state",
            ]
        )
        self.env["sale.order.line"].flush_model(
            [
                "order_id",
                "display_type",
            ]
        )
        self.env["account.move.line"].flush_model(["move_id", "price_total"])
        self.env["account.move"].flush_model(
            [
                "company_id",
                "state",
                "amount_residual_signed",
                "move_type",
                "od19_operational_flow",
            ]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH order_backlog AS (
                    SELECT
                        so.id AS order_id,
                        so.company_id,
                        GREATEST(
                            so.amount_total - COALESCE(
                                SUM(
                                    CASE
                                        WHEN sol.display_type IS NULL
                                            AND am.state = 'posted'
                                            AND am.move_type = 'out_invoice'
                                        THEN aml.price_total
                                        ELSE 0.0
                                    END
                                ),
                                0.0
                            ),
                            0.0
                        ) AS amount_to_invoice
                    FROM sale_order so
                    JOIN sale_order_line sol
                        ON sol.order_id = so.id
                    LEFT JOIN sale_order_line_invoice_rel solir
                        ON solir.order_line_id = sol.id
                    LEFT JOIN account_move_line aml
                        ON aml.id = solir.invoice_line_id
                    LEFT JOIN account_move am
                        ON am.id = aml.move_id
                    WHERE so.state IN ('sale', 'done')
                        AND so.od19_billing_readiness_state = 'ready'
                    GROUP BY so.id, so.company_id, so.amount_total
                ),
                company_scope AS (
                    SELECT DISTINCT so.company_id
                    FROM order_backlog so
                    WHERE so.amount_to_invoice != 0

                    UNION

                    SELECT DISTINCT am.company_id
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.od19_operational_flow IN ('customer', 'vendor')
                        AND am.amount_residual_signed != 0
                ),
                backlog AS (
                    SELECT
                        order_backlog.company_id,
                        COALESCE(SUM(order_backlog.amount_to_invoice), 0.0) AS billable_backlog
                    FROM order_backlog
                    WHERE order_backlog.amount_to_invoice != 0
                    GROUP BY order_backlog.company_id
                ),
                receivable AS (
                    SELECT
                        am.company_id,
                        COALESCE(SUM(am.amount_residual_signed), 0.0) AS open_receivable
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.od19_operational_flow = 'customer'
                        AND am.amount_residual_signed != 0
                    GROUP BY am.company_id
                ),
                payable AS (
                    SELECT
                        am.company_id,
                        COALESCE(SUM(am.amount_residual_signed), 0.0) AS open_payable
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.od19_operational_flow = 'vendor'
                        AND am.amount_residual_signed != 0
                    GROUP BY am.company_id
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY company_scope.company_id) AS id,
                    company_scope.company_id,
                    COALESCE(backlog.billable_backlog, 0.0) AS billable_backlog,
                    COALESCE(receivable.open_receivable, 0.0) AS open_receivable,
                    COALESCE(payable.open_payable, 0.0) AS open_payable
                FROM company_scope
                LEFT JOIN backlog
                    ON backlog.company_id = company_scope.company_id
                LEFT JOIN receivable
                    ON receivable.company_id = company_scope.company_id
                LEFT JOIN payable
                    ON payable.company_id = company_scope.company_id
            )
            """
        )
