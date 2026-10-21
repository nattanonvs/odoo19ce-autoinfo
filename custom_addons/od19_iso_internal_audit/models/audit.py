# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


AUDIT_STATUS = [
    ("draft", "ร่าง"),
    ("planned", "วางแปรยัง"),
    ("in_progress", "กำลังดำเนินการ"),
    ("report", "รายงานผล"),
    ("follow_up", "ติดตามผล"),
    ("closed", "ปิดการตรวจสอบ"),
    ("cancel", "ยกเลิก"),
]

AUDIT_TYPE = [
    ("system", "ระบบ (System)"),
    ("process", "กระบวนการ (Process)"),
    ("product", "ผลิตภัณฑ์ (Product)"),
    ("compliance", "การปฏิบัติตาม (Compliance)"),
]

FINDING_SEVERITY = [
    ("minor", "ไม่สอดคล้องรอง (Minor NC)"),
    ("major", "ไม่สอดคล้องหลัก (Major NC)"),
    ("observation", "ข้อสังเกต (Observation)"),
    ("ofi", "โอกาสปรับปรุง (OFI)"),
]

FINDING_STATUS = [
    ("open", "เปิด"),
    ("in_progress", "กำลังแก้ไข"),
    ("verified", "ตรวจสอบแล้ว"),
    ("closed", "ปิด"),
]


class IsoAuditProgram(models.Model):
    """แผนการตรวจสอบประจำปี (Annual Audit Programme) - ISO 9001 clause 9.2"""

    _name = "od19.iso.audit.program"
    _description = "ISO Audit Programme"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(string="ชื่อแผนการตรวจสอบ", required=True, tracking=True)
    year = fields.Integer(string="ปี", required=True, default=fields.Date.today().year, tracking=True)
    standard_ids = fields.Many2many(
        "od19.iso.standard", string="มาตรฐาน ISO", tracking=True,
    )
    scope = fields.Text(string="ขอบเขตการตรวจสอบ", tracking=True)
    state = fields.Selection(
        [("draft", "ร่าง"), ("approved", "อนุมัติแล้ว"), ("closed", "ปิด")],
        string="สถานะ", default="draft", required=True, tracking=True,
    )
    audit_ids = fields.One2many(
        "od19.iso.audit", "program_id", string="การตรวจสอบ",
    )
    company_id = fields.Many2one(
        "res.company", string="บริษัท", default=lambda self: self.env.company,
    )
    note = fields.Text(string="หมายเหตุ")

    def action_approve(self):
        self.write({"state": "approved"})

    def action_close(self):
        self.write({"state": "closed"})

    @api.constrains("year")
    def _check_year(self):
        for rec in self:
            if rec.year < 2000 or rec.year > 2100:
                raise ValidationError(_("ปีต้องอยู่ระหว่าง 2000 ถึง 2100"))


