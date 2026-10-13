from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class JasperReportTemplate(models.Model):
    _name = "jasper.report.template"
    _description = "Jasper Report Template"
    _order = "name"

    name = fields.Char(string="Template Name", required=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    model = fields.Char(
        related="model_id.model",
        string="Model Name",
        store=True,
        readonly=True,
    )
    report_type = fields.Selection(
        [
            ("qweb", "QWeb (PDF)"),
            ("jasper", "JasperServer"),
        ],
        string="Report Type",
        default="qweb",
        required=True,
    )
    template = fields.Text(
        string="Template Content",
        help="QWeb XML template or JasperServer report reference",
    )
    jasper_url = fields.Char(
        string="JasperServer URL",
        help="URL of the JasperServer report (for jasper type)",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.constrains("model_id")
    def _check_model_id(self):
        for template in self:
            if not template.model_id:
                raise ValidationError(
                    _("A report template must be linked to a model.")
                )

    @api.constrains("report_type", "template", "jasper_url")
    def _check_template_content(self):
        for template in self:
            if template.report_type == "qweb" and not template.template:
                raise ValidationError(
                    _("QWeb template content is required for QWeb report type.")
                )
            if template.report_type == "jasper" and not template.jasper_url:
                raise ValidationError(
                    _("JasperServer URL is required for Jasper report type.")
                )
