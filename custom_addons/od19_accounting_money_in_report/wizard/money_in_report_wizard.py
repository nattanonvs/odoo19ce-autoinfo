from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class MoneyInReportWizard(models.TransientModel):
    _name = "od19.money.in.report.wizard"
    _description = "OD19 Money In Report Wizard"

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    phase = fields.Selection(
        [
            ("phase1_invoice_based", "Phase 1 - Invoice Based"),
            ("phase2_cash_invoice_based", "Phase 2A - Cash Invoice Based"),
        ],
        required=True,
        default="phase1_invoice_based",
    )
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
    invoice_candidate_count = fields.Integer(
        string="Invoices Found",
        compute="_compute_preview_counts",
    )
    matching_invoice_count = fields.Integer(
        string="Invoices With Matching Lines",
        compute="_compute_preview_counts",
    )
    matching_line_count = fields.Integer(
        string="Preview Analysis Lines",
        compute="_compute_preview_counts",
    )

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(
                    _("Date From must be earlier than or equal to Date To.")
                )

    @api.depends(
        "date_from",
        "date_to",
        "company_id",
        "phase",
        "partner_ids",
        "salesperson_ids",
        "project_ids",
        "product_categ_ids",
        "job_type_values",
    )
    def _compute_preview_counts(self):
        builder = self.env["od19.money.in.report.builder"]
        for wizard in self:
            if not wizard.date_from or not wizard.date_to or not wizard.company_id:
                wizard.invoice_candidate_count = 0
                wizard.matching_invoice_count = 0
                wizard.matching_line_count = 0
                continue
            counts = builder.get_preview_counts(wizard)
            wizard.invoice_candidate_count = counts["invoice_candidate_count"]
            wizard.matching_invoice_count = counts["matching_invoice_count"]
            wizard.matching_line_count = counts["matching_line_count"]

    def action_generate_report(self):
        self.ensure_one()
        report_run = self.env[
            "od19.money.in.report.builder"
        ].create_run_from_wizard(self)
        if not report_run.line_count:
            help_message = _(
                "No analysis lines were generated for this run.\n\n"
                "Please check:\n"
                "- Date range matches invoice_date (not stamp_date in Phase 1)\n"
                "- Invoices are posted customer invoices\n"
                "- Invoice lines contain products\n"
                "- Filters (customer/salesperson/project/category/job type) are not too restrictive\n"
                "- Selected company matches invoice company"
            )
            if self.phase == "phase2_cash_invoice_based":
                help_message = _(
                    "No analysis lines were generated for this run.\n\n"
                    "Please check:\n"
                    "- Date range matches payment_date in Phase 2A\n"
                    "- Invoices have real payment/reconcile events in the selected period\n"
                    "- Invoice lines contain products for invoice-bridged dimensions\n"
                    "- Filters (customer/salesperson/project/category/job type) are not too restrictive\n"
                    "- Selected company matches invoice company and payment company"
                )
            raise UserError(help_message)
        return report_run.action_open_lines()

    def action_generate(self):
        return self.action_generate_report()