class IsoAudit(models.Model):
    """การตรวจสอบภายใน (Internal Audit) - ISO 9001 clause 9.2"""

    _name = "od19.iso.audit"
    _description = "ISO Internal Audit"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_planned desc"

    name = fields.Char(
        string="เลขที่การตรวจสอบ", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.audit") or "/",
    )
    title = fields.Char(string="หัวข้อการตรวจสอบ", required=True, tracking=True)
    program_id = fields.Many2one(
        "od19.iso.audit.program", string="แผนการตรวจสอบ", ondelete="restrict", tracking=True,
    )
    standard_ids = fields.Many2many(
        "od19.iso.standard", string="มาตรฐาน ISO", tracking=True,
    )
    audit_type = fields.Selection(AUDIT_TYPE, string="ประเภทการตรวจสอบ", required=True, tracking=True)
    state = fields.Selection(
        AUDIT_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )
    date_planned = fields.Date(string="วันที่วางแผน", required=True, tracking=True)
    date_start = fields.Date(string="วันที่เริ่ม", tracking=True)
    date_end = fields.Date(string="วันที่สิ้นสุด", tracking=True)
    lead_auditor_id = fields.Many2one(
        "res.users", string="หัวหน้าผู้ตรวจสอบ", required=True, tracking=True,
    )
    auditor_ids = fields.Many2many(
        "res.users", string="ผู้ตรวจสอบ", tracking=True,
    )
    auditee_department_id = fields.Many2one(
        "hr.department", string="แผนกที่ถูกตรวจสอบ", required=True, tracking=True,
    )
    process_audited = fields.Char(string="กระบวนการที่ตรวจสอบ", tracking=True)
    iso_clauses = fields.Char(string="ข้อ ISO ที่ตรวจสอบ", tracking=True)
    scope = fields.Text(string="ขอบเขต", tracking=True)
    criteria = fields.Text(string="เกณฑ์การตรวจสอบ", tracking=True)
    finding_ids = fields.One2many(
        "od19.iso.audit.finding", "audit_id", string="ผลการตรวจสอบ (Findings)",
    )
    summary = fields.Text(string="สรุปผลการตรวจสอบ")
    conclusion = fields.Selection(
        [("conforming", "สอดคล้อง"), ("nonconforming", "ไม่สอดคล้อง"), ("partial", "สอดคล้องบางส่วน")],
        string="ผลสรุป", tracking=True,
    )
    report_date = fields.Date(string="วันที่รายงาน", tracking=True)
    follow_up_date = fields.Date(string="วันที่ติดตามผล", tracking=True)
    close_date = fields.Date(string="วันที่ปิดการตรวจสอบ", tracking=True)
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")

    def action_plan(self):
        self.write({"state": "planned"})

    def action_start(self):
        self.write({"state": "in_progress", "date_start": fields.Date.today()})

    def action_report(self):
        self.write({"state": "report", "report_date": fields.Date.today()})

    def action_follow_up(self):
        self.write({"state": "follow_up", "follow_up_date": fields.Date.today()})

    def action_close(self):
        self.write({"state": "closed", "close_date": fields.Date.today()})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("วันที่เริ่มต้นต้องไม่หลังวันที่สิ้นสุด"))

    # ------------------------------------------------------------------
    # Cron: planned audit reminders
    # ------------------------------------------------------------------
    def _has_open_activity(self, summary):
        """True when an activity with the same summary already exists."""
        self.ensure_one()
        return bool(
            self.env["mail.activity"].search_count(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("summary", "=", summary),
                ]
            )
        )

    def _create_reminder_activity(self, activity_type_xmlid, summary, note):
        """Create a mail.activity for the lead auditor."""
        self.ensure_one()
        activity_type = self.env.ref(activity_type_xmlid, raise_if_not_found=False)
        user = self.lead_auditor_id or self.env.user
        if not user:
            return False
        return self.env["mail.activity"].sudo().create(
            {
                "activity_type_id": activity_type.id if activity_type else False,
                "summary": summary,
                "note": note,
                "user_id": user.id,
                "res_model_id": self.env["ir.model"]._get_id("od19.iso.audit"),
                "res_id": self.id,
                "date_deadline": fields.Date.today(),
            }
        )

    @api.model
    def _cron_audit_planned_reminder(self, days=7):
        """Daily cron: remind the lead auditor about audits planned within
        `days` that have not started yet.
        """
        today = fields.Date.today()
        due_limit = fields.Date.add(today, days=days)
        audits = self.search(
            [
                ("state", "in", ["draft", "planned"]),
                ("date_planned", ">=", today),
                ("date_planned", "<=", due_limit),
            ]
        )
        for audit in audits:
            summary = _("การตรวจสอบภายในใกล้ถึงกำหนด: %s") % audit.name
            if audit._has_open_activity(summary):
                continue
            days_left = (audit.date_planned - today).days
            note = _(
                "การตรวจสอบ '%(title)s' (เลขที่ %(name)s) กำหนดเริ่มภายใน "
                "%(days)s วัน (วันที่วางแผน: %(due)s) แผนก: %(dept)s"
            ) % {
                "title": audit.title,
                "name": audit.name,
                "days": days_left,
                "due": audit.date_planned,
                "dept": audit.auditee_department_id.name,
            }
            audit._create_reminder_activity(
                "mail.mail_activity_data_todo", summary, note
            )
            audit.message_post(body=note)


