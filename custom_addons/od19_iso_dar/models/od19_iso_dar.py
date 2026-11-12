# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Lifecycle statuses (4-level approval + terminal states)
DRAFT = "draft"
REVIEW = "review"
APPROVAL = "approval"
FINAL_APPROVAL = "final_approval"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"
CLOSED = "closed"

DAR_STATUS = [
    (DRAFT, "ร่าง"),
    (REVIEW, "รอตรวจทาน"),
    (APPROVAL, "รออนุมัติ"),
    (FINAL_APPROVAL, "รออนุมัติสุดท้าย"),
    (APPROVED, "อนุมัติแล้ว"),
    (REJECTED, "ถูกปฏิเสธ"),
    (CANCELLED, "ยกเลิก"),
    (CLOSED, "ปิด"),
]

REQUEST_TYPE = [
    ("new", "ออกเอกสารใหม่"),
    ("revise", "แก้ไข / เพิ่ม Revision"),
    ("obsolete", "ยกเลิก / เลิกใช้"),
    ("copy_controlled", "ขอสำเนาควบคุม"),
    ("copy_uncontrolled", "ขอสำเนาไม่ควบคุม"),
    ("other", "อื่น ๆ"),
]

# ประเภทที่ต้องอ้างอิงเอกสารเดิม
DOCUMENT_REQUIRED_TYPES = (
    "revise",
    "obsolete",
    "copy_controlled",
    "copy_uncontrolled",
)


