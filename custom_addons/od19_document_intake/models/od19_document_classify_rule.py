# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models

TARGET_SELECTION = [
    ("filename", "ชื่อไฟล์"),
    ("text", "ข้อความในไฟล์"),
    ("partner", "ชื่อคู่ค้า"),
]


class Od19DocumentClassifyRule(models.Model):
    _name = "od19.document.classify.rule"
    _description = "กฎจัดหมวดเอกสารอัตโนมัติ"
    _order = "sequence, id"

    name = fields.Char("ชื่อกฎ", required=True)
    sequence = fields.Integer(default=10)
    target = fields.Selection(TARGET_SELECTION, "ตรวจจาก", required=True, default="filename")
    pattern = fields.Char(
        "คำ/รูปแบบ", required=True,
        help="ข้อความ (ไม่สนตัวพิมพ์) — ใช้ find ในเป้าหมายที่เลือก ไม่ใช้ regex",
    )
    category_id = fields.Many2one(
        "od19.document.category", "หมวดที่ได้", required=True, ondelete="cascade",
    )
    partner_id = fields.Many2one("res.partner", "คู่ค้าที่ได้", ondelete="set null")
    active = fields.Boolean(default=True)
