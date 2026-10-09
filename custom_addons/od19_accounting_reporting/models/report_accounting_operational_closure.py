from odoo import fields, models, tools


class ReportAccountingOperationalClosure(models.Model):
    _name = "od19.report.accounting.operational.closure"
    _description = "OD19 Accounting Operational Closure"
    _auto = False
    _rec_name = "metric_label"

    metric_key = fields.Char(readonly=True)
    metric_label = fields.Char(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    item_count = fields.Integer(readonly=True)
    total_amount = fields.Float(readonly=True)

    def search(self, domain, offset=0, limit=None, order=None):
        self.env.flush_all()
        self.invalidate_model()
        self.env["sale.order"].flush_model(
            [
                "company_id",
                "state",
                "amount_total",
                "invoice_status",
                "od19_billing_readiness_state",
            ]
        )
        self.env["sale.order.line"].flush_model(
            [
                "order_id",
                "display_type",
                "price_total",
                "product_uom_qty",
                "qty_to_invoice",
            ]
        )
        self.env["account.move"].flush_model(
            [
                "company_id",
                "state",
                "amount_residual_signed",
                "amount_total_signed",
                "move_type",
                "invoice_date_due",
                "payment_state",
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
                        COALESCE(
                            SUM(
                                CASE
                                    WHEN sol.display_type IS NULL
                                        AND sol.product_uom_qty != 0
                                    THEN (sol.price_total / sol.product_uom_qty) * sol.qty_to_invoice
                                    ELSE 0.0
                                END
                            ),
                            0.0
                        ) AS amount_to_invoice
                    FROM sale_order so
                    JOIN sale_order_line sol
                        ON sol.order_id = so.id
                    WHERE so.state IN ('sale', 'done')
                        AND so.od19_billing_readiness_state = 'ready'
                    GROUP BY so.id, so.company_id
                ),
                move_scope AS (
                    SELECT
                        am.id,
                        am.company_id,
                        am.move_type,
                        am.payment_state,
                        am.amount_residual_signed,
                        am.amount_total_signed,
                        am.invoice_date_due
                    FROM account_move am
                    WHERE am.state = 'posted'
                        AND am.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
                ),
                company_scope AS (
                    SELECT rc.id AS company_id
                    FROM res_company rc
                ),
                metric_keys AS (
                    SELECT 'billable_backlog' AS metric_key, 'Billable Backlog' AS metric_label
                    UNION ALL SELECT 'open_receivable', 'Open Receivable'
                    UNION ALL SELECT 'overdue_receivable', 'Overdue Receivable'
                    UNION ALL SELECT 'open_payable', 'Open Payable'
                    UNION ALL SELECT 'due_payable', 'Due Payable'
                    UNION ALL SELECT 'cash_application_status', 'Cash Application Status'
                    UNION ALL SELECT 'unreconciled_customer_items', 'Unreconciled Customer Items'
                    UNION ALL SELECT 'unreconciled_vendor_items', 'Unreconciled Vendor Items'
                ),
                metric_scope AS (
                    SELECT
                        cs.company_id,
                        mk.metric_key,
                        mk.metric_label
                    FROM company_scope cs
                    CROSS JOIN metric_keys mk
                ),
                backlog_metric AS (
                    SELECT
                        ob.company_id,
                        'billable_backlog' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ob.amount_to_invoice), 0.0) AS total_amount
                    FROM order_backlog ob
                    WHERE ob.amount_to_invoice != 0
                    GROUP BY ob.company_id
                ),
                open_receivable_metric AS (
                    SELECT
                        ms.company_id,
                        'open_receivable' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ms.amount_residual_signed), 0.0) AS total_amount
                    FROM move_scope ms
                    WHERE ms.move_type IN ('out_invoice', 'out_refund')
                        AND ms.amount_residual_signed != 0
                    GROUP BY ms.company_id
                ),
                overdue_receivable_metric AS (
                    SELECT
                        ms.company_id,
                        'overdue_receivable' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ms.amount_residual_signed), 0.0) AS total_amount
                    FROM move_scope ms
                    WHERE ms.move_type IN ('out_invoice', 'out_refund')
                        AND ms.amount_residual_signed != 0
                        AND ms.invoice_date_due IS NOT NULL
                        AND ms.invoice_date_due < CURRENT_DATE
                        AND ms.payment_state = 'not_paid'
                    GROUP BY ms.company_id
                ),
                open_payable_metric AS (
                    SELECT
                        ms.company_id,
                        'open_payable' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ms.amount_residual_signed), 0.0) AS total_amount
                    FROM move_scope ms
                    WHERE ms.move_type IN ('in_invoice', 'in_refund')
                        AND ms.amount_residual_signed != 0
                    GROUP BY ms.company_id
                ),
                due_payable_metric AS (
                    SELECT
                        ms.company_id,
                        'due_payable' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ms.amount_residual_signed), 0.0) AS total_amount
                    FROM move_scope ms
                    WHERE ms.move_type IN ('in_invoice', 'in_refund')
                        AND ms.amount_residual_signed != 0
                        AND ms.invoice_date_due IS NOT NULL
                        AND ms.invoice_date_due <= CURRENT_DATE
                        AND ms.payment_state = 'not_paid'
                    GROUP BY ms.company_id
                ),
                cash_application_metric AS (
                    SELECT
                        ms.company_id,
                        'cash_application_status' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(
                            SUM(
                                ABS(ms.amount_total_signed) - ABS(ms.amount_residual_signed)
                            ),
                            0.0
                        ) AS total_amount
                    FROM move_scope ms
                    WHERE ms.payment_state IN ('partial', 'in_payment')
                        OR (
                            ms.payment_state = 'blocked'
                            AND ABS(ms.amount_residual_signed) < ABS(ms.amount_total_signed)
                        )
                    GROUP BY ms.company_id
                ),
                unreconciled_customer_metric AS (
                    SELECT
                        ms.company_id,
                        'unreconciled_customer_items' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ms.amount_residual_signed), 0.0) AS total_amount
                    FROM move_scope ms
                    WHERE ms.move_type IN ('out_invoice', 'out_refund')
                        AND ms.amount_residual_signed != 0
                    GROUP BY ms.company_id
                ),
                unreconciled_vendor_metric AS (
                    SELECT
                        ms.company_id,
                        'unreconciled_vendor_items' AS metric_key,
                        COUNT(*)::integer AS item_count,
                        COALESCE(SUM(ms.amount_residual_signed), 0.0) AS total_amount
                    FROM move_scope ms
                    WHERE ms.move_type IN ('in_invoice', 'in_refund')
                        AND ms.amount_residual_signed != 0
                    GROUP BY ms.company_id
                ),
                metric_values AS (
                    SELECT * FROM backlog_metric
                    UNION ALL
                    SELECT * FROM open_receivable_metric
                    UNION ALL
                    SELECT * FROM overdue_receivable_metric
                    UNION ALL
                    SELECT * FROM open_payable_metric
                    UNION ALL
                    SELECT * FROM due_payable_metric
                    UNION ALL
                    SELECT * FROM cash_application_metric
                    UNION ALL
                    SELECT * FROM unreconciled_customer_metric
                    UNION ALL
                    SELECT * FROM unreconciled_vendor_metric
                )
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY metric_scope.company_id, metric_scope.metric_key
                    ) AS id,
                    metric_scope.metric_key,
                    metric_scope.metric_label,
                    metric_scope.company_id,
                    COALESCE(metric_values.item_count, 0) AS item_count,
                    COALESCE(metric_values.total_amount, 0.0) AS total_amount
                FROM metric_scope
                LEFT JOIN metric_values
                    ON metric_values.company_id = metric_scope.company_id
                    AND metric_values.metric_key = metric_scope.metric_key
            )
            """
        )