class Od19IsoDar(models.Model):
    _name = "od19.iso.dar"
    _description = "ISO Document Action Request (DAR)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_name = "name"

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="เลขที่ DAR",
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
        help="รูปแบบ DC{ปี ค.ศ. 2 หลัก}-{ลำดับ 3 หลัก} เช่น DC26-001",
    )
    request_type = fields.Selection(
        REQUEST_TYPE,
        string="ประเภทคำขอ",
        required=True,
        default="new",
        tracking=True,
    )
    document_id = fields.Many2one(
        "od19.iso.document", string="เอกสารอ้างอิง", tracking=True
    )
    category_id = fields.Many2one(
        "od19.iso.document.category", string="ประเภทเอกสาร", tracking=True
    )
    department_id = fields.Many2one("hr.department", string="แผนก", tracking=True)
    standard_ids = fields.Many2many("od19.iso.standard", string="มาตรฐาน ISO")
    iso_clause = fields.Char(string="ข้อ ISO")
    reason = fields.Text(string="เหตุผล / ความจำเป็น")
    description = fields.Html(string="รายละเอียดคำขอ")

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    status = fields.Selection(
        DAR_STATUS,
        string="สถานะ",
        default=DRAFT,
        required=True,
        tracking=True,
        copy=False,
    )
    requester_id = fields.Many2one(
        "res.users",
        string="ผู้ขอ",
        default=lambda self: self.env.user,
        tracking=True,
    )
    reviewer_id = fields.Many2one("res.users", string="ผู้ตรวจทาน", tracking=True)
    approver_id = fields.Many2one("res.users", string="ผู้อนุมัติ", tracking=True)
    final_approver_id = fields.Many2one(
        "res.users", string="ผู้อนุมัติสุดท้าย", tracking=True
    )
    effective_date = fields.Date(string="วันที่มีผล", tracking=True)
    reject_reason = fields.Text(string="เหตุผลที่ถูกตีกลับ")
    effect_applied = fields.Boolean(
        string="ทำผลอัตโนมัติแล้ว",
        default=False,
        copy=False,
        readonly=True,
        help="กันการทำผลหลังอนุมัติซ้ำ (idempotent guard)",
    )

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    change_line_ids = fields.One2many(
        "od19.iso.dar.change.line", "dar_id", string="รายการเปลี่ยนแปลง"
    )
    copy_record_ids = fields.One2many(
        "od19.iso.dar.copy.record", "dar_id", string="ทะเบียนสำเนา"
    )
    attachment_ids = fields.Many2many("ir.attachment", string="เอกสารแนบ")
    company_id = fields.Many2one(
        "res.company", string="บริษัท", default=lambda self: self.env.company
    )

    # ------------------------------------------------------------------
    # Create / numbering
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self._generate_dar_number()
        return super().create(vals_list)

    @api.model
    def _generate_dar_number(self):
        """สร้างเลขที่ DC{yy}-{NNN} จาก ir.sequence od19.iso.dar."""
        year2 = fields.Date.today().strftime("%y")
        sequence = self.env.ref("od19_iso_dar.seq_iso_dar", raise_if_not_found=False)
        number = sequence.next_by_id() if sequence else "001"
        try:
            number = "%03d" % int(number)
        except (TypeError, ValueError):
            number = str(number or "001").zfill(3)
        return "DC%s-%s" % (year2, number)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("request_type", "document_id")
    def _check_document_required(self):
        for dar in self:
            if dar.request_type in DOCUMENT_REQUIRED_TYPES and not dar.document_id:
                raise UserError(
                    _("ประเภทคำขอ '%s' ต้องเลือกเอกสารอ้างอิงก่อนบันทึก")
                    % dict(REQUEST_TYPE)[dar.request_type]
                )

    # ------------------------------------------------------------------
    # Approval helper (mirrors od19.iso.document._check_approval_role)
    # ------------------------------------------------------------------
    def _check_approval_role(self, expected_user_field):
        self.ensure_one()
        field = self._fields[expected_user_field]
        field_label = (
            field.string if isinstance(field.string, str) else expected_user_field
        )
        expected_user = self[expected_user_field]
        if not expected_user:
            raise UserError(
                _("ยังไม่ได้กำหนด %s กรุณาตั้งค่าก่อนดำเนินการ") % field_label
            )
        if self.env.user != expected_user and not self.env.user.has_group(
            "base.group_system"
        ):
            raise UserError(
                _("เฉพาะ %s เท่านั้นที่สามารถดำเนินการขั้นตอนนี้ได้")
                % expected_user.name
            )

    # ------------------------------------------------------------------
    # 4-level approval workflow
    # ------------------------------------------------------------------
    def action_submit_for_review(self):
        for dar in self:
            if dar.status != DRAFT:
                raise UserError(_("เฉพาะใบสถานะ 'ร่าง' เท่านั้นที่ส่งตรวจทานได้"))
            if not dar.reviewer_id:
                raise UserError(_("กรุณากำหนดผู้ตรวจทานก่อนส่งตรวจทาน"))
            dar.status = REVIEW
            dar.message_post(body=_("ส่งใบคำขอเพื่อตรวจทานโดย %s") % self.env.user.name)

    def action_review_approve(self):
        for dar in self:
            if dar.status != REVIEW:
                raise UserError(_("ใบนี้ไม่อยู่ในสถานะรอตรวจทาน"))
            dar._check_approval_role("reviewer_id")
            if not dar.approver_id:
                raise UserError(_("กรุณากำหนดผู้อนุมัติก่อนดำเนินการ"))
            dar.status = APPROVAL
            dar.message_post(body=_("ตรวจทานผ่านโดย %s") % self.env.user.name)

    def action_review_reject(self):
        for dar in self:
            if dar.status != REVIEW:
                raise UserError(_("ใบนี้ไม่อยู่ในสถานะรอตรวจทาน"))
            dar._check_approval_role("reviewer_id")
            dar.status = DRAFT
            dar.message_post(body=_("ตรวจทานไม่ผ่าน โดย %s ส่งกลับเป็นร่าง") % self.env.user.name)

    def action_approve(self):
        for dar in self:
            if dar.status != APPROVAL:
                raise UserError(_("ใบนี้ไม่อยู่ในสถานะรออนุมัติ"))
            dar._check_approval_role("approver_id")
            if not dar.final_approver_id:
                raise UserError(_("กรุณากำหนดผู้อนุมัติสุดท้ายก่อนดำเนินการ"))
            dar.status = FINAL_APPROVAL
            dar.message_post(body=_("อนุมัติโดย %s") % self.env.user.name)

    def action_approve_reject(self):
        for dar in self:
            if dar.status != APPROVAL:
                raise UserError(_("ใบนี้ไม่อยู่ในสถานะรออนุมัติ"))
            dar._check_approval_role("approver_id")
            dar.status = DRAFT
            dar.message_post(body=_("ไม่อนุมัติ โดย %s ส่งกลับเป็นร่าง") % self.env.user.name)

    def action_final_approve(self):
        for dar in self:
            if dar.status != FINAL_APPROVAL:
                raise UserError(_("ใบนี้ไม่อยู่ในสถานะรออนุมัติสุดท้าย"))
            dar._check_approval_role("final_approver_id")
            dar.status = APPROVED
            if not dar.effective_date:
                dar.effective_date = fields.Date.today()
            dar._apply_approval_effect()
            dar.message_post(body=_("อนุมัติเป็นทางการโดย %s") % self.env.user.name)

    def action_final_reject(self):
        for dar in self:
            if dar.status != FINAL_APPROVAL:
                raise UserError(_("ใบนี้ไม่อยู่ในสถานะรออนุมัติสุดท้าย"))
            dar._check_approval_role("final_approver_id")
            dar.status = DRAFT
            dar.message_post(body=_("ไม่อนุมัติขั้นสุดท้าย โดย %s ส่งกลับเป็นร่าง") % self.env.user.name)

    def action_cancel(self):
        for dar in self:
            if dar.status in (APPROVED, CANCELLED, CLOSED):
                raise UserError(_("ไม่สามารถยกเลิกใบที่อนุมัติแล้ว/ยกเลิกแล้ว/ปิดแล้ว"))
            dar.status = CANCELLED
            dar.message_post(body=_("ยกเลิกใบคำขอโดย %s") % self.env.user.name)

    def action_close(self):
        for dar in self:
            if dar.status != APPROVED:
                raise UserError(_("ปิดใบได้เฉพาะใบที่อนุมัติแล้วเท่านั้น"))
            dar.status = CLOSED
            dar.message_post(body=_("ปิดใบคำขอโดย %s") % self.env.user.name)

    def action_reset_to_draft(self):
        for dar in self:
            if dar.status in (APPROVED, CLOSED):
                raise UserError(_("ไม่สามารถดึงใบที่อนุมัติแล้วกลับเป็นร่างได้"))
            if self.env.user != dar.requester_id and not self.env.user.has_group(
                "base.group_system"
            ):
                raise UserError(_("เฉพาะผู้ขอเท่านั้นที่ดึงกลับเป็นร่างได้"))
            dar.status = DRAFT
            dar.message_post(body=_("ดึงกลับเป็นร่างโดย %s") % self.env.user.name)

    # ------------------------------------------------------------------
    # Post-approval effect (Task T10)
    # ------------------------------------------------------------------
    def _apply_approval_effect(self):
        """ทำผลอัตโนมัติหลังอนุมัติ ตาม request_type (idempotent).

        ทำงานครั้งเดียวต่อใบ — ป้องกันผลซ้ำด้วย ``effect_applied``
        """
        for dar in self:
            if dar.effect_applied:
                continue
            if dar.request_type == "revise" and dar.document_id:
                dar.document_id.action_new_revision_keep_approved()
            elif dar.request_type == "obsolete" and dar.document_id:
                if dar.document_id.status == "approved":
                    dar.document_id.action_mark_obsolete()
            elif dar.request_type in ("copy_controlled", "copy_uncontrolled"):
                copy_type = (
                    "controlled"
                    if dar.request_type == "copy_controlled"
                    else "uncontrolled"
                )
                self.env["od19.iso.dar.copy.record"].create({
                    "dar_id": dar.id,
                    "copy_type": copy_type,
                    "issued_date": fields.Date.today(),
                })
            # 'new' -> ใช้ wizard (Task T11) ; 'other' -> ไม่มีผลอัตโนมัติ
            dar.effect_applied = True
