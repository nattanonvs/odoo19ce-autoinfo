# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .od19_iso_distribution_list import COPY_TYPE

DRAFT = "draft"
REVIEW = "review"
APPROVED = "approved"
PRINTED = "printed"
CANCELLED = "cancelled"

REQUEST_STATE = [
    (DRAFT, "ฉบับร่าง"),
    (REVIEW, "รออนุมัติ"),
    (APPROVED, "อนุมัติแล้ว"),
    (PRINTED, "พิมพ์แล้ว"),
    (CANCELLED, "ยกเลิก"),
]

NEW_PRINT = "new_print"
REPRINT = "reprint"
REPLACE_REVISION = "replace_revision"

REQUEST_TYPE = [
    (NEW_PRINT, "พิมพ์ใหม่"),
    (REPRINT, "พิมพ์ซ้ำ"),
    (REPLACE_REVISION, "พิมพ์แทน (เปลี่ยน revision)"),
]


class Od19IsoPrintRequest(models.Model):
    """ใบขอพิมพ์ (PDR — Print/Distribution Request)."""

    _name = "od19.iso.print.request"
    _description = "ISO Print Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="เลขที่ใบขอพิมพ์",
        default="/",
        copy=False,
        readonly=True,
        help="รูปแบบ PRN{yy}-{NNN} เช่น PRN26-001",
    )
    document_id = fields.Many2one(
        "od19.iso.document",
        string="เอกสาร",
        required=True,
        ondelete="cascade",
    )
    revision = fields.Char(
        string="Revision (snapshot)",
        help="revision ของเอกสารที่ขอพิมพ์",
    )
    request_type = fields.Selection(
        REQUEST_TYPE, string="ประเภทคำขอ", default=NEW_PRINT, required=True
    )
    copies_count = fields.Integer(string="จำนวนสำเนา", default=1, required=True)
    copy_type = fields.Selection(
        COPY_TYPE, string="ประเภทสำเนา", default="controlled", required=True
    )
    distribution_list_id = fields.Many2one(
        "od19.iso.distribution.list",
        string="ทะเบียนแจกจ่าย",
        ondelete="set null",
    )
    requester_id = fields.Many2one(
        "res.users",
        string="ผู้ขอ",
        default=lambda self: self.env.user,
        required=True,
    )
    state = fields.Selection(
        REQUEST_STATE, string="สถานะ", default=DRAFT, required=True, tracking=True
    )
    printed_by_id = fields.Many2one("res.users", string="ผู้พิมพ์ (DCC)")
    print_date = fields.Datetime(string="เวลาพิมพ์จริง")
    copy_ids = fields.One2many(
        "od19.iso.print.copy", "print_request_id", string="สำเนาที่พิมพ์"
    )
    copy_count = fields.Integer(string="จำนวนสำเนาที่สร้าง", compute="_compute_copy_count")
    note = fields.Text(string="หมายเหตุ")
    company_id = fields.Many2one(
        "res.company", string="บริษัท", default=lambda self: self.env.company
    )
    effective_applied = fields.Boolean(
        string="ประมวลผลการอนุมัติแล้ว", default=False, copy=False
    )

    @api.depends("copy_ids")
    def _compute_copy_count(self):
        for rec in self:
            rec.copy_count = len(rec.copy_ids)

    # ------------------------------------------------------------------
    # Numbering
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self._generate_name()
            if vals.get("document_id") and not vals.get("revision"):
                document = self.env["od19.iso.document"].browse(
                    vals["document_id"]
                )
                vals["revision"] = document.revision
        return super().create(vals_list)

    @api.model
    def _generate_name(self):
        """สร้างเลขที่ PRN{yy}-{NNN} จาก ir.sequence od19.iso.print.request."""
        year2 = fields.Date.today().strftime("%y")
        sequence = self.env.ref(
            "od19_iso_print_control.seq_iso_print_request",
            raise_if_not_found=False,
        )
        number = sequence.next_by_id() if sequence else "001"
        try:
            number = "%03d" % int(number)
        except (TypeError, ValueError):
            number = str(number)
        return "PRN%s-%s" % (year2, number)

    # ------------------------------------------------------------------
    # Lifecycle actions
    # ------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != DRAFT:
                raise UserError(_("ส่งอนุมัติได้เฉพาะใบขอพิมพ์ที่เป็นฉบับร่าง"))
            if rec.copies_count <= 0:
                raise UserError(_("จำนวนสำเนาต้องมากกว่า 0"))
            rec.state = REVIEW
            rec.message_post(body=_("ส่งขออนุมัติพิมพ์ %s สำเนา") % rec.copies_count)

    def action_approve(self):
        for rec in self:
            if rec.state != REVIEW:
                raise UserError(_("อนุมัติได้เฉพาะใบขอพิมพ์ที่รออนุมัติ"))
            rec._apply_approval_effect()
            rec.state = APPROVED
            rec.message_post(
                body=_("อนุมัติการพิมพ์ %s สำเนา") % rec.copies_count
            )

    def action_mark_printed(self):
        for rec in self:
            if rec.state != APPROVED:
                raise UserError(_("บันทึกการพิมพ์ได้เฉพาะใบที่อนุมัติแล้ว"))
            rec.state = PRINTED
            rec.printed_by_id = self.env.user
            rec.print_date = fields.Datetime.now()
            rec.message_post(
                body=_("พิมพ์เอกสารจริงโดย %s") % self.env.user.name
            )

    def action_cancel(self):
        for rec in self:
            if rec.state == PRINTED:
                raise UserError(_("ไม่สามารถยกเลิกใบขอพิมพ์ที่พิมพ์แล้ว"))
            rec.state = CANCELLED
            rec.message_post(body=_("ยกเลิกใบขอพิมพ์"))

    def action_reset_draft(self):
        for rec in self:
            rec.state = DRAFT
            rec.effective_applied = False

    # ------------------------------------------------------------------
    # G1 core: generate copies when approved
    # ------------------------------------------------------------------
    def _apply_approval_effect(self):
        """สร้าง print.copy ``copies_count`` ใบ (idempotent ผ่าน effective_applied)."""
        for rec in self:
            if rec.effective_applied:
                continue
            rec._generate_copies()
            rec.effective_applied = True

    def _generate_copies(self):
        self.ensure_one()
        copy_model = self.env["od19.iso.print.copy"]
        for _index in range(self.copies_count):
            copy_model.create({
                "print_request_id": self.id,
                "document_id": self.document_id.id,
                "copy_type": self.copy_type,
            })
        self.message_post(
            body=_("สร้างสำเนาควบคุม %s ใบสำหรับพิมพ์") % self.copies_count
        )
        return True
