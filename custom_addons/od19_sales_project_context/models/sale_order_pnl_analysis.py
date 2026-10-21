from odoo import _, api, fields, models


class Od19SaleOrderPnlAnalysis(models.TransientModel):
    """Pre-quote cost & profit analysis for the project linked to a sale order.

    Reuses ``project.project._od19_get_pnl_values()`` (the single P&L contract,
    defined in od19_project_analytic) instead of re-implementing the
    revenue/cost classification.
    """

    _name = "od19.sale.order.pnl.analysis"
    _description = "Sale Order Cost & Profit Analysis"

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
    )
    project_id = fields.Many2one(
        related="sale_order_id.od19_project_id",
        string="Project",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="sale_order_id.currency_id",
        readonly=True,
    )
    date_from = fields.Date(
        string="From",
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To",
        default=fields.Date.context_today,
    )
    revenue = fields.Monetary(
        string="Revenue",
        currency_field="currency_id",
        compute="_compute_values",
    )
    cost = fields.Monetary(
        string="Cost",
        currency_field="currency_id",
        compute="_compute_values",
    )
    gross_margin = fields.Monetary(
        string="Gross Margin",
        currency_field="currency_id",
        compute="_compute_values",
    )
    margin_percent = fields.Float(
        string="Margin %",
        compute="_compute_values",
    )
    uncategorized_amount = fields.Monetary(
        string="Uncategorized",
        currency_field="currency_id",
        compute="_compute_values",
    )
    has_analytic = fields.Boolean(compute="_compute_values")
    note = fields.Char(string="Note", compute="_compute_values")

    @api.depends("sale_order_id", "project_id", "date_from", "date_to")
    def _compute_values(self):
        for wizard in self:
            project = wizard.project_id
            values = {
                "revenue": 0.0,
                "cost": 0.0,
                "gross_margin": 0.0,
                "margin_percent": 0.0,
                "uncategorized_amount": 0.0,
                "has_analytic": False,
            }
            if not project:
                values["note"] = _(
                    "Select a project on the sale order to analyse cost and profit."
                )
            else:
                pnl = project._od19_get_pnl_values(
                    date_from=wizard.date_from,
                    date_to=wizard.date_to,
                    company_ids=[wizard.sale_order_id.company_id.id],
                )
                values.update(
                    revenue=pnl["revenue"],
                    cost=pnl["cost"],
                    gross_margin=pnl["gross_margin"],
                    margin_percent=pnl["margin_percent"],
                    uncategorized_amount=pnl["uncategorized_amount"],
                    has_analytic=pnl["has_analytic"],
                )
                if not pnl["has_analytic"]:
                    values["note"] = _(
                        "The project has no analytic account - cost and profit "
                        "cannot be analysed."
                    )
                elif not pnl["revenue"]:
                    values["note"] = _("No recognized revenue on the project yet.")
                elif pnl["uncategorized_amount"]:
                    values["note"] = _(
                        "Uncategorized amounts must be reviewed."
                    )
                else:
                    values["note"] = False
            wizard.update(values)
