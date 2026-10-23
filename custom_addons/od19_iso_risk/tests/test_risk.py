# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.tests.common import TransactionCase


class TestIsoRisk(TransactionCase):
    """Basic tests for ISO Risk & Opportunity management."""

    def _create_risk(self, **overrides):
        vals = {
            "title": "Test Risk",
            "risk_type": "risk",
            "category": "operational",
            "description": "Test risk description",
        }
        vals.update(overrides)
        return self.env["od19.iso.risk"].create(vals)

    def test_create_risk_with_minimal_fields(self):
        risk = self._create_risk()
        self.assertTrue(risk)
        self.assertEqual(risk.title, "Test Risk")
        self.assertEqual(risk.state, "draft")

    def test_risk_score_computation(self):
        risk = self._create_risk(likelihood="3", severity="4")
        self.assertEqual(risk.risk_score, 12)

    def test_risk_score_zero_when_no_values(self):
        risk = self._create_risk()
        self.assertEqual(risk.risk_score, 0)

    def test_risk_level_critical(self):
        risk = self._create_risk(likelihood="5", severity="5")
        self.assertEqual(risk.risk_score, 25)
        self.assertEqual(risk.risk_level, "critical")

    def test_risk_level_high(self):
        risk = self._create_risk(likelihood="3", severity="4")
        self.assertEqual(risk.risk_score, 12)
        self.assertEqual(risk.risk_level, "high")

    def test_risk_level_medium(self):
        risk = self._create_risk(likelihood="2", severity="3")
        self.assertEqual(risk.risk_score, 6)
        self.assertEqual(risk.risk_level, "medium")

    def test_risk_level_low(self):
        risk = self._create_risk(likelihood="1", severity="2")
        self.assertEqual(risk.risk_score, 2)
        self.assertEqual(risk.risk_level, "low")

    def test_residual_score_computation(self):
        risk = self._create_risk(residual_likelihood="2", residual_severity="2")
        self.assertEqual(risk.residual_score, 4)

    def test_state_transitions(self):
        risk = self._create_risk()
        self.assertEqual(risk.state, "draft")

        risk.action_identified()
        self.assertEqual(risk.state, "identified")

        risk.action_analyzed()
        self.assertEqual(risk.state, "analyzed")

        risk.action_evaluated()
        self.assertEqual(risk.state, "evaluated")

        risk.action_treated()
        self.assertEqual(risk.state, "treated")

        risk.action_monitored()
        self.assertEqual(risk.state, "monitored")

        risk.action_close()
        self.assertEqual(risk.state, "closed")
        self.assertTrue(risk.close_date)

    def test_cancel_and_reset(self):
        risk = self._create_risk()
        risk.action_cancel()
        self.assertEqual(risk.state, "cancel")

        risk.action_reset_to_draft()
        self.assertEqual(risk.state, "draft")

    def test_create_risk_action(self):
        risk = self._create_risk()
        action = self.env["od19.iso.risk.action"].create({
            "risk_id": risk.id,
            "action": "Mitigate the risk",
        })
        self.assertEqual(action.risk_id, risk)
        self.assertEqual(action.status, "pending")

        action.action_in_progress()
        self.assertEqual(action.status, "in_progress")

        action.action_done()
        self.assertEqual(action.status, "done")
        self.assertTrue(action.done_date)

    def _risk_activities(self, risk):
        return self.env["mail.activity"].search([
            ("res_model", "=", "od19.iso.risk"),
            ("res_id", "=", risk.id),
        ])

    def test_cron_due_reminder_creates_activity(self):
        risk = self._create_risk()
        risk.action_identified()
        risk.due_date = fields.Date.add(fields.Date.today(), days=3)
        self.env["od19.iso.risk"]._cron_risk_due_reminder()
        self.assertTrue(self._risk_activities(risk))

    def test_cron_overdue_reminder_creates_activity(self):
        risk = self._create_risk()
        risk.action_identified()
        risk.due_date = fields.Date.add(fields.Date.today(), days=-2)
        self.env["od19.iso.risk"]._cron_risk_due_reminder()
        self.assertTrue(self._risk_activities(risk))

    def test_cron_reminder_is_idempotent(self):
        risk = self._create_risk()
        risk.action_identified()
        risk.due_date = fields.Date.add(fields.Date.today(), days=3)
        Risk = self.env["od19.iso.risk"]
        Risk._cron_risk_due_reminder()
        count = len(self._risk_activities(risk))
        Risk._cron_risk_due_reminder()
        self.assertEqual(len(self._risk_activities(risk)), count)

    def test_cron_ignores_closed_risk(self):
        risk = self._create_risk()
        risk.action_close()
        risk.due_date = fields.Date.add(fields.Date.today(), days=3)
        self.env["od19.iso.risk"]._cron_risk_due_reminder()
        self.assertFalse(self._risk_activities(risk))
