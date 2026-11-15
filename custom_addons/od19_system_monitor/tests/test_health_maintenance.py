# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบหน้าต่างซ่อมบำรุง (P3): สถานะตามเวลา และการระงับการแจ้งเตือน."""

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHealthMaintenance(TransactionCase):
    """ทดสอบการระงับการแจ้งเตือนระหว่างหน้าต่างซ่อมบำรุง."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["od19.health.maintenance"].search([]).unlink()
        cls.check = cls.env["od19.health.check"].create(
            {"name": "Win Check", "code": "window_check", "check_type": "custom"}
        )
        cls.other = cls.env["od19.health.check"].create(
            {"name": "Other Check", "code": "window_other", "check_type": "custom"}
        )

    def _window(self, start, end, **kwargs):
        vals = {"name": "หน้าต่าง", "start_datetime": start, "end_datetime": end}
        vals.update(kwargs)
        return self.env["od19.health.maintenance"].create(vals)

    # ------------------------- สถานะตามเวลา -------------------------
    def test_state_scheduled(self):
        now = fields.Datetime.now()
        win = self._window(now + timedelta(hours=1), now + timedelta(hours=2))
        self.assertEqual(win.state, "scheduled")

    def test_state_running(self):
        now = fields.Datetime.now()
        win = self._window(now - timedelta(hours=1), now + timedelta(hours=1))
        self.assertEqual(win.state, "running")

    def test_state_done(self):
        now = fields.Datetime.now()
        win = self._window(now - timedelta(hours=2), now - timedelta(hours=1))
        self.assertEqual(win.state, "done")

    # ------------------------- การระงับการแจ้งเตือน -------------------------
    def test_is_suppressed_all_checks_when_empty(self):
        now = fields.Datetime.now()
        self._window(now - timedelta(hours=1), now + timedelta(hours=1))
        Maintenance = self.env["od19.health.maintenance"]
        self.assertTrue(Maintenance.is_suppressed(self.check))
        self.assertTrue(Maintenance.is_suppressed(self.other))

    def test_is_suppressed_only_listed_checks(self):
        now = fields.Datetime.now()
        self._window(
            now - timedelta(hours=1),
            now + timedelta(hours=1),
            check_ids=[(6, 0, [self.check.id])],
        )
        Maintenance = self.env["od19.health.maintenance"]
        self.assertTrue(Maintenance.is_suppressed(self.check))
        self.assertFalse(Maintenance.is_suppressed(self.other))

    def test_is_suppressed_outside_window(self):
        now = fields.Datetime.now()
        self._window(now - timedelta(hours=2), now - timedelta(hours=1))
        self.assertFalse(
            self.env["od19.health.maintenance"].is_suppressed(self.check)
        )

    def test_is_suppressed_respects_suppress_flag(self):
        now = fields.Datetime.now()
        self._window(
            now - timedelta(hours=1),
            now + timedelta(hours=1),
            suppress_notifications=False,
        )
        self.assertFalse(
            self.env["od19.health.maintenance"].is_suppressed(self.check)
        )

    def test_is_suppressed_respects_active(self):
        now = fields.Datetime.now()
        self._window(
            now - timedelta(hours=1), now + timedelta(hours=1), active=False
        )
        self.assertFalse(
            self.env["od19.health.maintenance"].is_suppressed(self.check)
        )
