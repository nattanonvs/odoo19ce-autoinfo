# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


MR_STATUS = [
    ("draft", "ร่าง"),
    ("planned", "วางแปรยัง"),
    ("in_progress", "กำลังประชุม"),
    ("reviewed", "ทบทวนแล้ว"),
    ("closed", "ปิด"),
    ("cancel", "ยกเลิก"),
]

INPUT_TOPIC = [
    ("policy", "ความเหมาะสมของนโยบาย"),
    ("objectives", "เป้าหมายและตัวชี้วัด"),
    ("audit", "ผลการตรวจสอบภายในและภายนอก"),
    ("nc", "ไม่สอดคล้องและการดำเนินการแก้ไข"),
    ("customer", "ความพึงพอใจและข้อร้องเรียนลูกค้า"),
    ("process", "ประสิทธิภาพกระบวนการ"),
    ("risk", "ความเสี่ยงและโอกาส"),
    ("resource", "ทรัพยากรและความเพียงพอ"),
    ("external", "ปัญหาภายนอก (กฎหมาย, เทคโนโลยี, ตลาด)"),
    ("improvement", "โอกาสการปรับปรุง"),
    ("other", "อื่นๆ"),
]

DECISION_TYPE = [
    ("improvement", "การปรับปรุง"),
    ("resource", "ทรัพยากร"),
    ("policy", "นโยบาย"),
    ("objective", "เป้าหมาย"),
    ("process", "กระบวนการ"),
    ("other", "อื่นๆ"),
]


class IsoManagementReview(models.Model):
    """การทบทวนระบบจัดการโดยผู้บริหาร (Management Review)
    ISO 9001 clause 9.3, ISO 14001 clause 9.3"""

    _name = "od19.iso.management.review"
    _description = "ISO Management Review"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(
        string="เลขที่", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.mr") or "/",
    )
    title = fields.Char(string="หัวข้อการทบทวน", required=True, tracking=True)
    state = fields.Selection(
        MR_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )
    standard_ids = fields.Many2many("od19.iso.standard", string="มาตรฐาน ISO", tracking=True)
    date = fields.Date(string="วันที่ทบทวน", required=True, tracking=True)
    location = fields.Char(string="สถานที่", tracking=True)
    chairman_id = fields.Many2one(
        "res.users", string="ประธานการประชุม", required=True, tracking=True,
    )
    attendee_ids = fields.Many2many(
        "res.users", string="ผู้เข้าร่วมการประชุม", tracking=True,
    )

    # Inputs to review (ISO 9001 9.3.2)
    input_ids = fields.One2many(
        "od19.iso.mr.input", "review_id", string="ข้อมูลนำเข้าสู่การทบทวน",
    )
    audit_ids = fields.Many2many(
        "od19.iso.audit", string="การตรวจสอบที่เกี่ยวข้อง", tracking=True,
    )
    nc_ids = fields.Many2many(
        "od19.iso.nonconformity", string="ไม่สอดคล้องที่เกี่ยวข้อง", tracking=True,
    )

    # Review output (ISO 9001 9.3.3)
    output_summary = fields.Text(string="สรุปผลการทบทวน", tracking=True)
    decision_ids = fields.One2many(
        "od19.iso.mr.decision", "review_id", string="การตัดสินใจและการดำเนินการ",
    )
    minutes = fields.Text(string="รายงานการประชุม (Minutes)", tracking=True)
    follow_up_date = fields.Date(string="วันติดตามผล", tracking=True)
    close_date = fields.Date(string="วันที่ปิด", tracking=True)
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")

    def action_plan(self):
        self.write({"state": "planned"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_reviewed(self):
        self.write({"state": "reviewed"})

    def action_close(self):
        self.write({"state": "closed", "close_date": fields.Date.today()})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class IsoMrInput(models.Model):
    """ข้อมูลนำเข้าสู่การทบทวน (Inputs to Management Review)"""

    _name = "od19.iso.mr.input"
    _description = "ISO Management Review Input"
    _order = "review_id, sequence, id"

    sequence = fields.Integer(string="ลำดับ", default=10)
    review_id = fields.Many2one(
        "od19.iso.management.review", string="การทบทวน", required=True, ondelete="cascade",
    )
    topic = fields.Selection(INPUT_TOPIC, string="หัวข้อ", required=True)
    topic_other = fields.Char(string="หัวข้ออื่นๆ")
    summary = fields.Text(string="สรุป", required=True)
    responsible_id = fields.Many2one("res.users", string="ผู้นำเสนอ")
    conclusion = fields.Text(string="ข้อเสนอแนะ")

    def name_get(self):
        result = []
        for rec in self:
            topic_label = dict(INPUT_TOPIC).get(rec.topic, rec.topic)
            name = f"{topic_label}"
            if rec.topic == "other" and rec.topic_other:
                name = rec.topic_other
            result.append((rec.id, name))
        return result


class IsoMrDecision(models.Model):
    """การตัดสินใจและการดำเนินการจากการทบทวน (Outputs of Management Review)"""

    _name = "od19.iso.mr.decision"
    _description = "ISO Management Review Decision"
    _order = "review_id, sequence, id"

    sequence = fields.Integer(string="ลำดับ", default=10)
    review_id = fields.Many2one(
        "od19.iso.management.review", string="การทบทวน", required=True, ondelete="cascade",
    )
    decision_type = fields.Selection(DECISION_TYPE, string="ประเภทการตัดสินใจ", required=True)
    decision = fields.Text(string="การตัดสินใจ", required=True)
    action = fields.Text(string="การดำเนินการที่ต้องทำ")
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ")
    due_date = fields.Date(string="วันกำหนด")
    status = fields.Selection(
        [("open", "เปิด"), ("in_progress", "กำลังดำเนินการ"), ("done", "เสร็จสิ้น"), ("closed", "ปิด")],
        string="สถานะ", default="open",
    )
    close_date = fields.Date(string="วันที่ปิด")
    note = fields.Text(string="หมายเหตุ")

    def action_in_progress(self):
        self.write({"status": "in_progress"})

    def action_done(self):
        self.write({"status": "done"})

    def action_close(self):
        self.write({"status": "closed", "close_date": fields.Date.today()})
