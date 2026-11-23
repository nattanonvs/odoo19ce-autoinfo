# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .od19_iso_distribution_list import COPY_TYPE

RESERVED = "reserved"
ISSUED = "issued"
RETURNED = "returned"
REPLACED = "replaced"
DESTROYED = "destroyed"
LOST = "lost"

COPY_STATE = [
    (RESERVED, "สำรองไว้"),
    (ISSUED, "จ่ายแล้ว"),
    (RETURNED, "คืนแล้ว"),
    (REPLACED, "ถูกแทนที่ (เปลี่ยน revision)"),
    (DESTROYED, "ทำลายแล้ว"),
    (LOST, "สูญหาย"),
]


class Od19IsoPrintCopy(models.Model):
    """ตัวสำเนาควบคุม (ทะเบียนพิมพ์) — 1 ใบต่อ 1 สำเนาที่พิมพ์ออกมา."""

    _name = "od19.iso.print.copy"
    _description = "ISO Controlled Print Copy"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_id, copy_number"
    _rec_name = "name"

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="เลขสำเนา",
        compute="_compute_name",
        store=True,
        help="รูปแบบ {รหัสเอกสาร}/P{ลำดับ 3 หลัก} เช่น FM-PU-12/P001",
    )
    print_request_id = fields.Many2one(
        "od19.iso.print.request",
        string="ใบขอพิมพ์",
        required=True,
        ondelete="cascade",
    )
    document_id = fields.Many2one(
        "od19.iso.document", string="เอกสาร", required=True, ondelete="cascade"
    )
    department_id = fields.Many2one(
        "hr.department",
        string="แผนก",
        related="document_id.department_id",
        store=True,
        readonly=True,
    )
    revision = fields.Char(
        string="Revision", related="print_request_id.revision", store=True
    )
    copy_number = fields.Integer(string="ลำดับสำเนา", required=True)
    copy_type = fields.Selection(
        COPY_TYPE, string="ประเภทสำเนา", default="controlled", required=True
    )

    # ------------------------------------------------------------------
    # Holder / lifecycle dates
    # ------------------------------------------------------------------
    holder_id = fields.Many2one("res.users", string="ผู้ถือครอง (ภายใน)")
    holder_name = fields.Char(string="ชื่อผู้ถือครอง (ภายนอก)")
    holder_dept_id = fields.Many2one("hr.department", string="แผนกผู้ถือครอง")
    issue_date = fields.Date(string="วันจ่ายสำเนา")
    return_due_date = fields.Date(string="กำหนดคืน")
    return_date = fields.Date(string="วันที่คืนจริง")
    state = fields.Selection(
        COPY_STATE, string="สถานะ", default=RESERVED, required=True, tracking=True
    )
    replaced_by_id = fields.Many2one(
        "od19.iso.print.copy", string="แทนที่ด้วย"
    )
    replaced_from_id = fields.Many2one(
        "od19.iso.print.copy", string="แทนที่ฉบับ"
    )
    reason = fields.Text(string="เหตุผล (ทำลาย/สูญหาย)")
    stamp_text = fields.Char(string="ข้อความตราประทับ", compute="_compute_stamp_text")
    qr_payload = fields.Char(string="ข้อมูล QR", compute="_compute_qr_payload")
    company_id = fields.Many2one(
        "res.company", string="บริษัท", default=lambda self: self.env.company
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("document_id", "copy_number")
    def _compute_name(self):
        for rec in self:
            code = rec.document_id.code if rec.document_id else False
            rec.name = "%s/P%03d" % (code or "DOC", rec.copy_number or 0)

    @api.depends("copy_type", "name", "revision")
    def _compute_stamp_text(self):
        for rec in self:
            label = (
                "CONTROLLED COPY"
                if rec.copy_type == "controlled"
                else "UNCONTROLLED COPY"
            )
            rec.stamp_text = "%s  %s  Rev.%s" % (
                label,
                rec.name or "",
                rec.revision or "00",
            )

    @api.depends("name", "document_id", "revision", "copy_number", "holder_id")
    def _compute_qr_payload(self):
        for rec in self:
            rec.qr_payload = "|".join([
                rec.document_id.code or "",
                "Rev.%s" % (rec.revision or "00"),
                rec.name or "",
                rec.holder_id.name or rec.holder_name or "",
            ])

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("print_request_id"):
                request = self.env["od19.iso.print.request"].browse(
                    vals["print_request_id"]
                )
                if not vals.get("document_id"):
                    vals["document_id"] = request.document_id.id
                if not vals.get("copy_type"):
                    vals["copy_type"] = request.copy_type
            if not vals.get("copy_number") and vals.get("document_id"):
                last = self.search(
                    [("document_id", "=", vals["document_id"])],
                    order="copy_number desc",
                    limit=1,
                )
                vals["copy_number"] = (last.copy_number or 0) + 1
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Lifecycle actions
    # ------------------------------------------------------------------
    def action_issue(self):
        for rec in self:
            if rec.state != RESERVED:
                raise UserError(
                    _("จ่ายสำเนาได้เฉพาะสำเนาที่สำรองไว้ (reserved) เท่านั้น")
                )
            rec.state = ISSUED
            if not rec.issue_date:
                rec.issue_date = fields.Date.today()
            rec.message_post(
                body=_("จ่ายสำเนา %s โดย %s") % (rec.name, self.env.user.name)
            )

    def action_return(self):
        for rec in self:
            if rec.state != ISSUED:
                raise UserError(_("คืนได้เฉพาะสำเนาที่จ่ายแล้วเท่านั้น"))
            rec.state = RETURNED
            rec.return_date = fields.Date.today()
            rec.message_post(
                body=_("รับคืนสำเนา %s") % rec.name
            )

    def action_destroy(self):
        for rec in self:
            if rec.state not in (RESERVED, ISSUED):
                raise UserError(
                    _("ทำลายได้เฉพาะสำเนาที่ยังไม่คืน/ไม่ถูกแทนที่")
                )
            rec.state = DESTROYED
            rec.message_post(body=_("ทำลายสำเนา %s") % rec.name)

    def action_mark_lost(self):
        for rec in self:
            if rec.state not in (RESERVED, ISSUED):
                raise UserError(
                    _("บันทึกสูญหายได้เฉพาะสำเนาที่ยังไม่คืน/ไม่ถูกแทนที่")
                )
            rec.state = LOST
            rec.message_post(body=_("บันทึกสำเนา %s สูญหาย") % rec.name)

    # ------------------------------------------------------------------
    # G1: revision-driven replacement
    # ------------------------------------------------------------------
    @api.model
    def _on_document_revision_change(self, document, new_revision):
        """เมื่อเอกสารมี revision ใหม่ — ตั้งสำเนาที่จ่ายแล้วของ revision เก่าเป็น
        ``replaced`` และสร้างใบขอพิมพ์ ``replace_revision`` อัตโนมัติ.

        คืนค่า print.request ที่สร้าง (หรือ recordset ว่างถ้าไม่มีสำเนาที่ต้องแทน)
        """
        copies = self.search([
            ("document_id", "=", document.id),
            ("state", "=", ISSUED),
        ]).filtered(lambda c: (c.revision or "") != (new_revision or ""))
        if not copies:
            return self.env["od19.iso.print.request"]

        request = self.env["od19.iso.print.request"].create({
            "document_id": document.id,
            "revision": new_revision,
            "request_type": "replace_revision",
            "copies_count": len(copies),
            "copy_type": copies[0].copy_type,
            "requester_id": self.env.user.id,
            "note": _("สร้างอัตโนมัติ: เอกสารเปลี่ยน revision เป็น %s")
            % new_revision,
        })
        copies.write({"state": REPLACED})
        request.message_post(
            body=_("ตรวจพบการเปลี่ยน revision เป็น %s — ต้องพิมพ์แทนสำเนาเดิม %s ใบ")
            % (new_revision, len(copies))
        )
        return request

    # ------------------------------------------------------------------
    # Cron: overdue return reminder
    # ------------------------------------------------------------------
    @api.model
    def _cron_copy_return_overdue(self):
        """แจ้งเตือนสำเนาที่จ่ายแล้วและเลยกำหนดคืน."""
        today = fields.Date.today()
        overdue = self.search([
            ("state", "=", ISSUED),
            ("return_due_date", "!=", False),
            ("return_due_date", "<", today),
        ])
        for copy in overdue:
            if copy.activity_ids:
                continue
            user = (
                copy.holder_id
                or copy.print_request_id.requester_id
                or self.env.user
            )
            copy.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                summary=_("สำเนา %s ค้างคืนเกินกำหนด") % copy.name,
                note=_("กรุณาคืนสำเนา %s ภายในกำหนด %s")
                % (copy.name, copy.return_due_date),
            )
        return True
