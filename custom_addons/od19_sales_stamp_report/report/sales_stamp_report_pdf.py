from odoo import _, models
from odoo.exceptions import UserError


class SalesStampReportPdf(models.AbstractModel):
    """Report model that feeds the PDF summary template.

    The wizard passes a JSON-safe ``filters`` dictionary (dates as ISO
    strings, ids as integers) through the report action, so the analysis is
    re-computed here on the server where recordsets and dates are available.
    """

    _name = "report.od19_sales_stamp_report.sales_stamp_report_pdf"
    _description = "Sales Stamp Date Report (PDF)"

    def _get_report_values(self, docids, data=None):
        data = data or {}
        filters = data.get("filters")
        if not filters:
            raise UserError(
                _("This report must be launched from the Sales Stamp report wizard.")
            )

        report_data = self.env[
            "od19.sales.stamp.report.analysis"
        ].build_report_data(filters)

        return {
            "doc_ids": docids,
            "doc_model": "od19.sales.stamp.report",
            "docs": self.env["od19.sales.stamp.report"].browse([]),
            "company": report_data["company"],
            "filters": filters,
            "period_label": report_data["period_label"],
            "period_rows": report_data["period_rows"],
            "dimension_tables": report_data["dimension_tables"],
            "totals": report_data["totals"],
        }
