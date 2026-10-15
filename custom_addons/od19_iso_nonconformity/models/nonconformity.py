# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


NC_STATUS = [
    ("draft", "ร่าง"),
    ("open", "เปิด"),
    ("analysis", "วิเคราะห์สาเหตุ"),
    ("action", "ดำเนินการแก้ไข"),
    ("verification", "ตรวจสอบผล"),
    ("closed", "ปิด"),
    ("cancel", "ยกเลิก"),
]

NC_SEVERITY = [
    ("minor", "รอง (Minor)"),
    ("major", "หลัก (Major)"),
    ("critical", "ร้ายแรง (Critical)"),
]

NC_SOURCE = [
    ("internal_audit", "การตรวจสอบภายใน"),
    ("external_audit", "การตรวจสอบภายนอก"),
    ("customer_complaint", "ร้องเรียนลูกค้า"),
    ("process", "กระบวนการผลิต"),
    ("incoming", "การตรวจสอบวัสดุเข้า"),
    ("final", "การตรวจสอบสินค้าสำเร็จรูป"),
    ("management_review", "การทบทวนระบบจัดการ"),
    ("other", "อื่นๆ"),
]

NC_CATEGORY = [
    ("quality", "คุณภาพ"),
    ("environment", "สิ่งแวดล้อม"),
    ("safety", "ความปลอดภัย"),
    ("document", "เอกสาร"),
    ("process", "กระบวนการ"),
    ("equipment", "อุปกรณ์"),
    ("personnel", "บุคลากร"),
    ("supplier", "ผู้ผลิต"),
    ("other", "อื่นๆ"),
]


class IsoNonconformity(models.Model):
    """ไม่สอดคล้องและการดำเนินการแก้ไข (Nonconformity & CAPA)
    ISO 9001 clause 10.2, ISO 14001 clause 10.2"""

    _name = "od19.iso.nonconformity"
    _description = "ISO Nonconformity / CAPA"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="เลขที่", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.nc") or "/",
    )
    title = fields.Char(string="หัวข้อ", required=True, tracking=True)
    state = fields.Selection(
        NC_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )
    severity = fields.Selection(NC_SEVERITY, string="ระดับ", required=True, tracking=True)
    source = fields.Selection(NC_SOURCE, string="แหล่งที่มา", required=True, tracking=True)
    category = fields.Selection(NC_CATEGORY, string="ประเภท", required=True, tracking=True)
    standard_ids = fields.Many2many("od19.iso.standard", string="มาตรฐาน ISO", tracking=True)
    iso_clause = fields.Char(string="ข้อ ISO", tracking=True)
    department_id = fields.Many2one(
        "hr.department", string="แผนกที่เกี่ยวข้อง", tracking=True,
    )
    related_audit_id = fields.Many2one(
        "od19.iso.audit", string="การตรวจสอบที่เกี่ยวข้อง", tracking=True,
    )
    partner_id = fields.Many2one("res.partner", string="ลูกค้า/ผู้ผลิต", tracking=True)

    # Description
    description = fields.Text(string="รายละเอียดความไม่สอดคล้อง", required=True, tracking=True)
    immediate_action = fields.Text(string="การดำเนินการทันที (Correction)", tracking=True)
    containment_action = fields.Text(string="การกักกัน (Containment Action)", tracking=True)

    # Root cause analysis
    root_cause_method = fields.Selection(
        [("5why", "5 Whys"), ("fishbone", "Fishbone / Ishikawa"), ("fmea", "FMEA"), ("other", "อื่นๆ")],
        string="วิธีวิเคราะห์สาเหตุ", tracking=True,
    )
    root_cause = fields.Text(string="สาเหตุที่แท้จริง (Root Cause)", tracking=True)

    # Corrective action
    corrective_action = fields.Text(string="การดำเนินการแก้ไข (Corrective Action)", tracking=True)
    preventive_action = fields.Text(string="การป้องกัน (Preventive Action)", tracking=True)
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ", tracking=True)
    due_date = fields.Date(string="วันกำหนดเสร็จ", tracking=True)
    action_date = fields.Date(string="วันดำเนินการ", tracking=True)

    # Verification
    verification_method = fields.Text(string="วิธีตรวจสอบ", tracking=True)
    verification_result = fields.Text(string="ผลการตรวจสอบ", tracking=True)
    verification_date = fields.Date(string="วันที่ตรวจสอบ", tracking=True)
    verified_by_id = fields.Many2one("res.users", string="ผู้ตรวจสอบ", tracking=True)

    # Closure
    effective = fields.Boolean(string="มีประสิทธิภาพ", tracking=True)
    close_date = fields.Date(string="วันที่ปิด", tracking=True)
    closed_by_id = fields.Many2one("res.users", string="ผู้ปิด", tracking=True)

    # Attachments
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")

    action_plan_ids = fields.One2many(
        "od19.iso.nc.action", "nc_id", string="แผนการดำเนินการ",
    )

    def action_open(self):
        self.write({"state": "open"})

    def action_analysis(self):
        self.write({"state": "analysis"})

    def action_action(self):
        self.write({"state": "action"})

    def action_verification(self):
        self.write({"state": "verification"})

    def action_close(self):
        self.write({
            "state": "closed",
            "close_date": fields.Date.today(),
            "closed_by_id": self.env.user.id,
        })

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    @api.constrains("due_date", "action_date")
    def _check_dates(self):
        for rec in self:
            if rec.due_date and rec.action_date and rec.action_date > rec.due_date:
                raise ValidationError(_("วันดำเนินการต้องไม่หลังวันกำหนด"))

    @api.constrains("state", "verification_date")
    def _check_verification(self):
        for rec in self:
            if rec.state == "closed" and not rec.verification_date:
                raise ValidationError(_("กรุณากรอกวันที่ตรวจสอบก่อนปิด"))


class IsoNcAction(models.Model):
    """รายการการดำเนินการในแผน CAPA"""

    _name = "od19.iso.nc.action"
    _description = "ISO Nonconformity Action Plan Item"
    _order = "sequence, id"

    sequence = fields.Integer(string="ลำดับ", default=10)
    nc_id = fields.Many2one(
        "od19.iso.nonconformity", string="ไม่สอดคล้อง", required=True, ondelete="cascade",
    )
    action = fields.Char(string="การดำเนินการ", required=True)
    action_type = fields.Selection(
        [("corrective", "แก้ไข"), ("preventive", "ป้องกัน"), ("improvement", "ปรับปรุง")],
        string="ประเภท", required=True, default="corrective",
    )
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ")
    due_date = fields.Date(string="วันกำหนด")
    done_date = fields.Date(string="วันเสร็จ")
    status = fields.Selection(
        [("pending", "รอดำเนินการ"), ("in_progress", "กำลังดำเนินการ"), ("done", "เสร็จสิ้น")],
        string="สถานะ", default="pending",
    )
    note = fields.Text(string="หมายเหตุ")

    def action_in_progress(self):
        self.write({"status": "in_progress"})

    def action_done(self):
        self.write({"status": "done", "done_date": fields.Date.today()})
