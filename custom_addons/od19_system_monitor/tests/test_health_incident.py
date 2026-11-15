# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบเหตุการณ์สุขภาพระบบ (P3): dedup, ยกระดับ, รับทราบ/เลื่อน/ปิด."""

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestHealthIncident(TransactionCase):
    """ทดสอบวงจรชีวิตของเหตุการณ์ + การ dedup ตาม fingerprint."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ปิดการตรวจชุดเริ่มต้นเพื่อให้ผลลัพธ์ในแต่ละเทสต์แน่นอน
        cls.env["od19.health.check"].search([]).write({"active": False})
        cls.check = cls.env["od19.health.check"].create(
            {
                "name": "Incident Check",
                "code": "incident_test_check",
                "check_type": "custom",
                "active": True,
            }
        )
        cls.rule = cls.env["od19.health.rule"].create(
            {
                "name": "Incident Rule",
                "check_id": cls.check.id,
                "severity": "critical",
                "check_state": "critical",
                "fingerprint_window_minutes": 60,
            }
        )

    def _measure(self, message="เกิดข้อผิดพลาดที่ระบบ", cron=None):
        details = {}
        if cron:
            details["cron"] = cron
        return {
            "value": 1,
            "value_label": "1",
            "status": "measured",
            "state": "critical",
            "message": message,
            "details": details,
        }

    # ------------------------- fingerprint / dedup -------------------------
    def test_fingerprint_includes_check_rule_target(self):
        Incident = self.env["od19.health.incident"]
        self.assertEqual(
            Incident._fingerprint(self.check, self.rule, "cronA"),
            "incident_test_check|%s|cronA" % self.rule.id,
        )
        # ไม่มี rule และไม่มี target -> ใช้ 0 และค่าว่าง
        self.assertEqual(
            Incident._fingerprint(self.check, None), "incident_test_check|0|"
        )

    def test_open_creates_incident_with_sequence_name(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        self.assertEqual(incident.state, "open")
        self.assertEqual(incident.severity, "critical")
        self.assertEqual(incident.check_state, "critical")
        self.assertEqual(incident.occurrence_count, 1)
        self.assertEqual(incident.check_id, self.check)
        self.assertNotEqual(incident.name, "New")
        # แจ้งเตือนครั้งแรกเมื่อเปิดเหตุใหม่
        self.assertEqual(incident.notification_count, 1)

    def test_open_or_update_dedups_within_window(self):
        Incident = self.env["od19.health.incident"]
        first = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        second = Incident._open_or_update(
            self.check, self.rule, self._measure("ซ้ำอีกครั้ง"), "critical"
        )
        self.assertEqual(first, second)
        self.assertEqual(second.occurrence_count, 2)
        # ยังอยู่ในหน้าต่าง dedup 60 นาที -> นับครั้งแต่ไม่แจ้งซ้ำ
        self.assertEqual(second.notification_count, 1)
        self.assertEqual(
            Incident.search_count([("fingerprint", "=", first.fingerprint)]), 1
        )

    def test_open_or_update_renotifies_after_window(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        # ถอยเวลาแจ้งเตือนล่าสุดให้พ้นหน้าต่าง dedup
        incident.write(
            {"last_notified_at": fields.Datetime.now() - timedelta(minutes=120)}
        )
        Incident._open_or_update(
            self.check, self.rule, self._measure("อีกครั้ง"), "critical"
        )
        self.assertEqual(incident.notification_count, 2)

    def test_unique_open_fingerprint(self):
        Incident = self.env["od19.health.incident"]
        Incident.create({"check_id": self.check.id, "fingerprint": "fp-dup"})
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            Incident.create({"check_id": self.check.id, "fingerprint": "fp-dup"})
            self.env.flush_all()

    def test_open_suppressed_by_maintenance(self):
        now = fields.Datetime.now()
        self.env["od19.health.maintenance"].create(
            {
                "name": "ซ่อมบำรุง",
                "start_datetime": now - timedelta(hours=1),
                "end_datetime": now + timedelta(hours=1),
                "check_ids": [(6, 0, [self.check.id])],
            }
        )
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        # เปิดเหตุได้ แต่ไม่แจ้งเตือนเพราะอยู่ในหน้าต่างซ่อมบำรุง
        self.assertEqual(incident.state, "open")
        self.assertEqual(incident.notification_count, 0)

    # ------------------------- ปิดอัตโนมัติ -------------------------
    def test_auto_resolve_closes_open_incident(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        self.assertEqual(Incident._auto_resolve(self.check, "ok"), 1)
        self.assertEqual(incident.state, "closed")
        self.assertEqual(incident.close_reason, "resolved")

    def test_auto_resolve_ignores_non_ok_state(self):
        Incident = self.env["od19.health.incident"]
        Incident._open_or_update(self.check, self.rule, self._measure(), "critical")
        self.assertEqual(Incident._auto_resolve(self.check, "warning"), 0)

    def test_auto_resolve_keeps_active_snooze(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        incident.action_snooze(hours=4)
        self.assertEqual(Incident._auto_resolve(self.check, "ok"), 0)
        self.assertEqual(incident.state, "snoozed")

    # ------------------------- ปุ่มบนหน้าจอ -------------------------
    def test_action_acknowledge(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        self.assertTrue(incident.action_acknowledge())
        self.assertEqual(incident.state, "acknowledged")
        self.assertEqual(incident.acknowledged_by, self.env.user)
        self.assertTrue(incident.acknowledged_at)

    def test_action_snooze_sets_until(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        incident.action_snooze(hours=2)
        self.assertEqual(incident.state, "snoozed")
        self.assertTrue(incident.snoozed_until)

    def test_action_close_manual(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        self.assertTrue(incident.action_close())
        self.assertEqual(incident.state, "closed")
        self.assertEqual(incident.close_reason, "manual")

    def test_actions_reject_closed_incident(self):
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, self.rule, self._measure(), "critical"
        )
        incident.action_close()
        with self.assertRaises(UserError):
            incident.action_acknowledge()
        with self.assertRaises(UserError):
            incident.action_snooze()

    # ------------------------- การยกระดับ -------------------------
    def test_cron_escalate_promotes_severity(self):
        rule = self.env["od19.health.rule"].create(
            {
                "name": "Escalating Rule",
                "check_id": self.check.id,
                "severity": "warning",
                "check_state": "warning",
                "escalate_after_minutes": 1,
                "escalate_severity": "critical",
            }
        )
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, rule, self._measure(), "warning"
        )
        incident.write({"first_seen": fields.Datetime.now() - timedelta(minutes=5)})
        Incident._cron_escalate()
        self.assertTrue(incident.escalated)
        self.assertEqual(incident.severity, "critical")
        self.assertEqual(incident.previous_severity, "warning")
        self.assertTrue(incident.escalated_at)

    def test_cron_escalate_skips_acknowledged(self):
        rule = self.env["od19.health.rule"].create(
            {
                "name": "Escalating Rule 2",
                "check_id": self.check.id,
                "severity": "warning",
                "check_state": "warning",
                "escalate_after_minutes": 1,
                "escalate_severity": "critical",
            }
        )
        Incident = self.env["od19.health.incident"]
        incident = Incident._open_or_update(
            self.check, rule, self._measure(), "warning"
        )
        incident.action_acknowledge()
        incident.write({"first_seen": fields.Datetime.now() - timedelta(minutes=5)})
        Incident._cron_escalate()
        self.assertFalse(incident.escalated)

    # ------------------------- สรุปรายวัน -------------------------
    def test_send_digest_returns_body(self):
        Incident = self.env["od19.health.incident"]
        Incident._open_or_update(self.check, self.rule, self._measure(), "critical")
        body = Incident._send_digest()
        self.assertIn("สรุปสุขภาพระบบ", body)
        self.assertIn(self.check.name, body)
