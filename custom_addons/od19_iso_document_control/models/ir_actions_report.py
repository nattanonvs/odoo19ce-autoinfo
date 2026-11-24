# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models
from odoo.tools.pdf import merge_pdf

# Report that assembles the controlled document and concatenates the
# document's PDF attachments after the generated pages.
CONTROLLED_DOCUMENT_REPORT = (
    "od19_iso_document_control.report_iso_controlled_document"
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    od19_iso_document_id = fields.Many2one(
        "od19.iso.document",
        string="ISO Document (เลขที่กำกับ)",
        help="เอกสารควบคุม ISO ที่เกี่ยวข้องกับรายงานนี้ "
        "จะแสดงเลขที่กำกับ (เช่น FM-PU-12) ที่มุมล่างของรายงาน",
    )
    od19_iso_show_footer = fields.Boolean(
        string="แสดงเลขที่กำกับ ISO ที่ท้ายรายงาน",
        default=True,
        help="ถ้าเปิดใช้งาน จะแสดงเลขที่กำกับเอกสาร ISO "
        "ที่มุมซ้ายล่างและมุมขวาล่างของรายงาน",
    )

    def _get_rendering_context(self, report, docids, data):
        """Inject report_action into the report rendering context.

        This allows QWeb templates to access the current report action
        (and its linked ISO document) to render the document control
        number in the footer.
        """
        values = super()._get_rendering_context(report, docids, data)
        values.setdefault("report_action", report)
        return values

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Append the document's PDF attachments to the controlled document.

        Only the ``report_iso_controlled_document`` report is affected; every
        other report keeps the default behaviour.
        """
        pdf_content, report_type = super()._render_qweb_pdf(
            report_ref, res_ids, data
        )
        if report_type != "pdf" or not res_ids:
            return pdf_content, report_type
        report = self._get_report(report_ref)
        if report.report_name != CONTROLLED_DOCUMENT_REPORT:
            return pdf_content, report_type
        ids = res_ids if isinstance(res_ids, (list, tuple)) else [res_ids]
        if len(ids) != 1:
            return pdf_content, report_type
        document = self.env["od19.iso.document"].browse(ids[0])
        extra_streams = document.sudo()._get_content_pdf_streams()
        if not extra_streams:
            return pdf_content, report_type
        return merge_pdf([pdf_content, *extra_streams]), report_type
