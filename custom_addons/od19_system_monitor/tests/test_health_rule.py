# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from psycopg2 import IntegrityError

from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestHealthRule(TransactionCase):
    """ทดสอบเกณฑ์สุขภาพ (rule engine): การจับคู่ การเลือกกฎ และผู้รับ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.check = cls.env["od19.health.check"].create(
            {"name": "Rule Check", "code": "rule_test_check", "check_type": "custom"}
        )

    def _make_rule(self, **kwargs):
        vals = {"name": "Rule", "check_id": self.check.id}
        vals.update(kwargs)
        return self.env["od19.health.rule"].create(vals)

    # ------------------------- การจับคู่ -------------------------
    def test_matches_value(self):
        rule = self._make_rule(metric="value", operator="gt", threshold=10)
        self.assertTrue(rule._matches({"value": 20}))
        self.assertFalse(rule._matches({"value": 5}))

    def test_matches_status(self):
        rule = self._make_rule(metric="status", operator="eq", threshold_text="down")
        self.assertTrue(rule._matches({"status": "down"}))
        self.assertFalse(rule._matches({"status": "ok"}))

    def test_matches_message_contains(self):
        rule = self._make_rule(
            metric="message", operator="contains", threshold_text="error"
        )
        self.assertTrue(rule._matches({"message": "an error happened"}))
        self.assertFalse(rule._matches({"message": "all good"}))

    def test_matches_always(self):
        rule = self._make_rule(metric="always")
        self.assertTrue(rule._matches({}))

    # ------------------------- การเลือกกฎ -------------------------
    def test_rank(self):
        self.assertEqual(self._make_rule(severity="info")._rank(), 10)
        self.assertEqual(self._make_rule(severity="critical")._rank(), 30)

    def test_pick_rule_highest_severity(self):
        self._make_rule(metric="always", severity="warning")
        top = self._make_rule(metric="always", severity="critical")
        picked = self.env["od19.health.rule"]._pick_rule(self.check, {"value": 0})
        self.assertEqual(picked.id, top.id)

    def test_pick_rule_none_when_no_match(self):
        self._make_rule(metric="value", operator="gt", threshold=100)
        picked = self.env["od19.health.rule"]._pick_rule(self.check, {"value": 1})
        self.assertFalse(picked)

    # ------------------------- ผู้รับ -------------------------
    def test_partners_from_group_and_user(self):
        group = self.env["res.groups"].create({"name": "Health Rule Test Group"})
        group_user = self.env["res.users"].create(
            {
                "name": "Health Group User",
                "login": "health_rule_group_user",
                "group_ids": [Command.link(group.id)],
            }
        )
        extra_user = self.env["res.users"].create(
            {
                "name": "Health Extra User",
                "login": "health_rule_extra_user",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        rule = self._make_rule(
            notify_group_ids=[Command.link(group.id)],
            notify_user_ids=[Command.link(extra_user.id)],
        )
        partners = rule._partners()
        self.assertIn(group_user.partner_id, partners)
        self.assertIn(extra_user.partner_id, partners)

    # ------------------------- ข้อจำกัด -------------------------
    def test_escalate_requires_severity(self):
        # CHECK constraint: เปิดยกระดับ (escalate_after_minutes > 0) ต้องระบุปลายทาง
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self._make_rule(escalate_after_minutes=5)
            self.env.flush_all()

    def test_escalate_with_severity_allowed(self):
        rule = self._make_rule(
            escalate_after_minutes=5, escalate_severity="emergency"
        )
        self.assertTrue(rule.id)
