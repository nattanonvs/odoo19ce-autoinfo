# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    # หมายเหตุ: ฟิลด์ code ถูกประกาศในโมดูลเลขเอกสารอื่นของโปรเจกต์ด้วย
    # (od19_delivery_label / od19_purchase_document_sequence / od19_iso_document_control)
    # การประกาศซ้ำที่นี่ทำให้ Layer 1 ใช้งาน od19_department_code ได้
    # แม้ติดตั้งก่อนโมดูลธุรกิจเหล่านั้น
    code = fields.Char(
        string="Department Code",
        copy=False,
        help="รหัสย่อของแผนก ใช้แสดงบนหน้าผู้ใช้และอ้างอิงขอบเขตข้อมูล",
    )
    od19_member_user_ids = fields.One2many(
        "res.users",
        "od19_department_id",
        string="Scoped Users",
        help="ผู้ใช้ที่ถูกกำหนดขอบเขตข้อมูลตามแผนกนี้",
    )
