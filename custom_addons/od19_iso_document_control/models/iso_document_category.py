# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IsoDocumentCategory(models.Model):
    _name = "od19.iso.document.category"
    _description = "ISO Document Category"
    _order = "prefix"

    name = fields.Char(string="ประเภทเอกสาร", required=True)
    prefix = fields.Char(
        string="คำนำหน้า",
        required=True,
        help="คำนำหน้ารหัสเอกสาร เช่น FM, PM, WI, REC, MANUAL",
    )
    use_sequence = fields.Boolean(
        string="ใช้เลขคุม",
        default=True,
        help="เปิด = สร้างรหัสอัตโนมัติ (คำนำหน้า-แผนก-ลำดับ) "
        "ปิด = ไม่สร้างรหัสอัตโนมัติ (เช่น บันทึก/คู่มือระบบ/นโยบาย) "
        "โดยยังใช้คำนำหน้าได้ในภายหลังหากเปิดกลับ",
    )
    description = fields.Text(string="คำอธิบาย")
    active = fields.Boolean(string="ใช้งาน", default=True)
