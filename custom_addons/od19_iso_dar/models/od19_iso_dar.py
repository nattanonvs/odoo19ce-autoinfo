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
    ("new", "ออกเอกสารใหม่ (NDR)"),
    ("revise", "แก้ไข / เพิ่ม Revision (EDR)"),
    ("obsolete", "ยกเลิก / เลิกใช้ (CDR)"),
    ("copy_controlled", "ขอสำเนาควบคุม"),
    ("copy_uncontrolled", "ขอสำเนาไม่ควบคุม"),
    ("change_distribution", "เปลี่ยนทะเบียนแจกจ่าย (CDL)"),
    ("print", "ขอพิมพ์เอกสาร (PDR)"),
    ("broad_distribution", "แจกจ่ายวงกว้าง (BDR)"),
    ("new_with_print", "ออกเอกสารใหม่ + พิมพ์ (NDRP)"),
    ("revise_with_print", "แก้ไข + พิมพ์ (EDRP)"),
    ("other", "อื่น ๆ"),
]

# ประเภทที่ต้องอ้างอิงเอกสารเดิม
DOCUMENT_REQUIRED_TYPES = (
    "revise",
    "obsolete",
    "copy_controlled",
    "copy_uncontrolled",
    "change_distribution",
    "print",
    "broad_distribution",
    "revise_with_print",
)

# ประเภทที่ต้องระบุจำนวนสำเนาที่พิมพ์
PRINT_REQUIRED_TYPES = ("print", "new_with_print", "revise_with_print")

