# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


EQUIPMENT_STATUS = [
    ("active", "ใช้งาน"),
    ("calibrated", "สอบเทียบแล้ว"),
    ("due", "ใกล้หมดอายุ"),
    ("overdue", "หมดอายุ"),
    ("out_of_service", "พักใช้งาน"),
    ("decommissioned", "เลิกใช้"),
]

CALIBRATION_STATUS = [
    ("draft", "ร่าง"),
    ("scheduled", "ตารางสอบเทียบ"),
    ("in_progress", "กำลังสอบเทียบ"),
    ("passed", "ผ่าน"),
    ("failed", "ไม่ผ่าน"),
    ("cancelled", "ยกเลิก"),
]

CALIBRATION_TYPE = [
    ("internal", "ภายใน"),
    ("external", "ภายนอก"),
    ("self", "สอบเทียบเอง"),
]

ACCURACY_RESULT = [
    ("within_tolerance", "อยู่ในเกณฑ์"),
    ("out_of_tolerance", "ออกนอกเกณฑ์"),
    ("adjusted", "ปรับแล้ว"),
]


class IsoCalibrationEquipment(models.Model):
    """เครื่องมือวัดและอุปกรณ์ตรวจสอบ (Monitoring & Measuring Equipment)
    ISO 9001 clause 7.1.5, ISO 14001 clause 7.1"""

    _name = "od19.iso.calibration.equipment"
    _description = "ISO Calibration Equipment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="ชื่อเครื่องมือ", required=True, tracking=True)
    code = fields.Char(string="รหัสเครื่องมือ", required=True, tracking=True)
    serial_no = fields.Char(string="หมายเลขซีเรียล", tracking=True)
    manufacturer = fields.Char(string="ยี่ห้อ/ผู้ผลิต", tracking=True)
    model = fields.Char(string="รุ่น", tracking=True)
    category = fields.Selection(
        [
            ("dimensional", "เครื่องมือวัดขนาด"),
            ("temperature", "อุณหภูมิ"),
            ("pressure", "ความดัน"),
            ("electrical", "ไฟฟ้า"),
            ("weight", "น้ำหนัก"),
            ("flow", "การไหล"),
            ("environmental", "สิ่งแวดล้อม"),
            ("other", "อื่นๆ"),
        ],
        string="ประเภท", required=True, tracking=True,
    )
    location = fields.Char(string="ตำแหน่งการใช้งาน", tracking=True)
    department_id = fields.Many2one("hr.department", string="แผนก", tracking=True)
    owner_id = fields.Many2one("hr.employee", string="ผู้รับผิดชอบ", tracking=True)
    accuracy_range = fields.Char(string="ช่วงความถูกต้อง", tracking=True)
    resolution = fields.Char(string="ความละเอียด", tracking=True)
    traceability = fields.Char(string="การติดตามความสอดคล้อง", tracking=True)

    # Calibration schedule
    calibration_interval = fields.Integer(string="ช่วงสอบเทียบ (วัน)", default=365, tracking=True)
    last_calibration_date = fields.Date(string="สอบเทียบล่าสุด", tracking=True)
    next_calibration_date = fields.Date(
        string="ครั้งต่อไป", compute="_compute_next_calibration", store=True, tracking=True,
    )
    calibration_status = fields.Selection(
        EQUIPMENT_STATUS, string="สถานะ", compute="_compute_calibration_status",
        store=True, default="active", tracking=True,
    )

    # Equipment state
    state = fields.Selection(
        [("active", "ใช้งาน"), ("out_of_service", "พักใช้"), ("decommissioned", "เลิกใช้")],
        string="สถานะการใช้งาน", default="active", required=True, tracking=True,
    )

    calibration_ids = fields.One2many(
        "od19.iso.calibration.record", "equipment_id", string="ประวัติการสอบเทียบ",
    )
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")
    note = fields.Text(string="หมายเหตุ")

    @api.depends("last_calibration_date", "calibration_interval")
    def _compute_next_calibration(self):
        for rec in self:
            if rec.last_calibration_date and rec.calibration_interval:
                rec.next_calibration_date = fields.Date.add(
                    rec.last_calibration_date, days=rec.calibration_interval
                )
            else:
                rec.next_calibration_date = False

    @api.depends("next_calibration_date", "state")
    def _compute_calibration_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state != "active":
                rec.calibration_status = "out_of_service" if rec.state == "out_of_service" else "decommissioned"
                continue
            if not rec.next_calibration_date:
                rec.calibration_status = "due"
            elif rec.next_calibration_date < today:
                rec.calibration_status = "overdue"
            elif (rec.next_calibration_date - today).days <= 30:
                rec.calibration_status = "due"
            else:
                rec.calibration_status = "calibrated"

    def action_out_of_service(self):
        self.write({"state": "out_of_service"})

    def action_decommission(self):
        self.write({"state": "decommissioned"})

    def action_reactivate(self):
        self.write({"state": "active"})


class IsoCalibrationRecord(models.Model):
    """บันทึกการสอบเทียบ (Calibration Record)"""

    _name = "od19.iso.calibration.record"
    _description = "ISO Calibration Record"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(
        string="เลขที่", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.cal") or "/",
    )
    equipment_id = fields.Many2one(
        "od19.iso.calibration.equipment", string="เครื่องมือ", required=True, ondelete="restrict", tracking=True,
    )
    date = fields.Date(string="วันที่สอบเทียบ", required=True, tracking=True)
    calibration_type = fields.Selection(CALIBRATION_TYPE, string="ประเภท", required=True, default="external", tracking=True)
    lab_id = fields.Many2one("res.partner", string="ห้องสอบเทียบ", tracking=True)
    technician_id = fields.Many2one("hr.employee", string="ช่างสอบเทียบ", tracking=True)
    status = fields.Selection(
        CALIBRATION_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )
    accuracy_result = fields.Selection(ACCURACY_RESULT, string="ผลความถูกต้อง", tracking=True)
    before_value = fields.Char(string="ค่าก่อนสอบเทียบ", tracking=True)
    after_value = fields.Char(string="ค่าหลังสอบเทียบ", tracking=True)
    uncertainty = fields.Char(string="ความไม่แน่นอน", tracking=True)
    passed = fields.Boolean(string="ผ่านการสอบเทียบ", tracking=True)
    certificate_no = fields.Char(string="เลขที่ใบรับรอง", tracking=True)
    certificate_date = fields.Date(string="วันที่ใบรับรอง", tracking=True)
    next_due_date = fields.Date(string="ครั้งต่อไป", tracking=True)
    comment = fields.Text(string="ความคิดเห็น", tracking=True)
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")

    def action_schedule(self):
        self.write({"status": "scheduled"})

    def action_start(self):
        self.write({"status": "in_progress"})

    def action_pass(self):
        self.write({"status": "passed", "passed": True})
        if self.equipment_id:
            self.equipment_id.write({"last_calibration_date": self.date})

    def action_fail(self):
        self.write({"status": "failed", "passed": False})

    def action_cancel(self):
        self.write({"status": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"status": "draft"})
