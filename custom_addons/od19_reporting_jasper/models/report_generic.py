from odoo import api, models


class ReportGenericTemplate(models.AbstractModel):
    """Render a generic report for whichever model a template targets.

    The report action ``od19_reporting_jasper.action_report_generic`` is not
    bound to a single model: the target model is passed through ``data`` (or
    the context) so one report can print records of any model. This is the
    idiomatic Odoo way to build a model-agnostic report, because
    ``ir.actions.report._get_rendering_context`` uses this abstract model
    instead of browsing ``report.model``.
    """

    _name = "report.od19_reporting_jasper.generic_report"
    _description = "OD19 Generic Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        model_name = (
            data.get("model")
            or data.get("doc_model")
            or self.env.context.get("model")
            or self.env.context.get("doc_model")
        )
        if model_name and model_name in self.env:
            docs = self.env[model_name].browse(docids)
        else:
            docs = self.env["res.partner"].browse()
        return {
            "doc_ids": docids,
            "doc_model": model_name,
            "docs": docs,
        }
