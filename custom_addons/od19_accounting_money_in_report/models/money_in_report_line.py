from odoo import api, fields, models


class MoneyInReportLine(models.Model):
    _name = "od19.money.in.report.line"
    _description = "OD19 Money In Report Line"
    _order = "run_id desc, id desc"

    run_id = fields.Many2one(
        "od19.money.in.report.run",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one("res.company", required=True, index=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one("res.partner", index=True)
    salesperson_id = fields.Many2one("res.users", index=True)
    project_id = fields.Many2one("project.project", index=True)
    project_job_type = fields.Char(index=True)
    project_type_name = fields.Char(index=True)
    product_id = fields.Many2one("product.product", index=True)
    product_categ_id = fields.Many2one("product.category", index=True)
    invoice_id = fields.Many2one("account.move", index=True)
    invoice_line_id = fields.Many2one("account.move.line", index=True)
    invoice_date = fields.Date(index=True)
    stamp_date = fields.Date(index=True)
    customer_reference = fields.Char(index=True)
    sale_order_id = fields.Many2one("sale.order", index=True)
    sale_order_line_id = fields.Many2one("sale.order.line", index=True)
    recognition_mode = fields.Selection(
        [
            ("invoice_proxy", "Invoice Proxy"),
            ("cash_based", "Cash Based"),
        ],
        required=True,
        default="invoice_proxy",
        index=True,
    )
    phase = fields.Selection(
        [
            ("phase1_invoice_based", "Phase 1 - Invoice Based"),
            ("phase2_cash_invoice_based", "Phase 2A - Cash Invoice Based"),
        ],
        required=True,
        default="phase1_invoice_based",
        index=True,
    )
    recognized_amount = fields.Monetary(currency_field="currency_id")
    sale_order_amount = fields.Monetary(currency_field="currency_id")
    paid_amount = fields.Monetary(currency_field="currency_id")
    refund_amount = fields.Monetary(currency_field="currency_id")
    net_cash_amount = fields.Monetary(
        compute="_compute_net_cash",
        store=True,
        currency_field="currency_id",
    )
    recognized_cost = fields.Monetary(currency_field="currency_id")
    cost_preliminary_available = fields.Boolean(default=False)
    recognized_profit = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_profit_metrics",
        store=True,
    )
    recognized_margin_pct = fields.Float(
        compute="_compute_profit_metrics",
        store=True,
        digits=(16, 2),
    )
    cycle_start_date = fields.Date(index=True)
    cycle_end_date = fields.Date(index=True)
    cycle_days = fields.Integer(compute="_compute_cycle_metrics", store=True)
    payment_date = fields.Date(index=True)
    reconcile_date = fields.Date(index=True)
    is_preliminary_profit = fields.Boolean(default=True)
    is_invoice_bridged_dimension = fields.Boolean(default=True)
    profit_preliminary_available = fields.Boolean(
        compute="_compute_profit_metrics",
        store=True,
    )
    missing_start_date = fields.Boolean(
        compute="_compute_cycle_metrics", store=True, index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("company_id"):
                continue
            run_id = vals.get("run_id")
            if run_id:
                vals["company_id"] = (
                    self.env["od19.money.in.report.run"].browse(run_id).company_id.id
                )
        return super().create(vals_list)

    @api.depends("paid_amount", "refund_amount")
    def _compute_net_cash(self):
        for line in self:
            line.net_cash_amount = (line.paid_amount or 0.0) - (
                line.refund_amount or 0.0
            )

    @api.depends(
        "recognized_amount", "recognized_cost", "cost_preliminary_available"
    )
    def _compute_profit_metrics(self):
        for line in self:
            amount_is_available = (
                line.recognized_amount is not False
                and line.recognized_amount is not None
            )
            cost_is_available = bool(line.cost_preliminary_available)
            if amount_is_available and cost_is_available:
                amount = line.recognized_amount
                cost = line.recognized_cost
                profit = amount - cost
                line.recognized_profit = profit
                line.recognized_margin_pct = (
                    amount and (profit / amount) * 100.0 or 0.0
                )
            else:
                line.recognized_profit = False
                line.recognized_margin_pct = False
            line.profit_preliminary_available = bool(
                line.is_preliminary_profit
                and amount_is_available
                and cost_is_available
            )

    @api.depends("stamp_date", "cycle_start_date", "cycle_end_date")
    def _compute_cycle_metrics(self):
        for line in self:
            line.missing_start_date = not bool(line.stamp_date)
            if line.cycle_start_date and line.cycle_end_date:
                line.cycle_days = (
                    line.cycle_end_date - line.cycle_start_date
                ).days
            else:
                line.cycle_days = False
