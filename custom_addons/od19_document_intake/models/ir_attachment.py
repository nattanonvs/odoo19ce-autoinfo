# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import io
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# ข้ามการสกัดเมื่อไฟล์ใหญ่เกิน (กันหน่วยความจำ/timeout) — สเปก §9
MAX_EXTRACT_SIZE = 25 * 1024 * 1024
TEXT_MIMETYPES = ("text/plain", "text/csv", "text/html", "application/json")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _od19_extract_text(self):
        """คืน (text, engine) — engine เป็น None เมื่อสกัดไม่ได้"""
        self.ensure_one()
        mimetype = (self.mimetype or "").lower()
        raw = self.raw or b""

        if mimetype in TEXT_MIMETYPES:
            return raw.decode("utf-8", "replace"), "core"
        if mimetype == "application/pdf":
            try:
                from pdfminer.high_level import extract_text
            except ImportError:  # pragma: no cover — มีใน requirements-od19.txt
                return "", None
            try:
                text = extract_text(io.BytesIO(raw))
            except Exception as exc:  # noqa: BLE001 — ไฟล์ PDF เสียหายต้องไม่ทำให้ cron ล้ม
                _logger.warning("od19_document_intake: สกัด PDF ไม่ได้ (%s): %s", self.name, exc)
                return "", None
            return text or "", "pdfminer"
        return "", None

    def _od19_ocr_text(self):
        """OCR เป็นตัวเลือก — คืน '' เมื่อไม่มี engine (ไม่ทำให้ติดตั้งล้ม)"""
        self.ensure_one()
        try:
            import pytesseract  # noqa: F401
            from pdf2image import convert_from_bytes
        except ImportError:
            _logger.info(
                "od19_document_intake: ไม่มี OCR engine — ข้ามการ OCR ไฟล์ %s", self.name,
            )
            return ""
        try:
            import pytesseract
            pages = convert_from_bytes(self.raw or b"")
            return "\n".join(pytesseract.image_to_string(p) for p in pages)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("od19_document_intake: OCR ล้มเหลว (%s): %s", self.name, exc)
            return ""

    def _od19_run_extraction(self, channel=None):
        """สกัดข้อความ → เขียน od19.document.extract → ปรับ od19_index_state"""
        self.ensure_one()
        if self.file_size and self.file_size > MAX_EXTRACT_SIZE:
            self.od19_index_state = "skipped"
            return self.env["od19.document.extract"]

        text, engine = self._od19_extract_text()
        if not text and engine is None and channel and channel.enable_ocr:
            text, engine = self._od19_ocr_text(), "manual"
        if not text:
            self.od19_index_state = "skipped"
            return self.env["od19.document.extract"]

        extract = self.env["od19.document.extract"].create({
            "attachment_id": self.id,
            "text_content": text,
            "engine": engine or "manual",
            "lang": "th",
        })
        self.write({
            "od19_index_state": "done",
            "od19_indexed_at": fields.Datetime.now(),
        })
        return extract
