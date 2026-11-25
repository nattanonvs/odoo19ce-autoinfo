# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""OCR service for the OD19 scan-to-article flow.

Engines (choose with ``od19_scan.ocr_engine`` or per-call):

* ``ollama``    - vision model served by any OpenAI-compatible endpoint
                  (Ollama ``/v1`` by default). Primary engine, 100% local.
* ``tesseract`` - the local Tesseract CLI, used as an offline fallback.
* ``manual``    - no OCR: the user types/corrects the text themselves.
* ``auto``      - try ``ollama`` then ``tesseract`` and report which one won.

The service never hard-fails the whole wizard: each engine raises a clear
``UserError`` that the caller can present, and ``auto`` reports the engine
that actually produced text.
"""

import base64
import logging
import os
import re
import shutil
import subprocess
import tempfile

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "od19_scan"

IMAGE_MIMETYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/gif",
}

ENGINE_SELECTION = [
    ("auto", "อัตโนมัติ (Vision → Tesseract)"),
    ("ollama", "Ollama Vision (AI ในเครื่อง)"),
    ("tesseract", "Tesseract (ออฟไลน์)"),
    ("manual", "กรอกเอง (ไม่ใช้ OCR)"),
]

VISION_PROMPT = (
    "คุณคือระบบ OCR ระดับมืออาชีพ ถอดข้อความทั้งหมดจากภาพให้ถูกต้องครบถ้วน "
    "รักษาการขึ้นบรรทัดใหม่ตามต้นฉบับ ใช้ตัวเลข/ตัวอักษรไทย-อังกฤษตามจริง "
    "ถ้ามีตารางให้เขียนเป็นข้อความที่อ่านง่าย "
    "ตอบกลับเฉพาะข้อความที่ถอดได้เท่านั้น ห้ามอธิบาย ห้ามใส่ความคิดเห็น "
    "ห้ามใส่เครื่องหมายคำพูดครอบทั้งบล็อก"
)


class Od19OcrService(models.AbstractModel):
    _name = "od19.ocr.service"
    _description = "บริการ OCR สำหรับแปลงไฟล์สแกนเป็นข้อความ (OD19)"

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @api.model
    def _get_param(self, key, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("%s.%s" % (PARAM_PREFIX, key), default)
        )

    @api.model
    def _get_vision_config(self):
        """Merge AI-endpoint config with the scan-specific vision model."""
        ai = self.env["od19.ai.assistant"]._get_ai_config()
        vision_model = self._get_param("vision_model") or ai.get("model") or ""
        return {
            "base_url": ai.get("base_url") or "",
            "api_key": ai.get("api_key") or "",
            "model": vision_model,
            "timeout": ai.get("timeout") or 60,
        }

    @api.model
    def _default_engine(self):
        return self._get_param("ocr_engine") or "auto"

    @api.model
    def _tesseract_lang(self, language="auto"):
        configured = self._get_param("tesseract_lang")
        if configured:
            return configured
        if language == "th":
            return "tha+eng"
        if language == "en":
            return "eng"
        return "tha+eng"

    # ------------------------------------------------------------------
    # Capability probing (used by views / wizard to show what is available)
    # ------------------------------------------------------------------
    @api.model
    def _tesseract_path(self):
        return shutil.which("tesseract")

    @api.model
    def engine_available(self, engine):
        if engine == "manual":
            return True
        if engine == "tesseract":
            return bool(self._tesseract_path())
        if engine == "ollama":
            cfg = self._get_vision_config()
            return bool(cfg["base_url"] and cfg["model"])
        return False

    @api.model
    def available_engines(self):
        return [e for e, _label in ENGINE_SELECTION if self.engine_available(e)]

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @api.model
    def extract_text(self, image_b64, filename="scan.jpg", engine=None, language="auto"):
        """Extract text from a base64-encoded image (Odoo binary value).

        :returns: dict ``{"text": str, "engine": str}``
        :raises UserError: when no engine could read the document.
        """
        engine = engine or self._default_engine()
        if not image_b64:
            raise UserError("ไม่พบภาพสำหรับอ่านข้อความ")
        mimetype = self._guess_mimetype(filename)
        raw = base64.b64decode(image_b64)

        if self._is_pdf(mimetype, filename):
            return {"text": self._extract_pdf(raw), "engine": "pdfminer"}

        if engine == "manual":
            return {"text": "", "engine": "manual"}

        if engine == "auto":
            errors = []
            for candidate in ("ollama", "tesseract"):
                try:
                    text = self._run_engine(candidate, image_b64, raw, mimetype, language)
                    if text.strip():
                        return {"text": text.strip(), "engine": candidate}
                    errors.append("%s: ไม่พบข้อความในภาพ" % candidate)
                except UserError as exc:
                    errors.append(str(exc))
                except Exception as exc:  # noqa: BLE001 - keep auto resilient
                    _logger.exception("OD19 OCR engine %s failed", candidate)
                    errors.append("%s: %s" % (candidate, exc))
            raise UserError(
                "อ่านข้อความอัตโนมัติไม่สำเร็จ\n- " + "\n- ".join(errors)
                + "\n\nกรุณาลองปรับแสง/มุมภาพ หรือเลือกโหมด 'กรอกเอง' แล้วพิมพ์ข้อความ"
            )

        return {
            "text": self._run_engine(engine, image_b64, raw, mimetype, language).strip(),
            "engine": engine,
        }

    # ------------------------------------------------------------------
    # Engine dispatch
    # ------------------------------------------------------------------
    @api.model
    def _run_engine(self, engine, image_b64, raw, mimetype, language):
        if engine == "ollama":
            return self._extract_with_vision(image_b64, mimetype, language)
        if engine == "tesseract":
            return self._extract_with_tesseract(raw, mimetype, language)
        raise UserError("ไม่รู้จักตัวอ่านข้อความ '%s'" % engine)

    # ------------------------------------------------------------------
    # Ollama / OpenAI-compatible vision
    # ------------------------------------------------------------------
    @api.model
    def _extract_with_vision(self, image_b64, mimetype, language):
        from odoo.addons.od19_ai_assistant.lib.client import AiClientError, chat_completion

        cfg = self._get_vision_config()
        if not cfg["base_url"] or not cfg["model"]:
            raise UserError(
                "ยังไม่ได้ตั้งค่าโมเดล Vision สำหรับ OCR "
                "(ตั้งค่าได้ที่ การตั้งค่า › ทั่วไป › สแกนเอกสาร)"
            )
        if mimetype not in IMAGE_MIMETYPES:
            raise UserError("Vision OCR รองรับเฉพาะไฟล์ภาพ (ไม่รองรับ %s)" % mimetype)

        lang_hint = ""
        if language == "th":
            lang_hint = " เอกสารนี้เป็นภาษาไทยเป็นหลัก"
        elif language == "en":
            lang_hint = " The document is mainly in English."

        messages = [
            {"role": "system", "content": VISION_PROMPT + lang_hint},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "ถอดข้อความทั้งหมดจากภาพนี้"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:%s;base64,%s" % (mimetype, image_b64)},
                    },
                ],
            },
        ]
        try:
            result = chat_completion(
                cfg["base_url"],
                cfg["model"],
                messages,
                api_key=cfg["api_key"],
                timeout=cfg["timeout"],
                temperature=0,
            )
        except AiClientError as exc:
            raise UserError("Ollama Vision อ่านไม่สำเร็จ: %s" % exc) from exc
        return self._clean_ocr_output(result)

    # ------------------------------------------------------------------
    # Tesseract (pytesseract if present, otherwise the CLI)
    # ------------------------------------------------------------------
    @api.model
    def _extract_with_tesseract(self, raw, mimetype, language):
        if not self.engine_available("tesseract"):
            raise UserError("ไม่พบโปรแกรม Tesseract ในเครื่อง")
        lang = self._tesseract_lang(language)
        suffix = self._suffix_for(mimetype)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            try:
                import pytesseract  # noqa: F401
                from PIL import Image

                with Image.open(tmp_path) as img:
                    text = pytesseract.image_to_string(img, lang=lang)
                return self._clean_ocr_output(text)
            except ImportError:
                return self._clean_ocr_output(self._tesseract_cli(tmp_path, lang))
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @api.model
    def _tesseract_cli(self, path, lang):
        result = subprocess.run(
            [self._tesseract_path(), path, "stdout", "-l", lang],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or b"").decode("utf-8", "replace").strip()
            raise UserError("Tesseract ทำงานไม่สำเร็จ: %s" % (message or "unknown error"))
        return result.stdout.decode("utf-8", "replace")

    # ------------------------------------------------------------------
    # PDF fallback (pdfminer.six ships with Odoo)
    # ------------------------------------------------------------------
    @api.model
    def _extract_pdf(self, raw):
        try:
            from pdfminer.high_level import extract_text
        except ImportError as exc:
            raise UserError(
                "ยังไม่ได้ติดตั้ง pdfminer.six จึงอ่านไฟล์ PDF ไม่ได้ "
                "กรุณาสแกนเป็นภาพหรือพิมพ์ข้อความเอง"
            ) from exc
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            return self._clean_ocr_output(extract_text(tmp_path) or "")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _guess_mimetype(self, filename):
        _base, ext = os.path.splitext((filename or "").lower())
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
        }.get(ext, "image/jpeg")

    @api.model
    def _suffix_for(self, mimetype):
        return {
            "image/png": ".png",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/gif": ".gif",
        }.get(mimetype, ".jpg")

    @api.model
    def _is_pdf(self, mimetype, filename):
        return mimetype == "application/pdf" or (filename or "").lower().endswith(".pdf")

    @api.model
    def _clean_ocr_output(self, text):
        """Trim noise LLMs sometimes add around the extracted text."""
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        # Drop a single surrounding pair of code fences if present.
        fence = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        return text
