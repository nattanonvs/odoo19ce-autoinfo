# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


# Document lifecycle statuses.
# 4-level approval: draft -> review -> approval -> final_approval -> approved
DRAFT = "draft"
REVIEW = "review"
APPROVAL = "approval"
FINAL_APPROVAL = "final_approval"
APPROVED = "approved"
REJECTED = "rejected"
OBSOLETE = "obsolete"

DOCUMENT_STATUS = [
    (DRAFT, "ร่าง"),
    (REVIEW, "รอตรวจทาน"),
    (APPROVAL, "รออนุมัติ"),
    (FINAL_APPROVAL, "รออนุมัติสุดท้าย"),
    (APPROVED, "อนุมัติแล้ว"),
    (REJECTED, "ถูกปฏิเสธ"),
    (OBSOLETE, "เลิกใช้"),
]

DATE_TYPE = [
    ("AD", "คริสต์ศักราช"),
    ("BE", "พุทธศักราช"),
]

DATE_FORMAT = [
    ("dd/MM/yyyy", "dd/MM/yyyy"),
    ("dd/MMM/yyyy", "dd/MMM/yyyy"),
    ("dd-MM-yyyy", "dd-MM-yyyy"),
    ("dd-MMM-yyyy", "dd-MMM-yyyy"),
    ("yyyy/MM/dd", "yyyy/MM/dd"),
]


