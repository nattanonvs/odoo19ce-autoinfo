# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบตัวเฝ้าชั้นนอก (P1): การรับ heartbeat สถานะตามความสด และสรุปภาพรวม."""

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestHealthWatchdog(TransactionCase):
    """ทดสอบวงจร heartbeat และการประเมินความสดของตัวเฝ้าชั้นนอก."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["od19.health.watchdog"].search([]).unlink()

    def _make(self, code, max_age=30, **kwargs):
        vals = {"name": code, "code": code, "max_age_minutes": max_age}
        vals.update(kwargs)
        return self.env["od19.health.watchdog"].create(vals)

    # ------------------------- การรับสัญญาณ -------------------------
    def test_register_creates_watchdog(self):
        Watchdog = self.env["od19.health.watchdog"]
        wd = Watchdog.register_heartbeat("wb-chan", status="ok", message="hi")
        self.assertTrue(wd.exists())
        self.assertEqual(wd.code, "wb-chan")
        self.assertEqual(wd.heartbeat_count, 1)
        self.assertEqual(wd.last_status, "ok")
        self.assertTrue(wd.last_heartbeat)

    def test_register_updates_existing(self):
        Watchdog = self.env["od19.health.watchdog"]
        first = Watchdog.register_heartbeat("wb-chan", status="ok")
        second = Watchdog.register_heartbeat("wb-chan", status="warning")
        self.assertEqual(first, second)
        self.assertEqual(second.heartbeat_count, 2)
        self.assertEqual(second.last_status, "warning")
        self.assertEqual(Watchdog.search_count([("code", "=", "wb-chan")]), 1)

    def test_register_invalid_status_falls_back_unknown(self):
        Watchdog = self.env["od19.health.watchdog"]
        wd = Watchdog.register_heartbeat("wb-chan", status="bogus")
        self.assertEqual(wd.last_status, "unknown")

    def test_register_truncates_message(self):
        Watchdog = self.env["od19.health.watchdog"]
        wd = Watchdog.register_heartbeat("wb-chan", message="x" * 500)
        self.assertEqual(len(wd.last_message), 255)

    def test_register_stores_payload(self):
        Watchdog = self.env["od19.health.watchdog"]
        wd = Watchdog.register_heartbeat("wb-chan", payload={"cpu": 42})
        self.assertEqual(wd.last_payload, {"cpu": 42})

    # ------------------------- สถานะตามความสด -------------------------
    def test_heartbeat_state_unknown_without_heartbeat(self):
        wd = self._make("wb-chan")
        self.assertEqual(wd._heartbeat_state(), "unknown")

    def test_heartbeat_state_zero_limit_is_ok(self):
        wd = self._make("wb-chan", max_age=0)
        wd.write({"last_heartbeat": fields.Datetime.now()})
        self.assertEqual(wd._heartbeat_state(), "ok")

    def test_heartbeat_state_reflects_age(self):
        now = fields.Datetime.now()
        wd = self._make("wb-chan", max_age=30)
        wd.write({"last_heartbeat": now - timedelta(minutes=10)})
        self.assertEqual(wd._heartbeat_state(), "ok")
        wd.write({"last_heartbeat": now - timedelta(minutes=45)})
        self.assertEqual(wd._heartbeat_state(), "warning")
        wd.write({"last_heartbeat": now - timedelta(minutes=90)})
        self.assertEqual(wd._heartbeat_state(), "critical")

    def test_action_report_ping(self):
        wd = self._make("wb-chan")
        self.assertTrue(wd.action_report_ping())
        self.assertEqual(wd.heartbeat_count, 1)
        self.assertEqual(wd.last_status, "ok")

    # ------------------------- สรุปภาพรวม -------------------------
    def test_heartbeat_summary(self):
        Watchdog = self.env["od19.health.watchdog"]
        Watchdog.register_heartbeat("wb-fresh", status="ok")
        stale = self._make("wb-stale", max_age=30)
        stale.write({"last_heartbeat": fields.Datetime.now() - timedelta(minutes=90)})
        self._make("wb-never")
        summary = Watchdog._heartbeat_summary()
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["never_seen"], 1)
        self.assertGreaterEqual(summary["worst_age_minutes"], 89)
        self.assertIn("wb-stale", summary["stale_codes"])
        self.assertNotIn("wb-fresh", summary["stale_codes"])

    # ------------------------- ข้อจำกัด -------------------------
    def test_unique_code_constraint(self):
        self._make("wb-dup")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self._make("wb-dup")
            self.env.flush_all()
