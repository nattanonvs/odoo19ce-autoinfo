# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIsoNonconformity(TransactionCase):
    """Tests for ISO nonconformity and CAPA records."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.NC = cls.env["od19.iso.nonconformity"]
        cls.Action = cls.env["od19.iso.nc.action"]
        cls.dept = cls.env["hr.department"].create({"name": "Production"})

    def _create_nc(self, **overrides):
        vals = {
            "title": "Nonconformity on line 1",
            "severity": "minor",
            "source": "process",
            "category": "quality",
            "description": "Dimension out of tolerance",
            "department_id": self.dept.id,
        }
        vals.update(overrides)
        return self.NC.create(vals)

    def test_nc_defaults(self):
        nc = self._create_nc()
        self.assertEqual(nc.state, "draft")
        self.assertTrue(nc.name)
        self.assertNotEqual(nc.name, "/")
        self.assertFalse(nc.effective)

    def test_nc_state_flow(self):
        nc = self._create_nc()

        nc.action_open()
        self.assertEqual(nc.state, "open")

        nc.action_analysis()
        self.assertEqual(nc.state, "analysis")

        nc.action_action()
        self.assertEqual(nc.state, "action")

        nc.action_verification()
        self.assertEqual(nc.state, "verification")

        nc.action_reset_to_draft()
        self.assertEqual(nc.state, "draft")

        nc.action_cancel()
        self.assertEqual(nc.state, "cancel")

    def test_nc_date_constraint(self):
        with self.assertRaises(ValidationError):
            self._create_nc(
                due_date="2026-01-01",
                action_date="2026-02-01",
            )

    def test_close_without_verification_date_raises(self):
        nc = self._create_nc()
        nc.action_verification()
        with self.assertRaises(ValidationError):
            nc.action_close()

    def test_close_with_verification_date_succeeds(self):
        nc = self._create_nc()
        nc.action_verification()
        nc.verification_date = fields.Date.today()
        nc.action_close()
        self.assertEqual(nc.state, "closed")
        self.assertTrue(nc.close_date)
        self.assertEqual(nc.closed_by_id, self.env.user)

    def _nc_activities(self, nc):
        return self.env["mail.activity"].search([
            ("res_model", "=", "od19.iso.nonconformity"),
            ("res_id", "=", nc.id),
        ])

    def test_cron_due_reminder_creates_activity(self):
        nc = self._create_nc(
            due_date=fields.Date.add(fields.Date.today(), days=3)
        )
        nc.action_open()
        self.NC._cron_nc_due_reminder()
        self.assertTrue(self._nc_activities(nc))

    def test_cron_overdue_reminder_creates_activity(self):
        nc = self._create_nc(
            due_date=fields.Date.add(fields.Date.today(), days=-1)
        )
        nc.action_action()
        self.NC._cron_nc_due_reminder()
        self.assertTrue(self._nc_activities(nc))

    def test_cron_reminder_is_idempotent(self):
        nc = self._create_nc(
            due_date=fields.Date.add(fields.Date.today(), days=3)
        )
        nc.action_open()
        self.NC._cron_nc_due_reminder()
        count = len(self._nc_activities(nc))
        self.NC._cron_nc_due_reminder()
        self.assertEqual(len(self._nc_activities(nc)), count)

    def test_cron_ignores_closed_nc(self):
        nc = self._create_nc(
            due_date=fields.Date.add(fields.Date.today(), days=3)
        )
        nc.action_verification()
        nc.verification_date = fields.Date.today()
        nc.action_close()
        self.NC._cron_nc_due_reminder()
        self.assertFalse(self._nc_activities(nc))


class TestIsoNcAction(TransactionCase):
    """Tests for CAPA action plan items."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.NC = cls.env["od19.iso.nonconformity"]
        cls.Action = cls.env["od19.iso.nc.action"]
        cls.nc = cls.NC.create(
            {
                "title": "NC with actions",
                "severity": "major",
                "source": "internal_audit",
                "category": "process",
                "description": "Process deviation",
            }
        )

    def test_action_defaults(self):
        action = self.Action.create(
            {
                "nc_id": self.nc.id,
                "action": "Retrain operators",
            }
        )
        self.assertEqual(action.action_type, "corrective")
        self.assertEqual(action.status, "pending")
        self.assertIn(action, self.nc.action_plan_ids)

    def test_action_status_flow(self):
        action = self.Action.create(
            {
                "nc_id": self.nc.id,
                "action": "Revise work instruction",
                "action_type": "preventive",
            }
        )

        action.action_in_progress()
        self.assertEqual(action.status, "in_progress")

        action.action_done()
        self.assertEqual(action.status, "done")
        self.assertTrue(action.done_date)
