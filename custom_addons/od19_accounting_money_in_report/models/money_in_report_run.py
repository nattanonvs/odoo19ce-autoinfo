from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MoneyInReportRun(models.Model):
    _name = "od19.money.in.report.run"
    _description = "OD19 Money In Report Run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, default=lambda self: _("New"), tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    date_from = fields.Date(required=True, index=True)
    date_to = fields.Date(required=True, index=True)
    phase = fields.Selection(
        [
            ("phase1_invoice_based", "Phase 1 - Invoice Based"),
            ("phase2_cash_invoice_based", "Phase 2A - Cash Invoice Based"),
        ],
        required=True,
        default="phase1_invoice_based",
        tracking=True,
    )
    generated_by = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    generated_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    notes = fields.Text()
    partner_ids = fields.Many2many("res.partner", string="Customers")
    salesperson_ids = fields.Many2many("res.users", string="Salespersons")
    project_ids = fields.Many2many("project.project", string="Projects")
    product_categ_ids = fields.Many2many("product.category", string="Product Categories")
    job_type_values = fields.Selection(
        [
            ("job", "Job"),
            ("pm", "PM"),
            ("service", "Service"),
            ("sale", "Sales"),
            ("unknown", "Unknown"),
        ],
        string="Job Type",
    )
    line_ids = fields.One2many(
        "od19.money.in.report.line",
        "run_id",
        string="Analysis Lines",
    )
    line_count = fields.Integer(compute="_compute_line_count", store=False)

    @api.depends("line_ids")
    def _compute_line_count(self):
        for run in self:
            run.line_count = len(run.line_ids)

    @api.model
    def _get_locked_snapshot_field_names(self):
        return {
            "company_id",
            "date_from",
            "date_to",
            "phase",
            "partner_ids",
            "salesperson_ids",
            "project_ids",
            "product_categ_ids",
            "job_type_values",
        }

    def write(self, vals):
        if "status" in vals:
            reverting_runs = self.filtered(
                lambda run: run.status == "done" and vals["status"] != "done"
            )
            if reverting_runs:
                raise UserError(
                    _("A report run cannot be reverted from done to another status.")
                )
        locked_fields = self._get_locked_snapshot_field_names()
        touched_locked_fields = sorted(locked_fields.intersection(vals))
        if touched_locked_fields:
            locked_runs = self.filtered(lambda run: run.status == "done")
            if locked_runs:
                raise UserError(
                    _(
                        "Snapshot fields cannot be changed after the run is marked done: %s"
                    )
                    % ", ".join(touched_locked_fields)
                )
        return super().write(vals)

    def action_open_lines(self):
        self.ensure_one()
        context = {
            "default_run_id": self.id,
            "search_default_run_id": self.id,
        }
        if self.phase == "phase1_invoice_based":
            context["search_default_phase1_only"] = 1
        return {
            "type": "ir.actions.act_window",
            "name": _("Money In Analysis Lines"),
            "res_model": "od19.money.in.report.line",
            "view_mode": "list,pivot,graph",
            "domain": [("run_id", "=", self.id)],
            "context": context,
            "target": "current",
        }

    def action_export_xlsx(self):
        """Export the report run(s) to an XLSX file using openpyxl."""
        self.ensure_one()
        xlsx_data = self.env[
            "report.od19_accounting_money_in_report.money_in_report_xlsx"
        ].create_xlsx_report(self.ids, {})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.xlsx" % (self.name or "money_in_report"),
                "datas": xlsx_data,
                "res_model": "od19.money.in.report.run",
                "res_id": self.id,
                "type": "binary",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
