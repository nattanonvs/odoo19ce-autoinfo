# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


SUPPLIER_STATUS = [
    ("prospective", "ผู้จำหน่ายใหม่"),
    ("evaluated", "กำลังประเมิน"),
    ("approved", "ได้รับอนุมัติ"),
    ("conditional", "อนุมัติมีเงื่อนไข"),
    ("rejected", "ไม่อนุมัติ"),
    ("disqualified", "ตัดสิทธิ์"),
    ("suspended", "ระงับ"),
    ("inactive", "ไม่ใช้งาน"),
]

BLOCKED_SUPPLIER_STATUSES = ("disqualified", "suspended", "rejected")

EVAL_STATUS = [
    ("draft", "ร่าง"),
    ("in_progress", "กำลังประเมิน"),
    ("done", "เสร็จสิ้น"),
    ("cancelled", "ยกเลิก"),
]

EVAL_TYPE = [
    ("initial", "ประเมินครั้งแรก"),
    ("periodic", "ประเมินประจำ"),
    ("re-evaluation", "ประเมินซ้ำ"),
    ("special", "ประเมินพิเศษ"),
]


class IsoSupplierEvaluation(models.Model):
    """การประเมินผู้จำหน่าย (Supplier Evaluation)
    ISO 9001 clause 8.4, ISO 14001 clause 8.1/8.4"""

    _name = "od19.iso.supplier.evaluation"
    _description = "ISO Supplier Evaluation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(
        string="เลขที่", required=True, tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("od19.iso.supplier.eval") or "/",
    )
    partner_id = fields.Many2one(
        "res.partner", string="ผู้จำหน่าย", required=True, tracking=True, domain="[('is_company','=',True)]",
    )
    eval_type = fields.Selection(EVAL_TYPE, string="ประเภทการประเมิน", required=True, default="initial", tracking=True)
    date = fields.Date(string="วันที่ประเมิน", required=True, default=fields.Date.today, tracking=True)
    evaluator_id = fields.Many2one("res.users", string="ผู้ประเมิน", default=lambda self: self.env.user, tracking=True)
    status = fields.Selection(
        EVAL_STATUS, string="สถานะ", default="draft", required=True, tracking=True, copy=False,
    )
    result = fields.Selection(
        SUPPLIER_STATUS, string="ผลการประเมิน", tracking=True,
    )
    total_score = fields.Float(
        string="คะแนนรวม", compute="_compute_total_score", store=True, tracking=True,
    )
    max_score = fields.Float(string="คะแนนเต็ม", compute="_compute_max_score", store=True)
    percentage = fields.Float(
        string="เปอร์เซ็นต์", compute="_compute_percentage", store=True, tracking=True,
    )
    grade = fields.Char(string="เกรด", compute="_compute_grade", store=True, tracking=True)
    criteria_ids = fields.One2many(
        "od19.iso.supplier.eval.criteria", "evaluation_id", string="เกณฑ์การประเมิน",
    )
    comment = fields.Text(string="ความคิดเห็น", tracking=True)
    improvement_plan = fields.Text(string="แผนปรับปรุง", tracking=True)
    review_date = fields.Date(string="วันที่ตรวจทานครั้งถัดไป", tracking=True)

    @api.depends("criteria_ids.score")
    def _compute_total_score(self):
        for rec in self:
            rec.total_score = sum(rec.criteria_ids.mapped("score"))

    @api.depends("criteria_ids.max_score")
    def _compute_max_score(self):
        for rec in self:
            rec.max_score = sum(rec.criteria_ids.mapped("max_score"))

    @api.depends(
        "criteria_ids.score",
        "criteria_ids.max_score",
        "criteria_ids.weight",
    )
    def _compute_percentage(self):
        for rec in self:
            total_weight = sum(rec.criteria_ids.mapped("weight"))
            if total_weight:
                weighted = sum(
                    (criterion.score / criterion.max_score) * criterion.weight
                    for criterion in rec.criteria_ids
                    if criterion.max_score
                )
                rec.percentage = (weighted / total_weight) * 100
            else:
                rec.percentage = 0.0

    @api.depends("percentage")
    def _compute_grade(self):
        for rec in self:
            p = rec.percentage
            if p >= 90:
                rec.grade = "A"
            elif p >= 80:
                rec.grade = "B"
            elif p >= 70:
                rec.grade = "C"
            elif p >= 60:
                rec.grade = "D"
            else:
                rec.grade = "F"

    def action_start(self):
        self.write({"status": "in_progress"})

    def action_done(self):
        self.write({"status": "done"})
        # Update partner status if result is set
        for rec in self:
            if rec.result and rec.partner_id:
                partner = rec.partner_id
                vals = {"od19_iso_supplier_status": rec.result}
                if rec.review_date:
                    vals["od19_iso_next_evaluation_date"] = rec.review_date
                partner.write(vals)

    def action_cancel(self):
        self.write({"status": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"status": "draft"})


class IsoSupplierEvalCriteria(models.Model):
    """เกณฑ์การประเมินผู้จำหน่าย (Evaluation Criteria)"""

    _name = "od19.iso.supplier.eval.criteria"
    _description = "ISO Supplier Evaluation Criteria"
    _order = "sequence, id"

    sequence = fields.Integer(string="ลำดับ", default=10)
    evaluation_id = fields.Many2one(
        "od19.iso.supplier.evaluation", string="การประเมิน", required=True, ondelete="cascade",
    )
    name = fields.Char(string="เกณฑ์", required=True)
    category = fields.Selection(
        [
            ("quality", "คุณภาพ"),
            ("delivery", "การจัดส่ง"),
            ("price", "ราคา"),
            ("service", "บริการ"),
            ("environment", "สิ่งแวดล้อม"),
            ("safety", "ความปลอดภัย"),
            ("management", "ระบบจัดการ"),
            ("financial", "การเงิน"),
            ("other", "อื่นๆ"),
        ],
        string="กลุ่ม", required=True, default="quality",
    )
    weight = fields.Float(string="น้ำหนัก (%)", default=100)
    max_score = fields.Float(string="คะแนนเต็ม", default=10, required=True)
    score = fields.Float(string="คะแนนที่ได้", default=0)
    comment = fields.Text(string="หมายเหตุ")

    @api.constrains("score", "max_score")
    def _check_score(self):
        for rec in self:
            if rec.score < 0 or rec.score > rec.max_score:
                raise ValidationError(
                    _("คะแนนต้องอยู่ระหว่าง 0 ถึง %.2f สำหรับ '%s'") % (rec.max_score, rec.name)
                )


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_iso_supplier_status = fields.Selection(
        SUPPLIER_STATUS, string="สถานะผู้จำหน่าย (ISO)", default="prospective",
        tracking=True, copy=False,
    )
    od19_iso_next_evaluation_date = fields.Date(
        string="วันที่ประเมินครั้งถัดไป (ISO)", tracking=True, copy=False,
    )
    od19_iso_evaluation_ids = fields.One2many(
        "od19.iso.supplier.evaluation", "partner_id", string="ประวัติการประเมิน (ISO)",
    )