class IsoAuditFinding(models.Model):
    """ผลการตรวจสอบ / ข้อสังเกต (Audit Findings)"""

    _name = "od19.iso.audit.finding"
    _description = "ISO Audit Finding"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "audit_id, id"

    name = fields.Char(string="หัวข้อ", required=True, tracking=True)
    audit_id = fields.Many2one(
        "od19.iso.audit", string="การตรวจสอบ", required=True, ondelete="cascade", tracking=True,
    )
    severity = fields.Selection(FINDING_SEVERITY, string="ระดับ", required=True, tracking=True)
    status = fields.Selection(
        FINDING_STATUS, string="สถานะ", default="open", required=True, tracking=True,
    )
    iso_clause = fields.Char(string="ข้อ ISO", tracking=True)
    requirement = fields.Text(string="ข้อกำหนด", tracking=True)
    evidence = fields.Text(string="หลักฐาน", tracking=True)
    description = fields.Text(string="รายละเอียด", tracking=True)
    correct_action = fields.Text(string="การแก้ไข (Corrective Action)")
    root_cause = fields.Text(string="สาเหตุที่แท้จริง")
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ", tracking=True)
    due_date = fields.Date(string="วันกำหนด", tracking=True)
    verification_date = fields.Date(string="วันที่ตรวจสอบ", tracking=True)
    close_date = fields.Date(string="วันที่ปิด", tracking=True)

    def action_in_progress(self):
        self.write({"status": "in_progress"})

    def action_verify(self):
        self.write({"status": "verified", "verification_date": fields.Date.today()})

    def action_close(self):
        self.write({"status": "closed", "close_date": fields.Date.today()})

    def action_open(self):
        self.write({"status": "open"})

    # ------------------------------------------------------------------
    # Cron: audit finding due reminders
    # ------------------------------------------------------------------
    def _get_reminder_user(self):
        """User to be notified about the finding corrective action."""
        self.ensure_one()
        return self.responsible_id or self.audit_id.lead_auditor_id or self.env.user

    def _has_open_activity(self, summary):
        """True when an activity with the same summary already exists."""
        self.ensure_one()
        return bool(
            self.env["mail.activity"].search_count(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("summary", "=", summary),
                ]
            )
        )

    def _create_reminder_activity(self, activity_type_xmlid, summary, note):
        """Create a mail.activity for the finding owner."""
        self.ensure_one()
        activity_type = self.env.ref(activity_type_xmlid, raise_if_not_found=False)
        user = self._get_reminder_user()
        if not user:
            return False
        return self.env["mail.activity"].sudo().create(
            {
                "activity_type_id": activity_type.id if activity_type else False,
                "summary": summary,
                "note": note,
                "user_id": user.id,
                "res_model_id": self.env["ir.model"]._get_id(
                    "od19.iso.audit.finding"
                ),
                "res_id": self.id,
                "date_deadline": fields.Date.today(),
            }
        )

    @api.model
    def _cron_finding_due_reminder(self, days=7):
        """Daily cron: remind the owner about findings due within `days`
        and findings whose corrective action is overdue.
        """
        today = fields.Date.today()
        due_limit = fields.Date.add(today, days=days)
        open_status = ["open", "in_progress"]

        # Findings due within `days`.
        due_findings = self.search(
            [
                ("status", "in", open_status),
                ("due_date", ">=", today),
                ("due_date", "<=", due_limit),
            ]
        )
        for finding in due_findings:
            summary = _("ข้อบกพร่องจากการตรวจสอบใกล้ครบกำหนด: %s") % finding.name
            if finding._has_open_activity(summary):
                continue
            days_left = (finding.due_date - today).days
            note = _(
                "ข้อบกพร่อง '%(title)s' (การตรวจสอบ %(audit)s) ต้องแก้ไข "
                "ภายใน %(days)s วัน (วันครบกำหนด: %(due)s)"
            ) % {
                "title": finding.name,
                "audit": finding.audit_id.name,
                "days": days_left,
                "due": finding.due_date,
            }
            finding._create_reminder_activity(
                "mail.mail_activity_data_todo", summary, note
            )
            finding.message_post(body=note)

        # Findings overdue.
        overdue_findings = self.search(
            [
                ("status", "in", open_status),
                ("due_date", "<", today),
            ]
        )
        for finding in overdue_findings:
            summary = _("ข้อบกพร่องจากการตรวจสอบเกินกำหนด: %s") % finding.name
            if finding._has_open_activity(summary):
                continue
            overdue_days = (today - finding.due_date).days
            note = _(
                "ข้อบกพร่อง '%(title)s' (การตรวจสอบ %(audit)s) เกินกำหนดมาแล้ว "
                "%(days)s วัน (วันครบกำหนด: %(due)s)"
            ) % {
                "title": finding.name,
                "audit": finding.audit_id.name,
                "days": overdue_days,
                "due": finding.due_date,
            }
            finding._create_reminder_activity(
                "mail.mail_activity_data_warning", summary, note
            )
            finding.message_post(body=note)