PRINT_SCOPE = [
    ("controlled", "สำเนาควบคุม (Controlled)"),
    ("uncontrolled", "สำเนาไม่ควบคุม (Uncontrolled)"),
]


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
    # Print / distribution (WP1)
    # ------------------------------------------------------------------
    print_request_id = fields.Many2one(
        "od19.iso.print.request",
        string="ใบขอพิมพ์ที่สร้าง",
        readonly=True,
        copy=False,
        help="ใบขอพิมพ์ที่สร้างอัตโนมัติจากคำขอนี้ (print/new_with_print/revise_with_print/broad_distribution)",
    )
    distribution_list_id = fields.Many2one(
        "od19.iso.distribution.list",
        string="ทะเบียนแจกจ่ายอ้างอิง",
        help="ทะเบียนแจกจ่ายที่เลือก/อ้างอิงสำหรับคำขอเปลี่ยนหรือแจกจ่าย",
    )
    target_holder_ids = fields.Many2many(
        "res.users",
        string="ผู้รับเป้าหมาย",
        help="ผู้รับปลายทางสำหรับการแจกจ่ายวงกว้าง (BDR)",
    )
    copies_count = fields.Integer(
        string="จำนวนสำเนาที่ขอพิมพ์",
        default=1,
        help="จำนวนสำเนาที่ต้องพิมพ์ (บังคับเมื่อ type ∈ print/new_with_print/revise_with_print)",
    )
    print_scope = fields.Selection(
        PRINT_SCOPE,
        string="ขอบเขตการพิมพ์",
        default="controlled",
        help="ขอบเขตสำเนาที่พิมพ์ (controlled/uncontrolled)",
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
    @api.constrains("request_type", "document_id", "copies_count")
    def _check_document_required(self):
        for dar in self:
            if dar.request_type in DOCUMENT_REQUIRED_TYPES and not dar.document_id:
                raise UserError(
                    _("ประเภทคำขอ '%s' ต้องเลือกเอกสารอ้างอิงก่อนบันทึก")
                    % dict(REQUEST_TYPE)[dar.request_type]
                )
            if dar.request_type in PRINT_REQUIRED_TYPES and (dar.copies_count or 0) <= 0:
                raise UserError(
                    _("ประเภทคำขอ '%s' ต้องระบุจำนวนสำเนาที่ขอพิมพ์มากกว่า 0")
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
        ทำงานด้วยสิทธิ์ระบบ (sudo) เพราะเป็นผลอัตโนมัติหลังอนุมัติ
        ผู้อนุมัติไม่จำเป็นต้องมีสิทธิ์จัดการทะเบียนพิมพ์/แจกจ่ายเอง
        """
        for dar in self.sudo():
            if dar.effect_applied:
                continue
            rtype = dar.request_type
            if rtype == "revise" and dar.document_id:
                dar.document_id.action_new_revision_keep_approved()
            elif rtype == "revise_with_print" and dar.document_id:
                dar.document_id.action_new_revision_keep_approved()
                dar._create_print_request()
            elif rtype == "obsolete" and dar.document_id:
                if dar.document_id.status == "approved":
                    dar.document_id.action_mark_obsolete()
                dar._recall_pending_copies()
            elif rtype in ("copy_controlled", "copy_uncontrolled"):
                copy_type = (
                    "controlled"
                    if rtype == "copy_controlled"
                    else "uncontrolled"
                )
                self.env["od19.iso.dar.copy.record"].create({
                    "dar_id": dar.id,
                    "copy_type": copy_type,
                    "issued_date": fields.Date.today(),
                })
            elif rtype == "change_distribution" and dar.document_id:
                dar._create_distribution_revision()
            elif rtype == "print" and dar.document_id:
                dar._create_print_request()
            elif rtype == "broad_distribution" and dar.document_id:
                dar._create_broad_distribution()
            # 'new' / 'new_with_print' -> ใช้ wizard สร้างเอกสาร (new_with_print จะสร้างใบพิมพ์ต่อ)
            # 'other' -> ไม่มีผลอัตโนมัติ
            dar.effect_applied = True

    # ------------------------------------------------------------------
    # Print / distribution helpers (WP1 §3.4)
    # ------------------------------------------------------------------
    def _create_print_request(self, copy_type=None):
        """สร้างใบขอพิมพ์ (od19.iso.print.request) จาก DAR และส่งขออนุมัติทันที."""
        self.ensure_one()
        if self.print_request_id:
            return self.print_request_id
        request = self.env["od19.iso.print.request"].create({
            "document_id": self.document_id.id,
            "revision": self.document_id.revision,
            "request_type": "new_print",
            "copies_count": self.copies_count or 1,
            "copy_type": copy_type or self.print_scope or "controlled",
            "distribution_list_id": self.distribution_list_id.id or False,
            "requester_id": self.requester_id.id or self.env.user.id,
            "note": _("สร้างอัตโนมัติจากใบ DAR %s") % self.name,
        })
        request.action_submit()
        self.print_request_id = request.id
        self.message_post(
            body=_("สร้างใบขอพิมพ์ %s (%s สำเนา) จากคำขอนี้")
            % (request.name, request.copies_count)
        )
        return request

    def _recall_pending_copies(self):
        """ยกเลิก/เรียกคืนสำเนาที่ค้างทั้งหมดของเอกสาร (เมื่อเอกสารถูกเลิกใช้)."""
        for dar in self:
            if not dar.document_id:
                continue
            copies = self.env["od19.iso.print.copy"].search([
                ("document_id", "=", dar.document_id.id),
                ("state", "in", ("reserved", "issued")),
            ])
            (copies.filtered(lambda c: c.state == "issued")).write(
                {"state": "returned", "return_date": fields.Date.today()}
            )
            (copies.filtered(lambda c: c.state == "reserved")).write(
                {"state": "destroyed"}
            )

    def _create_distribution_revision(self):
        """สร้างทะเบียนแจกจ่ายเวอร์ชันใหม่ (snapshot revision) และ supersede ของเดิม."""
        for dar in self:
            document = dar.document_id
            source = dar.distribution_list_id or self.env[
                "od19.iso.distribution.list"
            ].search([
                ("document_id", "=", document.id),
                ("state", "=", "active"),
            ], limit=1)
            line_vals = [
                (0, 0, {
                    "recipient_id": line.recipient_id.id,
                    "holder_name": line.holder_name,
                    "department_id": line.department_id.id,
                    "copies_required": line.copies_required,
                    "copy_type": line.copy_type,
                    "note": line.note,
                })
                for line in source.line_ids
            ]
            new_list = self.env["od19.iso.distribution.list"].create({
                "document_id": document.id,
                "revision": document.revision,
                "line_ids": line_vals,
                "note": _("สร้างจากใบ DAR %s (เปลี่ยนทะเบียนแจกจ่าย)") % dar.name,
            })
            if new_list.line_ids:
                new_list.action_activate()
            dar.message_post(
                body=_("สร้างทะเบียนแจกจ่าย %s (Rev.%s) จากคำขอเปลี่ยนทะเบียน")
                % (new_list.name, new_list.revision or "-")
            )

    def _create_broad_distribution(self):
        """แจกจ่ายวงกว้าง: สร้าง distribution.line ให้ target_holder_ids + ใบพิมพ์ uncontrolled."""
        for dar in self:
            document = dar.document_id
            line_vals = [
                (0, 0, {
                    "recipient_id": user.id,
                    "copies_required": 1,
                    "copy_type": "uncontrolled",
                })
                for user in dar.target_holder_ids
            ]
            new_list = self.env["od19.iso.distribution.list"].create({
                "document_id": document.id,
                "revision": document.revision,
                "line_ids": line_vals,
                "note": _("แจกจ่ายวงกว้างจากใบ DAR %s") % dar.name,
            })
            if new_list.line_ids:
                new_list.action_activate()
            if (dar.copies_count or 0) > 0:
                dar._create_print_request(copy_type="uncontrolled")

    def action_view_print_request(self):
        """เปิดใบขอพิมพ์ที่สร้างจากคำขอนี้."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "od19_iso_print_control.action_od19_iso_print_request"
        )
        action["res_id"] = self.print_request_id.id
        action["view_mode"] = "form"
        action["views"] = [(False, "form")]
        return action

    # ------------------------------------------------------------------
    # SLA reminder (Task T12)
    # ------------------------------------------------------------------
    SLA_DAYS = 5
    PENDING_STATES = (REVIEW, APPROVAL, FINAL_APPROVAL)

    @api.model
    def _cron_dar_sla_reminder(self):
        """แจ้งเตือนใบที่ค้างเกิน SLA (5 วัน) ในแต่ละขั้นที่รออนุมัติ."""
        deadline = fields.Datetime.subtract(
            fields.Datetime.now(), days=self.SLA_DAYS
        )
        pending = self.search([
            ("status", "in", self.PENDING_STATES),
            ("create_date", "<", deadline),
        ])
        for dar in pending:
            if dar.activity_ids:
                continue
            approver = (
                dar.reviewer_id
                or dar.approver_id
                or dar.final_approver_id
                or dar.requester_id
            )
            dar.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=(approver or self.env.user).id,
                summary=_("ใบ DAR ค้างเกิน %s วัน") % self.SLA_DAYS,
                note=_("ใบ %s รออนุมัติเกินกำหนด SLA") % dar.name,
            )
        return True
