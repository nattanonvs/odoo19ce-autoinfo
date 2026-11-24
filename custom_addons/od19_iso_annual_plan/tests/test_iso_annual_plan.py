# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIsoAnnualPlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Plan = cls.env["od19.iso.annual.plan"]
        cls.Line = cls.env["od19.iso.annual.plan.line"]
        cls.Schedule = cls.env["od19.iso.annual.plan.schedule"]
        cls.Dept = cls.env["hr.department"]

        cls.today = fields.Date.today()
        cls.dept = cls.Dept.create({"name": "Quality", "code": "QA"})
        cls.activity_audit = cls.env.ref(
            "od19_iso_annual_plan.plan_activity_internal_audit"
        )
        cls.activity_mgmt = cls.env.ref(
            "od19_iso_annual_plan.plan_activity_management_review"
        )
        cls.plan = cls.Plan.create(
            {
                "name": "ISO Plan %s" % cls.today.year,
                "year": cls.today.year,
                "responsible_id": cls.env.user.id,
            }
        )

    def _create_line(self, **overrides):
        vals = {
            "plan_id": self.plan.id,
            "activity_type_id": self.activity_audit.id,
            "name": self.activity_audit.name,
            "department_id": self.dept.id,
        }
        vals.update(overrides)
        return self.Line.create(vals)

    def _create_schedule(self, line, month, planned_date, status="not_started"):
        return self.Schedule.create(
            {
                "line_id": line.id,
                "month": month,
                "planned_date": planned_date,
                "status": status,
            }
        )

    # ------------------------------------------------------------------
    # Master data
    # ------------------------------------------------------------------
    def test_standard_activities_seeded(self):
        """The 8 standard ISO activities must be available out of the box."""
        activities = self.env["od19.iso.plan.activity.type"].search([])
        self.assertGreaterEqual(len(activities), 8)
        codes = activities.mapped("code")
        for expected in (
            "AUDIT",
            "MGMT_REVIEW",
            "TRAINING",
            "RISK",
            "CALIBRATION",
            "SUPPLIER_EVAL",
            "SATISFACTION",
            "DOC_REVIEW",
        ):
            self.assertIn(expected, codes)

    def test_onchange_activity_type_fills_defaults(self):
        line = self.Line.new(
            {
                "plan_id": self.plan.id,
                "activity_type_id": self.activity_mgmt.id,
            }
        )
        line._onchange_activity_type_id()
        self.assertEqual(line.name, self.activity_mgmt.name)
        self.assertEqual(
            line.frequency, self.activity_mgmt.default_frequency
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def test_year_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            self.Plan.create({"name": "Bad", "year": 1999})

    def test_invalid_reminder_days_raises(self):
        with self.assertRaises(ValidationError):
            self.Plan.create(
                {
                    "name": "Bad Reminder",
                    "year": self.today.year,
                    "reminder_days": "abc",
                }
            )

    def test_get_reminder_thresholds_parses_and_sorts(self):
        self.plan.reminder_days = "7, 30 , 15"
        self.assertEqual(
            self.plan._get_reminder_thresholds(), [30, 15, 7]
        )
        self.plan.reminder_days = "15;15;30"
        self.assertEqual(
            self.plan._get_reminder_thresholds(), [30, 15]
        )

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def test_display_status_transitions(self):
        future = fields.Date.add(self.today, days=10)
        schedule = self._create_schedule(
            self._create_line(), "03", future, status="not_started"
        )
        self.assertEqual(schedule._get_display_status(), "planned")

        schedule.action_start()
        self.assertEqual(schedule._get_display_status(), "in_progress")

        schedule.action_done()
        self.assertEqual(schedule._get_display_status(), "done")
        self.assertEqual(schedule.completed_date, self.today)
        self.assertFalse(schedule.is_overdue)

    def test_overdue_status_and_flag(self):
        past = fields.Date.add(self.today, days=-5)
        schedule = self._create_schedule(
            self._create_line(), "04", past, status="not_started"
        )
        self.assertEqual(schedule._get_display_status(), "overdue")
        self.assertTrue(schedule.is_overdue)

    # ------------------------------------------------------------------
    # Yearly 12-month matrix
    # ------------------------------------------------------------------
    def test_month_columns_reflect_schedule_status(self):
        line = self._create_line()
        self._create_schedule(
            line, "03", fields.Date.add(self.today, days=45), status="done"
        )
        self._create_schedule(
            line, "05", fields.Date.add(self.today, days=60), status="not_started"
        )
        self.assertEqual(line.month_03, "done")
        self.assertEqual(line.month_05, "planned")
        self.assertFalse(line.month_01)

    def test_month_column_priority_overdue_wins(self):
        line = self._create_line()
        self._create_schedule(
            line, "06", fields.Date.add(self.today, days=90), status="done"
        )
        self._create_schedule(
            line, "06", fields.Date.add(self.today, days=-2), status="not_started"
        )
        self.assertEqual(line.month_06, "overdue")

    # ------------------------------------------------------------------
    # Reminders (daily cron)
    # ------------------------------------------------------------------
    def test_cron_creates_due_reminder_once(self):
        line = self._create_line()
        schedule = self._create_schedule(
            line, "07", fields.Date.add(self.today, days=20), status="not_started"
        )
        self.Schedule._cron_annual_plan_reminder()
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", self.Schedule._name),
                ("res_id", "=", schedule.id),
            ]
        )
        self.assertEqual(len(activities), 1)
        # Running again must not create a duplicate reminder.
        self.Schedule._cron_annual_plan_reminder()
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", self.Schedule._name),
                ("res_id", "=", schedule.id),
            ]
        )
        self.assertEqual(len(activities), 1)

    def test_cron_skips_done_schedule(self):
        line = self._create_line()
        schedule = self._create_schedule(
            line, "08", fields.Date.add(self.today, days=-5), status="done"
        )
        self.Schedule._cron_annual_plan_reminder()
        count = self.env["mail.activity"].search_count(
            [
                ("res_model", "=", self.Schedule._name),
                ("res_id", "=", schedule.id),
            ]
        )
        self.assertEqual(count, 0)

    def test_cron_creates_overdue_reminder(self):
        line = self._create_line()
        schedule = self._create_schedule(
            line, "09", fields.Date.add(self.today, days=-3), status="not_started"
        )
        self.Schedule._cron_annual_plan_reminder()
        activity = self.env["mail.activity"].search(
            [
                ("res_model", "=", self.Schedule._name),
                ("res_id", "=", schedule.id),
            ]
        )
        self.assertEqual(len(activity), 1)
        self.assertIn("เลยกำหนด", activity.summary)
