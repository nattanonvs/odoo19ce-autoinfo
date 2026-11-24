# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .iso_plan_activity_type import FREQUENCY


PLAN_STATE = [
    ("draft", "ร่าง"),
    ("approved", "อนุมัติแล้ว"),
    ("closed", "ปิด"),
]

# Month columns for the yearly matrix (January .. December).
MONTH_SELECTION = [
    ("01", "ม.ค."),
    ("02", "ก.พ."),
    ("03", "มี.ค."),
    ("04", "เม.ย."),
    ("05", "พ.ค."),
    ("06", "มิ.ย."),
    ("07", "ก.ค."),
    ("08", "ส.ค."),
    ("09", "ก.ย."),
    ("10", "ต.ค."),
    ("11", "พ.ย."),
    ("12", "ธ.ค."),
]

MONTH_THAI = dict(MONTH_SELECTION)

# Status shown inside each month cell of the matrix.
MONTH_STATUS = [
    ("planned", "วางแผน"),
    ("in_progress", "กำลังทำ"),
    ("done", "เสร็จ"),
    ("overdue", "เลยกำหนด"),
]


class IsoAnnualPlan(models.Model):
    """แผนงาน ISO ประจำปี (Annual ISO Plan).

    Groups the ISO activities planned for a given year and drives the
    due-date reminders.
    """

    _name = "od19.iso.annual.plan"
    _description = "ISO Annual Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc, name"

    name = fields.Char(string="ชื่อแผนงาน", required=True, tracking=True)
    year = fields.Integer(
        string="ปี",
        required=True,
        default=lambda self: fields.Date.today().year,
        tracking=True,
    )
    state = fields.Selection(
        PLAN_STATE,
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company", string="บริษัท", default=lambda self: self.env.company
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="ผู้รับผิดชอบแผน",
        default=lambda self: self.env.user,
        tracking=True,
    )
    standard_ids = fields.Many2many(
        "od19.iso.standard", string="มาตรฐาน ISO", tracking=True
    )
    reminder_days = fields.Char(
        string="แจ้งล่วงหน้า (วัน)",
        default="30,15,7",
        help="จำนวนวันล่วงหน้าที่ต้องการแจ้งเตือน คั่นด้วยเครื่องหมายจุลภาค "
        "เช่น 30,15,7 (จะแจ้งเตือนเมื่อใกล้ถึงกำหนดในแต่ละช่วง)",
    )
    line_ids = fields.One2many(
        "od19.iso.annual.plan.line", "plan_id", string="กิจกรรมตามแผน"
    )
    schedule_ids = fields.One2many(
        "od19.iso.annual.plan.schedule",
        "plan_id",
        string="กำหนดการรายเดือน",
    )
    line_count = fields.Integer(
        string="จำนวนกิจกรรม", compute="_compute_counts"
    )
    schedule_count = fields.Integer(
        string="จำนวนกำหนดการ", compute="_compute_counts"
    )
    note = fields.Text(string="หมายเหตุ")

    @api.depends("line_ids", "line_ids.schedule_ids")
    def _compute_counts(self):
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.schedule_count = sum(
                len(line.schedule_ids) for line in plan.line_ids
            )

    @api.constrains("year")
    def _check_year(self):
        for plan in self:
            if plan.year < 2000 or plan.year > 2100:
                raise ValidationError(_("ปีต้องอยู่ระหว่าง 2000 ถึง 2100"))

    @api.constrains("reminder_days")
    def _check_reminder_days(self):
        for plan in self:
            if plan.reminder_days and not plan._get_reminder_thresholds():
                raise ValidationError(
                    _("รูปแบบแจ้งล่วงหน้าไม่ถูกต้อง ตัวอย่างที่ถูกต้อง: 30,15,7")
                )

    def _get_reminder_thresholds(self):
        """Return the configured reminder lead times (days), largest first."""
        self.ensure_one()
        values = []
        for token in (self.reminder_days or "").replace(";", ",").split(","):
            token = token.strip()
            if token.isdigit():
                values.append(int(token))
        return sorted(set(values), reverse=True)

    def action_approve(self):
        self.write({"state": "approved"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_open_matrix(self):
        """Open the 12-month matrix filtered on this plan."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ตารางแผนงาน ISO ทั้งปี"),
            "res_model": "od19.iso.annual.plan.line",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id},
        }


class IsoAnnualPlanLine(models.Model):
    """กิจกรรมหนึ่งรายการในแผนงาน ISO (a row of the yearly matrix)."""

    _name = "od19.iso.annual.plan.line"
    _description = "ISO Annual Plan Activity"
    _order = "sequence, id"

    plan_id = fields.Many2one(
        "od19.iso.annual.plan",
        string="แผนงาน",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    activity_type_id = fields.Many2one(
        "od19.iso.plan.activity.type",
        string="ประเภทกิจกรรม",
        required=True,
    )
    name = fields.Char(string="กิจกรรม", required=True)
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบ")
    department_id = fields.Many2one("hr.department", string="แผนก")
    frequency = fields.Selection(
        FREQUENCY, string="ความถี่", default="annual"
    )
    year = fields.Integer(
        string="ปี", related="plan_id.year", store=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="บริษัท",
        related="plan_id.company_id",
        store=True,
    )
    schedule_ids = fields.One2many(
        "od19.iso.annual.plan.schedule", "line_id", string="กำหนดการรายเดือน"
    )
    note = fields.Text(string="หมายเหตุ")

    # 12 month columns of the yearly matrix (read-only overview).
    month_01 = fields.Selection(MONTH_STATUS, string="ม.ค.", compute="_compute_month_status")
    month_02 = fields.Selection(MONTH_STATUS, string="ก.พ.", compute="_compute_month_status")
    month_03 = fields.Selection(MONTH_STATUS, string="มี.ค.", compute="_compute_month_status")
    month_04 = fields.Selection(MONTH_STATUS, string="เม.ย.", compute="_compute_month_status")
    month_05 = fields.Selection(MONTH_STATUS, string="พ.ค.", compute="_compute_month_status")
    month_06 = fields.Selection(MONTH_STATUS, string="มิ.ย.", compute="_compute_month_status")
    month_07 = fields.Selection(MONTH_STATUS, string="ก.ค.", compute="_compute_month_status")
    month_08 = fields.Selection(MONTH_STATUS, string="ส.ค.", compute="_compute_month_status")
    month_09 = fields.Selection(MONTH_STATUS, string="ก.ย.", compute="_compute_month_status")
    month_10 = fields.Selection(MONTH_STATUS, string="ต.ค.", compute="_compute_month_status")
    month_11 = fields.Selection(MONTH_STATUS, string="พ.ย.", compute="_compute_month_status")
    month_12 = fields.Selection(MONTH_STATUS, string="ธ.ค.", compute="_compute_month_status")

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        for line in self:
            if not line.activity_type_id:
                continue
            if not line.name:
                line.name = line.activity_type_id.name
            if line.activity_type_id.default_frequency:
                line.frequency = line.activity_type_id.default_frequency

    @api.depends(
        "schedule_ids.status",
        "schedule_ids.month",
        "schedule_ids.planned_date",
    )
    def _compute_month_status(self):
        """Aggregate the monthly schedules into the 12 matrix columns."""
        priority = {"overdue": 3, "in_progress": 2, "planned": 1, "done": 0}
        today = fields.Date.today()
        for line in self:
            best = {}
            result = {}
            for sched in line.schedule_ids:
                status = sched._get_display_status(today)
                rank = priority.get(status, -1)
                if rank > best.get(sched.month, -2):
                    best[sched.month] = rank
                    result[sched.month] = status
            for month, _label in MONTH_SELECTION:
                setattr(line, "month_%s" % month, result.get(month, False))
