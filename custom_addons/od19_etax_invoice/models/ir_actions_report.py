# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Embed the signed e-Tax XML inside the produced PDF.

An e-Tax Invoice must travel as a single file carrying both the human readable
rendering and the machine readable, signed XML, so the report hook attaches the
signed XML to the PDF catalogue before the file is returned to the user.
"""

import base64
import logging

from odoo import models

from ..lib import pdf_embed

_logger = logging.getLogger(__name__)

_REPORT_NAME = "od19_etax_invoice.etax_document_report"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        content, report_type = super()._render_qweb_pdf(report_ref, res_ids, data)
        if report_type != "pdf" or not content:
            return content, report_type
        if self._get_report(report_ref).report_name != _REPORT_NAME:
            return content, report_type
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        return self._od19_embed_etax_xml(content, res_ids or []), "pdf"

    def _od19_embed_etax_xml(self, content, res_ids):
        """Return ``content`` with the signed XML attached when available."""
        documents = self.env["od19.etax.document"].browse(res_ids).exists()
        payload = False
        filename = pdf_embed.DEFAULT_FILENAME
        for document in documents:
            if document.signed_xml_file:
                payload = base64.b64decode(document.signed_xml_file)
                filename = document.signed_xml_filename or filename
                break
        if not payload:
            return content
        try:
            return pdf_embed.embed_xml(content, payload, filename=filename)
        except Exception:  # the PDF must still print if the attachment fails
            _logger.exception("Cannot embed the e-Tax XML into the PDF report.")
            return content
