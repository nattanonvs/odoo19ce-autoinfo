# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


CLAIM_TYPE_SELECTION = [
    ("warranty", "เคลมประกัน/หลังการขาย"),
    ("return", "คืนสินค้า/เสียหายขนส่ง"),
    ("supplier", "เรียกร้องผู้ขาย"),
    ("insurance", "เรียกร้องประกันภัย"),
    ("billing", "ขอเปิดบิล"),
    ("purchase", "ขออนุมัติจัดซื้อ"),
    ("internal", "คำขอภายใน/ไอที"),
    ("other", "อื่น ๆ"),
]


class Od19ClaimForm(models.Model):
    _name = "od19.claim.form"
    _description = "ทะเบียนแบบฟอร์มเรื่องเรียกร้อง"
    _order = "code, revision desc"

    name = fields.Char("ชื่อแบบฟอร์ม", required=True)
    code = fields.Char("รหัสแบบฟอร์ม", required=True)
    revision = fields.Char("ครั้งที่แก้ไข", default="00", required=True)
    claim_type = fields.Selection(
        CLAIM_TYPE_SELECTION, "ชนิดเรื่องเรียกร้อง", required=True, index=True,
    )
    effective_date = fields.Date("วันที่มีผลใช้")
    owner_department_id = fields.Many2one("hr.department", "หน่วยงานเจ้าของ")
    category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", ondelete="restrict",
    )
    template_attachment_id = fields.Many2one(
        "ir.attachment", "ไฟล์แบบฟอร์มต้นแบบ", ondelete="restrict",
        help="ไฟล์ที่ใช้อัปโหลดไว้ในระบบ เพื่อพิมพ์ออกมาเก็บเป็นหลักฐาน hard copy",
    )
    note = fields.Text("หมายเหตุ")
    active = fields.Boolean(default=True)
    print_ids = fields.One2many(
        "od19.claim.form.print", "form_id", "ประวัติการพิมพ์",
    )
    print_count = fields.Integer(
        "จำนวนครั้งที่พิมพ์", compute="_compute_print_count",
    )

    _code_revision_uniq = models.Constraint(
        "UNIQUE(code, revision)", "รหัสแบบฟอร์ม + ครั้งที่แก้ไข ต้องไม่ซ้ำ",
    )

    @api.depends("print_ids")
    def _compute_print_count(self):
        for form in self:
            form.print_count = len(form.print_ids)

    def action_print_form(self):
        """พิมพ์แบบฟอร์ม: บันทึกประวัติการพิมพ์ แล้วเปิดไฟล์ให้พิมพ์เป็น hard copy"""
        self.ensure_one()
        if not self.template_attachment_id:
            raise UserError(_("ยังไม่มีไฟล์แบบฟอร์มต้นแบบสำหรับพิมพ์"))
        self.env["od19.claim.form.print"].create({
            "form_id": self.id,
            "printed_by_id": self.env.uid,
            "printed_at": fields.Datetime.now(),
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.template_attachment_id.id}?download=false",
            "target": "new",
        }


class Od19ClaimFormPrint(models.Model):
    _name = "od19.claim.form.print"
    _description = "ประวัติการพิมพ์แบบฟอร์มเรื่องเรียกร้อง"
    _order = "printed_at desc, id desc"

    form_id = fields.Many2one(
        "od19.claim.form", "แบบฟอร์ม", required=True, ondelete="cascade", index=True,
    )
    printed_by_id = fields.Many2one(
        "res.users", "พิมพ์โดย", default=lambda self: self.env.uid, required=True,
    )
    printed_at = fields.Datetime(
        "พิมพ์เมื่อ", default=fields.Datetime.now, required=True,
    )
    copy_count = fields.Integer("จำนวนชุด", default=1, required=True)
    note = fields.Char("หมายเหตุ")
