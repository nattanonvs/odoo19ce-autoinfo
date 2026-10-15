from odoo import api, fields, models, tools


class Od19ProjectRiskReport(models.Model):
    _name = "od19.project.risk.report"
    _description = "OD19 Project Risk Report"
    _auto = False
    _order = "risk_score desc"

    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    project_name = fields.Char(string="Project Name", readonly=True)
    contract_amount = fields.Float(string="Contract Amount", readonly=True)
    invoiced_amount = fields.Float(string="Invoiced Amount", readonly=True)
    actual_cost = fields.Float(string="Actual Cost", readonly=True)
    committed_cost = fields.Float(string="Committed Cost", readonly=True)
    overdue_ar = fields.Float(string="Overdue AR", readonly=True)
    margin_percent = fields.Float(
        string="Margin %",
        compute="_compute_margin_percent",
        store=False,
    )
    risk_score = fields.Integer(
        string="Risk Score",
        compute="_compute_risk_score",
        store=False,
    )
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Risk Level",
        compute="_compute_risk_level",
        store=False,
    )

    @api.depends("contract_amount", "actual_cost")
    def _compute_margin_percent(self):
        for rec in self:
            if rec.contract_amount:
                rec.margin_percent = (
                    (rec.contract_amount - rec.actual_cost) / rec.contract_amount * 100
                )
            else:
                rec.margin_percent = 0.0

    @api.depends("margin_percent", "overdue_ar", "project_id.date")
    def _compute_risk_score(self):
        today = fields.Date.today()
        for rec in self:
            score = 0
            if rec.margin_percent < 15:
                score += 40
            if rec.overdue_ar > 0:
                score += 30
            project_date = rec.project_id.date if rec.project_id else False
            if project_date and project_date < today:
                score += 30
            rec.risk_score = score

    @api.depends("risk_score")
    def _compute_risk_level(self):
        for rec in self:
            if rec.risk_score >= 60:
                rec.risk_level = "high"
            elif rec.risk_score >= 30:
                rec.risk_level = "medium"
            else:
                rec.risk_level = "low"

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    p.id AS id,
                    p.id AS project_id,
                    p.name AS project_name,
                    COALESCE(so_agg.contract_amount, 0.0) AS contract_amount,
                    COALESCE(ar_agg.invoiced_amount, 0.0) AS invoiced_amount,
                    COALESCE(exp_agg.actual_cost, 0.0) AS actual_cost,
                    COALESCE(po_agg.committed_cost, 0.0) AS committed_cost,
                    COALESCE(overdue_agg.overdue_ar, 0.0) AS overdue_ar
                FROM project_project p
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_untaxed) AS contract_amount
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            so.id,
                            so.amount_untaxed
                        FROM project_project p2
                        JOIN sale_order_line sol
                            ON sol.analytic_distribution ? p2.account_id::text
                        JOIN sale_order so
                            ON so.id = sol.order_id
                            AND so.state IN ('sale', 'done')
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) so_agg ON so_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_untaxed) AS invoiced_amount
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            am.id,
                            am.amount_untaxed
                        FROM project_project p2
                        JOIN account_move_line aml
                            ON aml.analytic_distribution ? p2.account_id::text
                        JOIN account_move am
                            ON am.id = aml.move_id
                            AND am.move_type = 'out_invoice'
                            AND am.state = 'posted'
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) ar_agg ON ar_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        p2.id AS project_id,
                        SUM(exp.total_amount) AS actual_cost
                    FROM project_project p2
                    JOIN hr_expense exp
                        ON exp.analytic_distribution ? p2.account_id::text
                    WHERE p2.account_id IS NOT NULL
                        AND exp.state IN ('approved', 'posted', 'in_payment', 'paid')
                    GROUP BY p2.id
                ) exp_agg ON exp_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_untaxed) AS committed_cost
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            po.id,
                            po.amount_untaxed
                        FROM project_project p2
                        JOIN purchase_order_line pol
                            ON pol.analytic_distribution ? p2.account_id::text
                        JOIN purchase_order po
                            ON po.id = pol.order_id
                            AND po.state IN ('purchase', 'done')
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) po_agg ON po_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_residual) AS overdue_ar
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            am.id,
                            am.amount_residual
                        FROM project_project p2
                        JOIN account_move_line aml
                            ON aml.analytic_distribution ? p2.account_id::text
                        JOIN account_move am
                            ON am.id = aml.move_id
                            AND am.move_type = 'out_invoice'
                            AND am.state = 'posted'
                            AND am.invoice_date_due < CURRENT_DATE
                            AND am.amount_residual > 0
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) overdue_agg ON overdue_agg.project_id = p.id
                ORDER BY p.id
            )
            """
        )
