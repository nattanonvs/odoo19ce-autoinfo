# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


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
