from odoo import _, api, fields, models


class Od19ProjectPnlReport(models.TransientModel):
    _name = "od19.project.pnl.report"
    _description = "Project P&L Report"

    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=fields.Date.context_today,
    )
    company_ids = fields.Many2many(
        "res.company",
        string="Companies",
        default=lambda self: self.env.companies,
    )
    project_ids = fields.Many2many(
        "project.project",
        string="Projects",
        help="Leave empty to process every project.",
    )
    line_ids = fields.One2many(
        "od19.project.pnl.report.line",
        "wizard_id",
        string="Results",
    )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        projects = self.project_ids or self.env["project.project"].search(
            [("company_id", "in", self.company_ids.ids)]
        )
        lines = []
        for project in projects:
            values = project._od19_get_pnl_values(
                date_from=self.date_from,
                date_to=self.date_to,
                company_ids=self.company_ids.ids,
            )
            lines.append((0, 0, dict(values, project_id=project.id)))
        self.line_ids = lines
        return {
            "type": "ir.actions.act_window",
            "name": _("Project P&L"),
            "res_model": "od19.project.pnl.report.line",
            "view_mode": "list",
            "domain": [("id", "in", self.line_ids.ids)],
            "target": "current",
        }


class Od19ProjectPnlReportLine(models.TransientModel):
    _name = "od19.project.pnl.report.line"
    _description = "Project P&L Report Line"

    wizard_id = fields.Many2one(
        "od19.project.pnl.report",
        ondelete="cascade",
        required=True,
    )
    project_id = fields.Many2one("project.project", string="Project")
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
    )
    has_analytic = fields.Boolean(string="Has Analytic Account")
    revenue = fields.Float(string="Revenue")
    cost = fields.Float(string="Cost")
    gross_margin = fields.Float(string="Gross Margin")
    margin_percent = fields.Float(string="Margin %")
    uncategorized_amount = fields.Float(string="Uncategorized")
    warning = fields.Char(string="Warning", compute="_compute_warning")

    @api.depends("has_analytic", "revenue", "uncategorized_amount")
    def _compute_warning(self):
        for line in self:
            if not line.has_analytic:
                line.warning = _("No analytic account - P&L shows 0.")
            elif not line.revenue:
                line.warning = _("No recognized revenue yet.")
            elif line.uncategorized_amount:
                line.warning = _("Uncategorized amounts must be reviewed.")
            else:
                line.warning = False
