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
    od19_scan_server_compress_enabled = fields.Boolean(
        string="บีบอัดภาพฝั่งเซิร์ฟเวอร์ (ชั้นที่ 2)",
        config_parameter="od19_scan.server_compress_enabled",
        default=True,
        help="บีบอัดภาพอัตโนมัติบนเซิร์ฟเวอร์ก่อนบันทึก ใช้กับไฟล์ภาพที่อัปโหลด"
        "จากทุกช่องทาง (ต่อจากการบีบอัดในเบราว์เซอร์ชั้นที่ 1) "
        "ไฟล์ที่ไม่ใช่ภาพหรือไฟล์เล็กอยู่แล้วจะไม่ถูกแตะ",
    )
    od19_scan_server_max_px = fields.Integer(
        string="ขนาดภาพสูงสุด (พิกเซล)",
        config_parameter="od19_scan.server_max_px",
        default=1600,
        help="ความยาวด้านที่ยาวที่สุดของภาพหลังบีบอัด (พิกเซล). ใส่ 0 เพื่อปิดการย่อ",
    )
    od19_scan_server_quality = fields.Integer(
        string="คุณภาพ JPEG (%)",
        config_parameter="od19_scan.server_quality",
        default=78,
        help="คุณภาพการเข้ารหัส JPEG (1-95) ยิ่งต่ำไฟล์ยิ่งเล็ก (มีผลกับ JPEG เท่านั้น)",
    )
