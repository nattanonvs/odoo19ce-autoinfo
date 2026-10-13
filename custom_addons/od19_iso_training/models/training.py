# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


COURSE_STATUS = [
    ("draft", "ร่าง"),
    ("planned", "วางแปรยัง"),
    ("in_progress", "กำลังจัดฝึก"),
    ("completed", "จบหลักสูตร"),
    ("cancelled", "ยกเลิก"),
]

COMPETENCE_LEVEL = [
    ("1", "1 - เริ่มต้น"),
    ("2", "2 - พื้นฐาน"),
    ("3", "3 - ปานกลาง"),
    ("4", "4 - สูง"),
    ("5", "5 - เชี่ยวชาญ"),
]


class IsoTrainingCourse(models.Model):
    """หลักสูตรการฝึกอบรม (Training Course)
    ISO 9001 clause 7.2, ISO 14001 clause 7.2"""

    _name = "od19.iso.training.course"
    _description = "ISO Training Course"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(string="ชื่อหลักสูตร", required=True, tracking=True)
    code = fields.Char(string="รหัสหลักสูตร", tracking=True)
    description = fields.Text(string="รายละเอียด", tracking=True)
    course_type = fields.Selection(
        [
            ("internal", "ภายในองค์กร"),
            ("external", "ภายนอกองค์กร"),
            ("online", "ออนไลน์"),
            ("on_job", "งานจริง (On-the-job)"),
        ],
        string="ประเภทการฝึก", required=True, default="internal", tracking=True,
    )
    iso_clause = fields.Char(string="ข้อ ISO", tracking=True)
    standard_ids = fields.Many2many("od19.iso.standard", string="มาตรฐาน ISO", tracking=True)
    trainer_id = fields.Many2one("res.partner", string="ผู้สอน", tracking=True)
    trainer_internal_id = fields.Many2one("hr.employee", string="ผู้สอน (ภายใน)", tracking=True)
    date = fields.Date(string="วันที่จัด", required=True, tracking=True)
    duration = fields.Float(string="ระยะเวลา (ชม.)", tracking=True)
    location = fields.Char(string="สถานที่", tracking=True)
    max_participants = fields.Integer(string="จำนวนผู้เข้าร่วมสูงสุด", default=0, tracking=True)
    state = fields.Selection(
        COURSE_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )

    participant_ids = fields.One2many(
        "od19.iso.training.participant", "course_id", string="ผู้เข้าร่วม",
    )
    competency_ids = fields.Many2many(
        "od19.iso.competence", string="ความสามารถที่พัฒนา", tracking=True,
    )

    materials = fields.Text(string="สื่อการสอน", tracking=True)
    evaluation_method = fields.Text(string="วิธีประเมินผล", tracking=True)
    conclusion = fields.Text(string="สรุปผล", tracking=True)
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")

    def action_plan(self):
        self.write({"state": "planned"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_complete(self):
        self.write({"state": "completed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    @api.constrains("max_participants")
    def _check_max_participants(self):
        for rec in self:
            if rec.max_participants < 0:
                raise ValidationError(_("จำนวนผู้เข้าร่วมสูงสุดต้องไม่ติดลบ"))


class IsoTrainingParticipant(models.Model):
    """ผู้เข้าร่วมการฝึกอบรม"""

    _name = "od19.iso.training.participant"
    _description = "ISO Training Participant"
    _order = "course_id, id"

    course_id = fields.Many2one(
        "od19.iso.training.course", string="หลักสูตร", required=True, ondelete="cascade", tracking=True,
    )
    employee_id = fields.Many2one("hr.employee", string="พนักงาน", required=True, tracking=True)
    department_id = fields.Many2one(
        "hr.department", string="แผนก", related="employee_id.department_id", store=True,
    )
    attended = fields.Boolean(string="เข้าร่วม", default=True, tracking=True)
    attendance_date = fields.Date(string="วันที่เข้าร่วม", tracking=True)
    pre_test_score = fields.Float(string="คะแนนก่อนฝึก", tracking=True)
    post_test_score = fields.Float(string="คะแนนหลังฝึก", tracking=True)
    passed = fields.Boolean(string="ผ่านการประเมิน", tracking=True)
    competence_level_before = fields.Selection(COMPETENCE_LEVEL, string="ระดับก่อนฝึก", tracking=True)
    competence_level_after = fields.Selection(COMPETENCE_LEVEL, string="ระดับหลังฝึก", tracking=True)
    certificate_issued = fields.Boolean(string="ออกใบประกาศ", default=False, tracking=True)
    certificate_date = fields.Date(string="วันที่ออกใบประกาศ", tracking=True)
    certificate_no = fields.Char(string="เลขที่ใบประกาศ", tracking=True)
    note = fields.Text(string="หมายเหตุ", tracking=True)


class IsoCompetence(models.Model):
    """ความสามารถ/ทักษะ (Competence)
    ISO 9001 clause 7.2"""

    _name = "od19.iso.competence"
    _description = "ISO Competence / Skill"
    _order = "name"

    name = fields.Char(string="ความสามารถ/ทักษะ", required=True, tracking=True)
    code = fields.Char(string="รหัส", tracking=True)
    description = fields.Text(string="รายละเอียด", tracking=True)
    category = fields.Selection(
        [
            ("technical", "ทักษะทางเทคนิค"),
            ("managerial", "ทักษะการจัดการ"),
            ("quality", "คุณภาพ"),
            ("environment", "สิ่งแวดล้อม"),
            ("safety", "ความปลอดภัย"),
            ("iso", "ISO"),
            ("other", "อื่นๆ"),
        ],
        string="กลุ่ม", tracking=True,
    )
    iso_clause = fields.Char(string="ข้อ ISO", tracking=True)
    active = fields.Boolean(string="ใช้งาน", default=True)
    employee_competence_ids = fields.One2many(
        "od19.iso.employee.competence", "competence_id", string="พนักงานที่มีความสามารถนี้",
    )


class IsoEmployeeCompetence(models.Model):
    """ความสามารถของพนักงาน (Employee Competence Matrix)"""

    _name = "od19.iso.employee.competence"
    _description = "ISO Employee Competence"
    _order = "employee_id, competence_id"
    _rec_name = "competence_id"

    employee_id = fields.Many2one(
        "hr.employee", string="พนักงาน", required=True, ondelete="cascade", tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department", string="แผนก", related="employee_id.department_id", store=True,
    )
    competence_id = fields.Many2one(
        "od19.iso.competence", string="ความสามารถ", required=True, ondelete="cascade", tracking=True,
    )
    level = fields.Selection(COMPETENCE_LEVEL, string="ระดับ", required=True, default="1", tracking=True)
    valid_from = fields.Date(string="มีผลตั้งแต่", tracking=True)
    valid_to = fields.Date(string="หมดอายุ", tracking=True)
    source_course_id = fields.Many2one(
        "od19.iso.training.course", string="มาจากหลักสูตร", tracking=True,
    )
    assessor_id = fields.Many2one("hr.employee", string="ผู้ประเมิน", tracking=True)
    note = fields.Text(string="หมายเหตุ", tracking=True)
