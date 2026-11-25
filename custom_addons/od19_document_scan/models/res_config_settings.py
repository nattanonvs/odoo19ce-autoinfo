# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models

from .od19_ocr_service import ENGINE_SELECTION


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_scan_ocr_engine = fields.Selection(
        ENGINE_SELECTION,
        string="ตัวอ่านข้อความเริ่มต้น (OCR)",
        config_parameter="od19_scan.ocr_engine",
        default="auto",
        help="ตัวอ่านที่ใช้เมื่อผู้ใช้ไม่ระบุ: Ollama Vision เป็นหลัก "
        "แล้ว fallback ไป Tesseract อัตโนมัติ",
    )
    od19_scan_vision_model = fields.Char(
        string="โมเดล Vision สำหรับ OCR",
        config_parameter="od19_scan.vision_model",
        help="ชื่อโมเดลที่รองรับการอ่านภาพ เช่น qwen2.5vl:7b, llama3.2-vision, "
        "minicpm-v (เว้นว่างเพื่อใช้โมเดล AI หลักของระบบ)",
    )
    od19_scan_tesseract_lang = fields.Char(
        string="ภาษา Tesseract",
        config_parameter="od19_scan.tesseract_lang",
        help="รหัสภาษาแบบ Tesseract เช่น tha+eng (ไทย+อังกฤษ), eng",
    )
