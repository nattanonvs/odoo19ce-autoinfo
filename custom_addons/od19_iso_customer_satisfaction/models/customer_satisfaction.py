# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


SURVEY_STATUS = [
    ("draft", "ร่าง"),
    ("sent", "ส่งแล้ว"),
    ("completed", "ตอบกลับแล้ว"),
    ("cancelled", "ยกเลิก"),
]

CSAT_LEVEL = [
    ("1", "1 - ไม่พอใจมาก"),
    ("2", "2 - ไม่พอใจ"),
    ("3", "3 - ปานกลาง"),
    ("4", "4 - พอใจ"),
    ("5", "5 - พอใจมาก"),
]


class IsoCustomerSatisfactionSurvey(models.Model):
    """แบบสอบถามความพึงพอใจลูกค้า (Customer Satisfaction Survey)
    ISO 9001 clause 9.1.2"""

    _name = "od19.iso.customer.satisfaction"
    _description = "ISO Customer Satisfaction Survey"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(
        string="เลขที่", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.csat") or "/",
    )
    partner_id = fields.Many2one(
        "res.partner", string="ลูกค้า", required=True, tracking=True,
    )
    contact_person = fields.Char(string="ผู้ติดต่อ", tracking=True)
    date = fields.Date(string="วันที่", required=True, default=fields.Date.today, tracking=True)
    period = fields.Char(string="ระยะเวลา", tracking=True, help="เช่น Q1/2569, รอบ 6 เดือน")
    method = fields.Selection(
        [
            ("questionnaire", "แบบสอบถาม"),
            ("interview", "สัมภาษณ์"),
            ("meeting", "ประชุม"),
            ("online", "ออนไลน์"),
            ("other", "อื่นๆ"),
        ],
        string="วิธีการ", required=True, default="questionnaire", tracking=True,
    )
    status = fields.Selection(
        SURVEY_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )
    overall_score = fields.Float(
        string="คะแนนรวม", compute="_compute_overall_score", store=True, tracking=True,
    )
    overall_csat = fields.Selection(
        CSAT_LEVEL, string="ระดับความพึงพอใจโดยรวม", tracking=True,
    )
    would_recommend = fields.Selection(
        [("yes", "ใช่"), ("no", "ไม่"), ("maybe", "อาจจะ")],
        string="แนะนำให้ผู้อื่น", tracking=True,
    )
    item_ids = fields.One2many(
        "od19.iso.csat.item", "survey_id", string="รายการประเมิน",
    )
    positive_feedback = fields.Text(string="ข้อเสนอแนะเชิงบวก", tracking=True)
    improvement = fields.Text(string="ข้อเสนอแนะปรับปรุง", tracking=True)
    complaint = fields.Text(string="เรื่องร้องเรียน", tracking=True)
    action_taken = fields.Text(string="การดำเนินการที่ทำแล้ว", tracking=True)
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ", tracking=True)
    close_date = fields.Date(string="วันที่ปิด", tracking=True)

    @api.depends("item_ids.score")
    def _compute_overall_score(self):
        for rec in self:
            items = rec.item_ids.filtered(lambda i: i.max_score > 0)
            if items:
                total_max = sum(items.mapped("max_score"))
                total_score = sum(items.mapped("score"))
                rec.overall_score = (total_score / total_max) * 5 if total_max else 0
            else:
                rec.overall_score = 0

    def action_sent(self):
        self.write({"status": "sent"})

    def action_complete(self):
        self.write({"status": "completed"})

    def action_cancel(self):
        self.write({"status": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"status": "draft"})

    def action_close(self):
        self.write({"status": "completed", "close_date": fields.Date.today()})


class IsoCsatItem(models.Model):
    """รายการประเมินในแบบสอบถาม"""

    _name = "od19.iso.csat.item"
    _description = "ISO Customer Satisfaction Item"
    _order = "sequence, id"

    sequence = fields.Integer(string="ลำดับ", default=10)
    survey_id = fields.Many2one(
        "od19.iso.customer.satisfaction", string="แบบสอบถาม", required=True, ondelete="cascade",
    )
    name = fields.Char(string="หัวข้อ", required=True)
    category = fields.Selection(
        [
            ("quality", "คุณภาพสินค้า"),
            ("delivery", "การจัดส่ง"),
            ("price", "ราคา"),
            ("service", "บริการ"),
            ("communication", "การสื่อสาร"),
            ("support", "การสนับสนุน"),
            ("documentation", "เอกสาร"),
            ("other", "อื่นๆ"),
        ],
        string="กลุ่ม", required=True, default="quality",
    )
    max_score = fields.Float(string="คะแนนเต็ม", default=5, required=True)
    score = fields.Float(string="คะแนนที่ได้", default=0)
    comment = fields.Text(string="ความคิดเห็น")

    @api.constrains("score", "max_score")
    def _check_score(self):
        for rec in self:
            if rec.score < 0 or rec.score > rec.max_score:
                raise ValidationError(
                    _("คะแนน '%s' ต้องอยู่ระหว่าง 0 ถึง %.2f") % (rec.name, rec.max_score)
                )


class IsoCsatPeriodReport(models.Model):
    """รายงานสรุปความพึงพอใจรายงวด"""

    _name = "od19.iso.csat.period.report"
    _description = "ISO Customer Satisfaction Period Report"
    _order = "period desc"

    name = fields.Char(string="ชื่อรายงาน", required=True)
    period = fields.Char(string="งวด", required=True)
    date_from = fields.Date(string="จากวันที่")
    date_to = fields.Date(string="ถึงวันที่")
    survey_count = fields.Integer(string="จำนวนแบบสอบถาม", compute="_compute_stats", store=True)
    avg_score = fields.Float(string="คะแนนเฉลี่ย", compute="_compute_stats", store=True)
    summary = fields.Text(string="สรุปผล")
    action_plan = fields.Text(string="แผนการปรับปรุง")
    state = fields.Selection(
        [("draft", "ร่าง"), ("done", "เสร็จสิ้น")], string="สถานะ", default="draft",
    )

    survey_ids = fields.Many2many(
        "od19.iso.customer.satisfaction", string="แบบสอบถาม",
        domain="[('date','>=',date_from),('date','<=',date_to)]",
    )

    @api.depends("survey_ids.overall_score")
    def _compute_stats(self):
        for rec in self:
            surveys = rec.survey_ids
            rec.survey_count = len(surveys)
            scores = surveys.mapped("overall_score")
            rec.avg_score = sum(scores) / len(scores) if scores else 0

    def action_done(self):
        self.write({"state": "done"})
