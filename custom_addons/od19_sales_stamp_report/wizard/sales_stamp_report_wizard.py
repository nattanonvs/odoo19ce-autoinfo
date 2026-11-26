from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19SalesStampReportWizard(models.TransientModel):
    """Collect the filters used to print the PDF summary or export the XLSX."""

    _name = "od19.sales.stamp.report.wizard"
    _description = "Sales Stamp Date Report Wizard"

    date_from = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1),
    )
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    period_type = fields.Selection(
        [
            ("month", "Monthly"),
            ("quarter", "Quarterly"),
            ("year", "Yearly"),
        ],
        required=True,
        default="month",
    )
    department_ids = fields.Many2many("hr.department", string="Departments")
    user_ids = fields.Many2many("res.users", string="Salespersons")
    partner_ids = fields.Many2many("res.partner", string="Customers")
    sale_mode = fields.Selection(
        [
            ("one_time", "One-time"),
            ("contract", "Contract-based"),
        ],
        string="Sale Mode",
    )
    top_n = fields.Integer(
        string="Top Values per Dimension",
        default=10,
        help="Keep only the N largest values of each dimension table. "
        "Set 0 to keep every value.",
    )

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for wizard in self:
            if (
                wizard.date_from
                and wizard.date_to
                and wizard.date_from > wizard.date_to
            ):
                raise ValidationError(
                    _("Date From must be earlier than or equal to Date To.")
                )

    def _prepare_filters(self):
        """Return a JSON-safe filter dictionary for the analysis engine."""
        self.ensure_one()
        return {
            "company_id": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "period_type": self.period_type,
            "department_ids": self.department_ids.ids,
            "user_ids": self.user_ids.ids,
            "partner_ids": self.partner_ids.ids,
            "sale_mode": self.sale_mode or False,
            "top_n": self.top_n or 0,
        }

    def _check_has_data(self, filters):
        rows = self.env["od19.sales.stamp.report.analysis"].get_period_rows(filters)
        if not any(row["orders"] for row in rows):
            raise UserError(
                _(
                    "No confirmed sale order carries a stamp date in the selected "
                    "period and filters.\n\n"
                    "Please widen the date range or relax the filters."
                )
            )

    def action_print_pdf(self):
        self.ensure_one()
        filters = self._prepare_filters()
        self._check_has_data(filters)
        return self.env.ref(
            "od19_sales_stamp_report.action_report_sales_stamp_pdf"
        ).report_action(self, data={"filters": filters})

    def action_export_xlsx(self):
        self.ensure_one()
        filters = self._prepare_filters()
        self._check_has_data(filters)
        xlsx_data = self.env[
            "report.od19_sales_stamp_report.sales_stamp_report_xlsx"
        ].create_xlsx_report(self.ids, {"filters": filters})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "sales_stamp_report_%s.xlsx"
                % fields.Date.to_string(self.date_to),
                "datas": xlsx_data,
                "res_model": self._name,
                "res_id": self.id,
                "type": "binary",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
