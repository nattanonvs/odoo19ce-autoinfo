from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class JasperReportAction(models.Model):
    _name = "jasper.report.action"
    _description = "Jasper Report Action"
    _order = "name"

    name = fields.Char(string="Action Name", required=True)
    template_id = fields.Many2one(
        "jasper.report.template",
        string="Report Template",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        related="template_id.model_id",
        store=True,
        readonly=True,
    )
    model = fields.Char(
        related="model_id.model",
        string="Model Name",
        store=True,
        readonly=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.constrains("template_id")
    def _check_template_id(self):
        for action in self:
            if not action.template_id:
                raise ValidationError(
                    _("A report action must have a template.")
                )

    def action_print(self, record_ids=None):
        self.ensure_one()
        if record_ids is None:
            record_ids = self.env.context.get("active_ids", [])
        template = self.template_id
        if template.report_type == "qweb":
            return self._print_qweb(record_ids)
        elif template.report_type == "jasper":
            return self._print_jasper(record_ids)
        return True

    def _print_qweb(self, record_ids):
        self.ensure_one()
        template = self.template_id
        records = self.env[template.model].browse(record_ids)
        if not records:
            return True
        # Use Odoo's built-in report rendering
        report_action = {
            "type": "ir.actions.report",
            "report_type": "qweb-pdf",
            "report_name": "od19_reporting_jasper.generic_report",
            "context": {
                "template_xml": template.template,
                "active_ids": record_ids,
            },
            "data": {
                "template_xml": template.template,
                "model": template.model,
                "ids": record_ids,
            },
        }
        return report_action

    def _print_jasper(self, record_ids):
        self.ensure_one()
        template = self.template_id
        return {
            "type": "ir.actions.act_url",
            "url": template.jasper_url,
            "target": "new",
        }
