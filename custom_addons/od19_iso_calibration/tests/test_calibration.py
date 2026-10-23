# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCalibrationCron(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Equipment = cls.env["od19.iso.calibration.equipment"]
        cls.CalRecord = cls.env["od19.iso.calibration.record"]

        cls.employee = cls.env["hr.employee"].create(
            {"name": "Calibration Owner", "user_id": cls.env.user.id}
        )
        cls.department = cls.env["hr.department"].create(
            {"name": "QA", "manager_id": cls.employee.id}
        )

    def _make_equipment(self, next_date, **overrides):
        # ``next_calibration_date`` is a stored computed field (last date +
        # interval), so it must be reached through its dependencies.
        interval = overrides.pop("calibration_interval", 365)
        vals = {
            "name": "Test Caliper",
            "code": "EQ-001",
            "category": "dimensional",
            "owner_id": self.employee.id,
            "department_id": self.department.id,
            "calibration_interval": interval,
            "last_calibration_date": next_date - timedelta(days=interval),
        }
        vals.update(overrides)
        return self.Equipment.create(vals)

    # ------------------------------------------------------------------
    # Overdue flag
    # ------------------------------------------------------------------
    def test_overdue_flag_set_when_next_date_passed(self):
        eq = self._make_equipment(fields.Date.today() - timedelta(days=1))
        self.assertTrue(eq.is_overdue)
        self.assertEqual(eq.calibration_status, "overdue")

    def test_not_overdue_when_future(self):
        eq = self._make_equipment(fields.Date.today() + timedelta(days=365))
        self.assertFalse(eq.is_overdue)
        self.assertEqual(eq.calibration_status, "calibrated")

    # ------------------------------------------------------------------
    # Cron reminders
    # ------------------------------------------------------------------
    def test_cron_creates_activity_for_due_equipment(self):
        eq = self._make_equipment(fields.Date.today() + timedelta(days=3))
        before = self.env["mail.activity"].search_count(
            [("res_model", "=", "od19.iso.calibration.equipment"),
             ("res_id", "=", eq.id)]
        )
        self.Equipment._cron_calibration_due_reminder(days=7)
        after = self.env["mail.activity"].search_count(
            [("res_model", "=", "od19.iso.calibration.equipment"),
             ("res_id", "=", eq.id)]
        )
        self.assertGreater(after, before)
        self.assertTrue(eq.reminder_sent)

    def test_cron_no_reminder_for_far_future(self):
        eq = self._make_equipment(fields.Date.today() + timedelta(days=300))
        before = self.env["mail.activity"].search_count(
            [("res_model", "=", "od19.iso.calibration.equipment"),
             ("res_id", "=", eq.id)]
        )
        self.Equipment._cron_calibration_due_reminder(days=7)
        after = self.env["mail.activity"].search_count(
            [("res_model", "=", "od19.iso.calibration.equipment"),
             ("res_id", "=", eq.id)]
        )
        self.assertEqual(after, before)

    def test_cron_overdue_creates_activity(self):
        eq = self._make_equipment(fields.Date.today() - timedelta(days=2))
        before = self.env["mail.activity"].search_count(
            [("res_model", "=", "od19.iso.calibration.equipment"),
             ("res_id", "=", eq.id)]
        )
        self.Equipment._cron_calibration_due_reminder(days=7)
        after = self.env["mail.activity"].search_count(
            [("res_model", "=", "od19.iso.calibration.equipment"),
             ("res_id", "=", eq.id)]
        )
        self.assertGreater(after, before)

    def test_reminder_sent_reset_after_pass(self):
        eq = self._make_equipment(fields.Date.today() + timedelta(days=3))
        self.Equipment._cron_calibration_due_reminder(days=7)
        self.assertTrue(eq.reminder_sent)

        record = self.CalRecord.create(
            {
                "equipment_id": eq.id,
                "date": fields.Date.today(),
                "calibration_type": "external",
                "status": "draft",
            }
        )
        record.action_pass()
        self.assertFalse(eq.reminder_sent)
