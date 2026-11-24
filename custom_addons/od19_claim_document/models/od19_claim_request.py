# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .od19_claim_form import CLAIM_TYPE_SELECTION


STATE_SELECTION = [
    ("draft", "ฉบับร่าง"),
    ("submitted", "ยื่นเรื่องแล้ว"),
    ("approved", "อนุมัติ"),
    ("closed", "ปิดเรื่อง"),
    ("cancelled", "ยกเลิก"),
]


class Od19ClaimRequest(models.Model):
    _name = "od19.claim.request"
    _description = "แฟ้มเรื่องเรียกร้อง/คำขอ"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char("เลขที่เรื่อง", default="/", readonly=True, copy=False)
    claim_type = fields.Selection(
        CLAIM_TYPE_SELECTION, "ชนิดเรื่องเรียกร้อง", required=True,
        tracking=True, index=True,
    )
    subject = fields.Char("เรื่อง", required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", "คู่ค้า/ผู้เกี่ยวข้อง")
    department_id = fields.Many2one("hr.department", "แผนก")
    user_id = fields.Many2one(
        "res.users", "ผู้รับผิดชอบ", default=lambda self: self.env.uid, tracking=True,
    )
    request_date = fields.Date(
        "วันที่ยื่นเรื่อง", default=fields.Date.context_today, required=True,
    )
    description = fields.Text("รายละเอียด")
    state = fields.Selection(
        STATE_SELECTION, "สถานะ", default="draft", tracking=True, index=True,
    )

    form_id = fields.Many2one("od19.claim.form", "แบบฟอร์มที่ใช้")
    category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", ondelete="restrict",
    )
    retention_policy_id = fields.Many2one(
        "od19.document.retention.policy", "นโยบายอายุ",
    )
    legal_hold = fields.Boolean("ห้ามทำลาย")
    source_ref = fields.Char("เลขอ้างอิงเรื่องต้นทาง")

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "od19_claim_request_attachment_rel",
        "claim_request_id",
        "attachment_id",
        "ไฟล์แนบ/หลักฐาน",
    )
    attachment_count = fields.Integer(
        "จำนวนไฟล์แนบ", compute="_compute_attachment_count",
    )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.claim.request") or "/"
                )
        return super().create(vals_list)

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def action_print_form(self):
        """พิมพ์แบบฟอร์มของเรื่องนี้ (บันทึกประวัติการพิมพ์) เพื่อเก็บเป็น hard copy"""
        self.ensure_one()
        if not self.form_id:
            raise UserError(_("ยังไม่ได้ระบุแบบฟอร์มสำหรับเรื่องนี้"))
        return self.form_id.action_print_form()
