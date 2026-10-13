# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


RISK_TYPE = [
    ("risk", "ความเสี่ยง (Risk)"),
    ("opportunity", "โอกาส (Opportunity)"),
]

RISK_STATUS = [
    ("draft", "ร่าง"),
    ("identified", "ระบุแล้ว"),
    ("analyzed", "วิเคราะห์แล้ว"),
    ("evaluated", "ประเมินแล้ว"),
    ("treated", "กำลังดำเนินการ"),
    ("monitored", "เฝ้าดู"),
    ("closed", "ปิด"),
    ("cancel", "ยกเลิก"),
]

RISK_CATEGORY = [
    ("strategic", "เชิงกลยุทธ์"),
    ("operational", "ปฏิบัติการ"),
    ("financial", "การเงิน"),
    ("quality", "คุณภาพ"),
    ("environment", "สิ่งแวดล้อม"),
    ("safety", "ความปลอดภัย"),
    ("compliance", "การปฏิบัติตามกฎหมาย"),
    ("reputational", "ชื่อเสียง"),
    ("supply_chain", "ห่วงโซ่จัดหา"),
    ("technology", "เทคโนโลยี"),
    ("other", "อื่นๆ"),
]

LIKELIHOOD_LEVEL = [
    ("1", "1 - น้อยมาก"),
    ("2", "2 - น้อย"),
    ("3", "3 - ปานกลาง"),
    ("4", "4 - สูง"),
    ("5", "5 - สูงมาก"),
]

SEVERITY_LEVEL = [
    ("1", "1 - น้อยมาก"),
    ("2", "2 - น้อย"),
    ("3", "3 - ปานกลาง"),
    ("4", "4 - สูง"),
    ("5", "5 - สูงมาก"),
]

RISK_LEVEL = [
    ("low", "ต่ำ"),
    ("medium", "ปานกลาง"),
    ("high", "สูง"),
    ("critical", "วิกฤต"),
]

TREATMENT_TYPE = [
    ("avoid", "หลีกเลี่ยง (Avoid)"),
    ("reduce", "ลดความเสี่ยง (Reduce)"),
    ("transfer", "โอน (Transfer)"),
    ("accept", "ยอมรับ (Accept)"),
    ("exploit", "ใช้ประโยชน์ (Exploit) - โอกาส"),
    ("enhance", "เพิ่ม (Enhance) - โอกาส"),
    ("share", "แบ่งปัน (Share) - โอกาส"),
]


