# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models

from .iso_annual_plan import MONTH_SELECTION, MONTH_THAI

_logger = logging.getLogger(__name__)


SCHEDULE_STATUS = [
    ("not_started", "ยังไม่เริ่ม"),
    ("in_progress", "กำลังทำ"),
    ("done", "เสร็จ"),
]


class IsoAnnualPlanSchedule(models.Model):
    """กำหนดการของกิจกรรมในแต่ละเดือน (one month occurrence of a plan line).

    Holds the real planned date, owner and progress for a single month of an
    activity; the 12-month matrix columns of the plan line are derived from
    these records.
    """

    _name = "od19.iso.annual.plan.schedule"
    _description = "ISO Annual Plan Schedule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "line_id, month"
    _rec_name = "display_name"

    line_id = fields.Many2one(
        "od19.iso.annual.plan.line",
        string="กิจกรรม",
        required=True,
        ondelete="cascade",
    )
    plan_id = fields.Many2one(
        "od19.iso.annual.plan",
        string="แผนงาน",
        related="line_id.plan_id",
        store=True,
    )
    activity_type_id = fields.Many2one(
        "od19.iso.plan.activity.type",
        string="ประเภทกิจกรรม",
        related="line_id.activity_type_id",
        store=True,
    )
    month = fields.Selection(MONTH_SELECTION, string="เดือน", required=True)
    planned_date = fields.Date(string="วันที่ตามแผน")
    status = fields.Selection(
        SCHEDULE_STATUS,
        string="สถานะ",
        default="not_started",
        required=True,
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="ผู้รับผิดชอบ",
        help="เว้นว่างไว้เพื่อใช้ผู้รับผิดชอบของกิจกรรม/แผนงาน",
    )
    completed_date = fields.Date(string="วันที่เสร็จ")
    note = fields.Text(string="หมายเหตุ")
    company_id = fields.Many2one(
        "res.company",
        string="บริษัท",
        related="line_id.company_id",
        store=True,
    )
    is_overdue = fields.Boolean(string="เลยกำหนด", compute="_compute_is_overdue", search="_search_is_overdue")
    display_name = fields.Char(
        string="ชื่อแสดงผล", compute="_compute_display_name", store=True
    )

    @api.depends("line_id.name", "month")
    def _compute_display_name(self):
        for schedule in self:
            month_label = MONTH_THAI.get(schedule.month, "")
            schedule.display_name = "%s - %s" % (
                schedule.line_id.name or "",
                month_label,
            )

    @api.depends("planned_date", "status")
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for schedule in self:
            schedule.is_overdue = (
                schedule._get_display_status(today) == "overdue"
            )

    def _search_is_overdue(self, operator, value):
        """Searchable helper so the matrix/list can filter overdue rows."""
        today = fields.Date.today()
        overdue = [("planned_date", "<", today), ("status", "!=", "done")]
        if (operator, value) in (("=", True), ("!=", False)):
            return overdue
        return [
            "|",
            ("planned_date", ">=", today),
            "|",
            ("planned_date", "=", False),
            ("status", "=", "done"),
        ]

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def _get_display_status(self, today=None):
        """Return the matrix status (planned/in_progress/done/overdue)."""
        self.ensure_one()
        today = today or fields.Date.today()
        if self.status == "done":
            return "done"
        if self.planned_date and self.planned_date < today:
            return "overdue"
        if self.status == "in_progress":
            return "in_progress"
        return "planned"

    def action_start(self):
        self.write({"status": "in_progress"})

    def action_done(self):
        self.write({"status": "done", "completed_date": fields.Date.today()})

    def action_reset(self):
        self.write({"status": "not_started", "completed_date": False})

    # ------------------------------------------------------------------
    # Reminder plumbing
    # ------------------------------------------------------------------
    def _get_responsible_user(self):
        self.ensure_one()
        return (
            self.responsible_id
            or self.line_id.responsible_id
            or self.plan_id.responsible_id
            or self.env.user
        )

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
        """Create a mail.activity for the responsible user."""
        self.ensure_one()
        activity_type = self.env.ref(
            activity_type_xmlid, raise_if_not_found=False
        )
        user = self._get_responsible_user()
        if not user:
            return False
        return self.env["mail.activity"].sudo().create(
            {
                "activity_type_id": activity_type.id if activity_type else False,
                "summary": summary,
                "note": note,
                "user_id": user.id,
                "res_model_id": self.env["ir.model"]._get_id(self._name),
                "res_id": self.id,
                "date_deadline": fields.Date.today(),
            }
        )

    def _notify_channels(self, message, event, subject):
        """Push the reminder through the multi-channel notification service."""
        self.ensure_one()
        partner = self._get_responsible_user().partner_id
        if not partner:
            return
        try:
            service = self.env["notification.service"]
        except KeyError:  # notification module not installed
            self.message_post(body=message, partner_ids=partner.ids)
            return
        service.notify(partner, message, event=event, subject=subject)

    def _notify_due(self, threshold, days_left):
        """Create the reminder for a schedule approaching its planned date."""
        self.ensure_one()
        tag = _("แผนงาน ISO ใกล้ถึงกำหนด (ล่วงหน้า %s วัน)") % threshold
        summary = "%s: %s" % (tag, self.display_name)
        if self._has_open_activity(summary):
            return
        note = _(
            "กิจกรรม '%(activity)s' (%(month)s) กำหนดดำเนินการภายใน %(days)s วัน "
            "(วันที่ตามแผน: %(date)s) ผู้รับผิดชอบ: %(user)s"
        ) % {
            "activity": self.line_id.name,
            "month": MONTH_THAI.get(self.month, ""),
            "days": days_left,
            "date": self.planned_date,
            "user": self._get_responsible_user().name,
        }
        self._create_reminder_activity(
            "mail.mail_activity_data_todo", summary, note
        )
        self.message_post(body=note)
        self._notify_channels(note, "iso_annual_plan_due", summary)

    def _notify_overdue(self, overdue_days):
        """Create the reminder for a schedule that is past its planned date."""
        self.ensure_one()
        tag = _("แผนงาน ISO เลยกำหนด")
        summary = "%s: %s" % (tag, self.display_name)
        if self._has_open_activity(summary):
            return
        note = _(
            "กิจกรรม '%(activity)s' (%(month)s) เลยกำหนดมาแล้ว %(days)s วัน "
            "(วันที่ตามแผน: %(date)s) ผู้รับผิดชอบ: %(user)s"
        ) % {
            "activity": self.line_id.name,
            "month": MONTH_THAI.get(self.month, ""),
            "days": overdue_days,
            "date": self.planned_date,
            "user": self._get_responsible_user().name,
        }
        self._create_reminder_activity(
            "mail.mail_activity_data_warning", summary, note
        )
        self.message_post(body=note)
        self._notify_channels(note, "iso_annual_plan_overdue", summary)

    @api.model
    def _cron_annual_plan_reminder(self):
        """Daily cron: remind owners about upcoming and overdue plan items.

        For each open plan, a schedule approaching its planned date fires a
        single reminder at the closest configured lead time (e.g. 30/15/7
        days), and an overdue schedule fires an overdue reminder.
        """
        today = fields.Date.today()
        plans = self.env["od19.iso.annual.plan"].search(
            [
                ("state", "in", ["draft", "approved"]),
                ("year", ">=", today.year),
            ]
        )
        for plan in plans:
            thresholds = plan._get_reminder_thresholds()
            if not thresholds:
                continue
            due_limit = fields.Date.add(today, days=max(thresholds))

            due_schedules = self.search(
                [
                    ("plan_id", "=", plan.id),
                    ("status", "!=", "done"),
                    ("planned_date", ">=", today),
                    ("planned_date", "<=", due_limit),
                ]
            )
            for schedule in due_schedules:
                days_left = (schedule.planned_date - today).days
                threshold = next(
                    (t for t in sorted(thresholds) if t >= days_left), None
                )
                if threshold is None:
                    continue
                schedule._notify_due(threshold, days_left)

            overdue_schedules = self.search(
                [
                    ("plan_id", "=", plan.id),
                    ("status", "!=", "done"),
                    ("planned_date", "<", today),
                ]
            )
            for schedule in overdue_schedules:
                schedule._notify_overdue(
                    (today - schedule.planned_date).days
                )
