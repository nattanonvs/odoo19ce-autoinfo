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
                "od19_invoice_closure_state",
            ]
        )
        self.env["account.move"].flush_model(
            [
                "company_id",
                "state",
                "amount_residual",
                "od19_operational_flow",
            ]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH company_scope AS (
                    SELECT DISTINCT so.company_id
                    FROM sale_order so
                    WHERE so.od19_billing_readiness_state = 'ready'
                        AND so.state != 'cancel'
                        AND COALESCE(so.od19_invoice_closure_state, '') != 'paid'

                    UNION

                    SELECT DISTINCT am.company_id
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.od19_operational_flow IN ('customer', 'vendor')
                        AND am.amount_residual != 0
                ),
                backlog AS (
                    SELECT
                        so.company_id,
                        COALESCE(SUM(so.amount_total), 0.0) AS billable_backlog
                    FROM sale_order so
                    WHERE so.od19_billing_readiness_state = 'ready'
                        AND so.state != 'cancel'
                        AND COALESCE(so.od19_invoice_closure_state, '') != 'paid'
                    GROUP BY so.company_id
                ),
                receivable AS (
                    SELECT
                        am.company_id,
                        COALESCE(SUM(am.amount_residual), 0.0) AS open_receivable
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.od19_operational_flow = 'customer'
                        AND am.amount_residual != 0
                    GROUP BY am.company_id
                ),
                payable AS (
                    SELECT
                        am.company_id,
                        COALESCE(SUM(am.amount_residual), 0.0) AS open_payable
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.od19_operational_flow = 'vendor'
                        AND am.amount_residual != 0
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