class IsoRisk(models.Model):
    """ความเสี่ยงและโอกาส (Risk & Opportunity)
    ISO 9001 clause 6.1, ISO 14001 clause 6.1"""

    _name = "od19.iso.risk"
    _description = "ISO Risk and Opportunity"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "risk_score desc, id"

    name = fields.Char(
        string="รหัส", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.risk") or "/",
    )
    title = fields.Char(string="หัวข้อ", required=True, tracking=True)
    risk_type = fields.Selection(RISK_TYPE, string="ประเภท", required=True, tracking=True)
    category = fields.Selection(RISK_CATEGORY, string="กลุ่ม", required=True, tracking=True)
    standard_ids = fields.Many2many("od19.iso.standard", string="มาตรฐาน ISO", tracking=True)
    iso_clause = fields.Char(string="ข้อ ISO", tracking=True)
    department_id = fields.Many2one("hr.department", string="แผนก", tracking=True)
    process = fields.Char(string="กระบวนการที่เกี่ยวข้อง", tracking=True)
    state = fields.Selection(
        RISK_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )

    # Description
    description = fields.Text(string="รายละเอียด", required=True, tracking=True)
    cause = fields.Text(string="สาเหตุ", tracking=True)
    consequence = fields.Text(string="ผลกระทบ", tracking=True)

    # Risk analysis (likelihood x severity = score)
    likelihood = fields.Selection(LIKELIHOOD_LEVEL, string="ความเป็นไปได้", tracking=True)
    severity = fields.Selection(SEVERITY_LEVEL, string="ความรุนแรง", tracking=True)
    risk_score = fields.Integer(
        string="คะแนนความเสี่ยง", compute="_compute_risk_score", store=True, tracking=True,
    )
    risk_level = fields.Selection(
        RISK_LEVEL, string="ระดับความเสี่ยง", compute="_compute_risk_level", store=True, tracking=True,
    )

    # Risk evaluation
    risk_owner_id = fields.Many2one("res.users", string="ผู้รับผิดชอบความเสี่ยง", tracking=True)
    risk_appetite = fields.Selection(
        [("accept", "ยอมรับ"), ("treat", "ต้องดำเนินการ")],
        string="การตัดสินใจ", tracking=True,
    )

    # Treatment
    treatment_type = fields.Selection(TREATMENT_TYPE, string="วิธีการดำเนินการ", tracking=True)
    treatment_plan = fields.Text(string="แผนการดำเนินการ", tracking=True)
    treatment_responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบดำเนินการ", tracking=True)
    due_date = fields.Date(string="วันกำหนด", tracking=True)
    treatment_done_date = fields.Date(string="วันดำเนินการเสร็จ", tracking=True)

    # Monitoring
    residual_likelihood = fields.Selection(LIKELIHOOD_LEVEL, string="ความเป็นไปได้หลังดำเนินการ", tracking=True)
    residual_severity = fields.Selection(SEVERITY_LEVEL, string="ความรุนแรงหลังดำเนินการ", tracking=True)
    residual_score = fields.Integer(
        string="คะแนนหลังดำเนินการ", compute="_compute_residual_score", store=True, tracking=True,
    )
    effectiveness = fields.Selection(
        [("effective", "มีประสิทธิภาพ"), ("partially", "บางส่วน"), ("ineffective", "ไม่มีประสิทธิภาพ")],
        string="ประสิทธิภาพ", tracking=True,
    )

    review_date = fields.Date(string="วันที่ตรวจทานครั้งถัดไป", tracking=True)
    close_date = fields.Date(string="วันที่ปิด", tracking=True)
    note = fields.Text(string="หมายเหตุ")
    attachment_ids = fields.Many2many("ir.attachment", string="ไฟล์แนบ")

    action_ids = fields.One2many("od19.iso.risk.action", "risk_id", string="รายการดำเนินการ")

    @api.depends("likelihood", "severity")
    def _compute_risk_score(self):
        for rec in self:
            if rec.likelihood and rec.severity:
                rec.risk_score = int(rec.likelihood) * int(rec.severity)
            else:
                rec.risk_score = 0

    @api.depends("risk_score")
    def _compute_risk_level(self):
        for rec in self:
            score = rec.risk_score or 0
            if score >= 20:
                rec.risk_level = "critical"
            elif score >= 12:
                rec.risk_level = "high"
            elif score >= 6:
                rec.risk_level = "medium"
            else:
                rec.risk_level = "low"

    @api.depends("residual_likelihood", "residual_severity")
    def _compute_residual_score(self):
        for rec in self:
            if rec.residual_likelihood and rec.residual_severity:
                rec.residual_score = int(rec.residual_likelihood) * int(rec.residual_severity)
            else:
                rec.residual_score = 0

    def action_identified(self):
        self.write({"state": "identified"})

    def action_analyzed(self):
        self.write({"state": "analyzed"})

    def action_evaluated(self):
        self.write({"state": "evaluated"})

    def action_treated(self):
        self.write({"state": "treated"})

    def action_monitored(self):
        self.write({"state": "monitored"})

    def action_close(self):
        self.write({"state": "closed", "close_date": fields.Date.today()})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class IsoRiskAction(models.Model):
    """รายการดำเนินการจัดการความเสี่ยง"""

    _name = "od19.iso.risk.action"
    _description = "ISO Risk Action Plan Item"
    _order = "sequence, id"

    sequence = fields.Integer(string="ลำดับ", default=10)
    risk_id = fields.Many2one(
        "od19.iso.risk", string="ความเสี่ยง/โอกาส", required=True, ondelete="cascade",
    )
    action = fields.Char(string="การดำเนินการ", required=True)
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ")
    due_date = fields.Date(string="วันกำหนด")
    done_date = fields.Date(string="วันเสร็จ")
    status = fields.Selection(
        [("pending", "รอ"), ("in_progress", "กำลังทำ"), ("done", "เสร็จ")],
        string="สถานะ", default="pending",
    )
    note = fields.Text(string="หมายเหตุ")

    def action_in_progress(self):
        self.write({"status": "in_progress"})

    def action_done(self):
        self.write({"status": "done", "done_date": fields.Date.today()})