class IsoDocument(models.Model):
    _name = "od19.iso.document"
    _description = "ISO Controlled Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code"
    _rec_name = "code"

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    code = fields.Char(
        string="รหัสเอกสาร",
        required=False,
        readonly=True,
        copy=False,
        tracking=True,
        help="รูปแบบ เช่น FM-PU-12, PROC-QA-01, WI-PU-03 "
        "(สร้างอัตโนมัติเมื่อบันทึกเอกสาร)",
    )
    document_title = fields.Char(
        string="ชื่อเอกสาร", required=True, tracking=True
    )
    category_id = fields.Many2one(
        "od19.iso.document.category",
        string="ประเภทเอกสาร",
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="แผนก",
        tracking=True,
        help="แผนกที่รับผิดชอบเอกสารนี้ "
        "ใช้กำหนดรหัสแผนกในรหัสเอกสาร",
    )
    department_code = fields.Char(
        string="รหัสแผนก",
        related="department_id.code",
        store=True,
        readonly=True,
        help="รหัสแผนกในรหัสเอกสาร เช่น PU, SA, QA, IA "
        "(อ้างอิงจากรหัสแผนก)",
    )
    standard_ids = fields.Many2many(
        "od19.iso.standard",
        string="มาตรฐาน ISO",
        tracking=True,
        help="เลือกมาตรฐานที่เอกสารนี้สอดคล้อง (ISO 9001, ISO 14001)",
    )
    iso_clause = fields.Char(
        string="ข้อ ISO",
        help="ข้อ/อนุประโยคของมาตรฐาน ISO ที่เกี่ยวข้อง เช่น 7.5, 8.6",
    )

    # ------------------------------------------------------------------
    # Revision control
    # ------------------------------------------------------------------
    revision = fields.Char(
        string="Revision",
        default="00",
        required=True,
        tracking=True,
        help="เลขที่แก้ไข เช่น 00, 01, 02",
    )
    effective_date = fields.Date(string="วันที่มีผล", tracking=True)
    review_date = fields.Date(
        string="วันที่ตรวจทานครั้งถัดไป", tracking=True
    )
    status = fields.Selection(
        DOCUMENT_STATUS,
        string="สถานะ",
        default=DRAFT,
        required=True,
        tracking=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Roles / 4-level approval
    # ------------------------------------------------------------------
    owner_id = fields.Many2one(
        "res.users", string="ผู้รับผิดชอบ", tracking=True
    )
    drafter_id = fields.Many2one(
        "res.users",
        string="ผู้จัดทำ",
        default=lambda self: self.env.user,
        tracking=True,
    )
    reviewer_id = fields.Many2one(
        "res.users", string="ผู้ตรวจทาน", tracking=True
    )
    approver_id = fields.Many2one(
        "res.users", string="ผู้อนุมัติ", tracking=True
    )
    final_approver_id = fields.Many2one(
        "res.users", string="ผู้อนุมัติสุดท้าย", tracking=True
    )

    # ------------------------------------------------------------------
    # Formatting / display options (carried over from dtr.report.base)
    # ------------------------------------------------------------------
    date_type = fields.Selection(
        DATE_TYPE, string="ระบบวันที่", default="AD", tracking=True
    )
    date_format = fields.Selection(
        DATE_FORMAT, string="รูปแบบวันที่", default="dd/MM/yyyy", tracking=True
    )
    allow_e_name = fields.Boolean(
        string="อนุญาตชื่ออิเล็กทรอนิกส์", default=True, tracking=True
    )
    allow_e_signature = fields.Boolean(
        string="อนุญาตลายมือชื่ออิเล็กทรอนิกส์", default=True, tracking=True
    )

    # ------------------------------------------------------------------
    # Attachments & revision history
    # ------------------------------------------------------------------
    document_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="ไฟล์เอกสาร",
        help="ไฟล์เอกสารที่ควบคุม",
    )
    revision_history_ids = fields.One2many(
        "od19.iso.document.revision",
        "document_id",
        string="ประวัติการแก้ไข",
    )
    active = fields.Boolean(string="ใช้งาน", default=True)

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    display_name = fields.Char(
        compute="_compute_display_name", store=True, string="ชื่อแสดงผล"
    )
    filename_pattern = fields.Char(
        compute="_compute_filename_pattern",
        string="รูปแบบชื่อไฟล์",
        help="ชื่อไฟล์ที่จะใช้เมื่อดาวน์โหลดเอกสาร",
    )

    @api.depends("code", "document_title", "revision")
    def _compute_display_name(self):
        for doc in self:
            doc.display_name = f"{doc.code} - {doc.document_title}"

    @api.depends("code", "document_title", "revision")
    def _compute_filename_pattern(self):
        """Return the filename used when downloading the controlled document.

        Format: {CODE}_{TITLE}_Rev.{REVISION}
        Example: FM-PU-12_ใบปะหน้าสินค้ารอส่ง_Rev.00.pdf
        """
        for doc in self:
            safe_title = (doc.document_title or "").strip()
            # Replace characters that are problematic in filenames.
            for ch in ['/', '\\', ':', '*', '?', '"', "<", ">", "|"]:
                safe_title = safe_title.replace(ch, "_")
            doc.filename_pattern = (
                f"{doc.code}_{safe_title}_Rev.{doc.revision or '00'}"
            )

    def _get_download_filename(self, extension="pdf"):
        """Return the full filename for download including extension."""
        self.ensure_one()
        ext = extension.lstrip(".")
        return f"{self.filename_pattern}.{ext}"

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("code")
    def _check_code_unique(self):
        for doc in self:
            if not doc.code:
                continue
            duplicates = self.search(
                [("code", "=", doc.code), ("id", "!=", doc.id)]
            )
            if duplicates:
                raise ValidationError(
                    _(
                        "รหัสเอกสาร '%(code)s' มีอยู่แล้วในระบบ",
                        code=doc.code,
                    )
                )

    @api.constrains("revision")
    def _check_revision_format(self):
        for doc in self:
            if doc.revision and not doc.revision.isdigit():
                raise ValidationError(
                    _("Revision ต้องเป็นตัวเลขเท่านั้น เช่น 00, 01, 02")
                )

    # ------------------------------------------------------------------
    # 4-level approval workflow
    # ------------------------------------------------------------------
    def _check_approval_role(self, expected_user_field):
        """Ensure the current user is the expected approver for this step."""
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

    def action_submit_for_review(self):
        """Drafter submits the document for review (step 1 -> 2)."""
        for doc in self:
            if doc.status != DRAFT:
                raise UserError(_("เฉพาะเอกสารสถานะ 'ร่าง' เท่านั้นที่สามารถส่งตรวจทานได้"))
            if not doc.reviewer_id:
                raise UserError(_("กรุณากำหนดผู้ตรวจทานก่อนส่งตรวจทาน"))
            doc.status = REVIEW
            doc.message_post(
                body=_("ส่งเอกสารเพื่อตรวจทานโดย %s") % self.env.user.name
            )

    def action_review_approve(self):
        """Reviewer approves and sends to approver (step 2 -> 3)."""
        for doc in self:
            if doc.status != REVIEW:
                raise UserError(_("เอกสารนี้ไม่อยู่ในสถานะรอตรวจทาน"))
            doc._check_approval_role("reviewer_id")
            if not doc.approver_id:
                raise UserError(_("กรุณากำหนดผู้อนุมัติก่อนดำเนินการ"))
            doc.status = APPROVAL
            doc.message_post(
                body=_("ตรวจทานผ่านโดย %s") % self.env.user.name
            )

    def action_review_reject(self):
        """Reviewer rejects the document back to draft."""
        for doc in self:
            if doc.status != REVIEW:
                raise UserError(_("เอกสารนี้ไม่อยู่ในสถานะรอตรวจทาน"))
            doc._check_approval_role("reviewer_id")
            doc.status = DRAFT
            doc.message_post(
                body=_("ตรวจทานไม่ผ่าน โดย %s ส่งกลับเป็นร่าง")
                % self.env.user.name
            )

    def action_approve(self):
        """Approver approves and sends to final approval (step 3 -> 4)."""
        for doc in self:
            if doc.status != APPROVAL:
                raise UserError(_("เอกสารนี้ไม่อยู่ในสถานะรออนุมัติ"))
            doc._check_approval_role("approver_id")
            if not doc.final_approver_id:
                raise UserError(_("กรุณากำหนดผู้อนุมัติสุดท้ายก่อนดำเนินการ"))
            doc.status = FINAL_APPROVAL
            doc.message_post(
                body=_("อนุมัติโดย %s") % self.env.user.name
            )

    def action_approve_reject(self):
        """Approver rejects the document back to review."""
        for doc in self:
            if doc.status != APPROVAL:
                raise UserError(_("เอกสารนี้ไม่อยู่ในสถานะรออนุมัติ"))
            doc._check_approval_role("approver_id")
            doc.status = REVIEW
            doc.message_post(
                body=_("อนุมัติไม่ผ่าน โดย %s ส่งกลับตรวจทาน")
                % self.env.user.name
            )

    def action_final_approve(self):
        """Final approver approves -> document is effective (step 4 -> approved)."""
        for doc in self:
            if doc.status != FINAL_APPROVAL:
                raise UserError(_("เอกสารนี้ไม่อยู่ในสถานะรออนุมัติสุดท้าย"))
            doc._check_approval_role("final_approver_id")
            # Create a revision history record.
            self.env["od19.iso.document.revision"].create(
                {
                    "document_id": doc.id,
                    "revision": doc.revision,
                    "effective_date": doc.effective_date,
                    "approved_by": self.env.user.id,
                    "note": _("อนุมัติเป็นทางการ"),
                }
            )
            doc.status = APPROVED
            if not doc.effective_date:
                doc.effective_date = fields.Date.today()
            doc.message_post(
                body=_("อนุมัติเป็นทางการโดย %s") % self.env.user.name
            )

    def action_final_reject(self):
        """Final approver rejects back to approval."""
        for doc in self:
            if doc.status != FINAL_APPROVAL:
                raise UserError(_("เอกสารนี้ไม่อยู่ในสถานะรออนุมัติสุดท้าย"))
            doc._check_approval_role("final_approver_id")
            doc.status = APPROVAL
            doc.message_post(
                body=_("อนุมัติไม่ผ่านขั้นสุดท้าย โดย %s ส่งกลับรออนุมัติ")
                % self.env.user.name
            )

    def action_new_revision(self):
        """Create a new revision from an approved document.

        Increments revision and resets status to draft for re-approval.
        """
        for doc in self:
            if doc.status not in (APPROVED, OBSOLETE):
                raise UserError(
                    _("สามารถสร้าง revision ใหม่ได้เฉพาะเอกสารที่อนุมัติแล้วหรือเลิกใช้เท่านั้น")
                )
            # Archive current revision history.
            self.env["od19.iso.document.revision"].create(
                {
                    "document_id": doc.id,
                    "revision": doc.revision,
                    "effective_date": doc.effective_date,
                    "note": _("Superseded by new revision"),
                }
            )
            new_rev = f"{int(doc.revision) + 1:02d}"
            doc.revision = new_rev
            doc.status = DRAFT
            doc.message_post(
                body=_("สร้าง revision ใหม่: Rev.%s") % new_rev
            )

    def action_mark_obsolete(self):
        """Mark the document as obsolete (เลิกใช้)."""
        for doc in self:
            if doc.status != APPROVED:
                raise UserError(
                    _("สามารถเลิกใช้ได้เฉพาะเอกสารที่อนุมัติแล้วเท่านั้น")
                )
            doc.status = OBSOLETE
            doc.active = False
            doc.message_post(
                body=_("เลิกใช้เอกสารโดย %s") % self.env.user.name
            )

    def action_reset_to_draft(self):
        """Allow the drafter/owner to pull back to draft from review/approval."""
        for doc in self:
            if doc.status in (APPROVED, OBSOLETE):
                raise UserError(
                    _("ไม่สามารถดึงเอกสารที่อนุมัติแล้วกลับเป็นร่างได้")
                )
            if self.env.user not in (
                doc.drafter_id,
                doc.owner_id,
            ) and not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _("เฉพาะผู้จัดทำหรือผู้รับผิดชอบเท่านั้นที่สามารถดึงกลับเป็นร่างได้")
                )
            doc.status = DRAFT
            doc.message_post(
                body=_("ดึงกลับเป็นร่างโดย %s") % self.env.user.name
            )

    # ------------------------------------------------------------------
    # Attachment handling: rename uploaded files to include document code
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = self._generate_document_code(vals)
        records = super().create(vals_list)
        records._rename_attachments()
        return records

    def _get_sequence_by_category(self, category):
        """Return the ir.sequence for the given document category prefix."""
        self.ensure_one()
        if not category:
            return False
        prefix = (category.prefix or "").strip().upper()
        seq_xml_id = "od19_iso_document_control.seq_iso_doc_%s" % prefix.lower()
        return self.env.ref(seq_xml_id, raise_if_not_found=False)

    def _generate_document_code(self, vals):
        """Generate the document code: {PREFIX}-{DEPT}-{NNN}.

        Falls back to '/' when no category is set.
        """
        category_id = vals.get("category_id")
        if not category_id:
            return "/"
        category = self.env["od19.iso.document.category"].browse(category_id)
        if not category:
            return "/"
        prefix = (category.prefix or "").strip().upper()
        if not prefix:
            return "/"
        # Determine department code.
        dept_code = ""
        dept_id = vals.get("department_id")
        if dept_id:
            dept = self.env["hr.department"].browse(dept_id)
            dept_code = (dept.code or "").strip().upper()
        if not dept_code:
            dept_code = "XX"
        sequence = self.env.ref(
            "od19_iso_document_control.seq_iso_doc_%s" % prefix.lower(),
            raise_if_not_found=False,
        )
        number = sequence.next_by_id() if sequence else "001"
        # Normalize number to 3 digits.
        try:
            number = "%03d" % int(number)
        except (TypeError, ValueError):
            number = str(number or "001").zfill(3)
        return "%s-%s-%s" % (prefix, dept_code, number)

    def write(self, vals):
        if "category_id" in vals or "department_id" in vals:
            for doc in self:
                current_code = doc.code or ""
                # A code generated before the department was known carries the
                # "XX" placeholder: regenerate it once the department is set.
                needs_code = (
                    not current_code
                    or current_code == "/"
                    or "-XX-" in current_code
                )
                if needs_code:
                    new_vals = dict(vals)
                    new_vals["category_id"] = vals.get(
                        "category_id", doc.category_id.id
                    )
                    new_vals["department_id"] = vals.get(
                        "department_id", doc.department_id.id
                    )
                    doc.code = doc._generate_document_code(new_vals)
        result = super().write(vals)
        # When attachments are added, rename them to include the document code.
        if "document_attachment_ids" in vals:
            self._rename_attachments()
        return result

    def _rename_attachments(self):
        """Rename linked attachments to follow the document filename pattern."""
        for doc in self:
            for attachment in doc.document_attachment_ids:
                if not attachment.name:
                    continue
                # Preserve the original extension.
                parts = attachment.name.rsplit(".", 1)
                ext = parts[1] if len(parts) == 2 else ""
                new_name = doc._get_download_filename(ext) if ext else doc.filename_pattern
                if attachment.name != new_name:
                    attachment.sudo().write({"name": new_name})


class IsoDocumentRevision(models.Model):
    _name = "od19.iso.document.revision"
    _description = "ISO Document Revision History"
    _order = "effective_date desc, id desc"

    document_id = fields.Many2one(
        "od19.iso.document", string="เอกสาร", required=True, ondelete="cascade"
    )
    revision = fields.Char(string="Revision", required=True)
    effective_date = fields.Date(string="วันที่มีผล")
    approved_by = fields.Many2one("res.users", string="ผู้อนุมัติ")
    note = fields.Char(string="หมายเหตุ")
