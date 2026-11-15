# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบการวินิจฉัยด้วย AI (P5): โหมดอ่านอย่างเดียว + การจัดการข้อผิดพลาด."""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

CHAT_COMPLETION = "odoo.addons.od19_ai_assistant.lib.client.chat_completion"
PARAM_AI_TRIAGE_ENABLED = "od19_health.ai_triage_enabled"


@tagged("post_install", "-at_install")
class TestHealthAiTriage(TransactionCase):
    """ทดสอบการประกอบคำถามและการบันทึกผลวินิจฉัย (ไม่เรียก AI จริง)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["od19.health.check"].search([]).write({"active": False})
        cls.check = cls.env["od19.health.check"].create(
            {"name": "AI Check", "code": "ai_triage_check", "check_type": "custom"}
        )
        cls.incident = cls.env["od19.health.incident"].create(
            {
                "check_id": cls.check.id,
                "fingerprint": "ai_triage_check|0|",
                "severity": "critical",
                "check_state": "critical",
                "description": "ระบบตอบสนองช้า",
            }
        )

    # ------------------------- การเตรียมข้อมูล -------------------------
    def test_build_prompt_includes_context(self):
        prompt = self.env["od19.health.ai.triage"]._build_prompt(self.incident)
        self.assertIn(self.incident.name, prompt)
        self.assertIn(self.check.name, prompt)
        self.assertIn(self.check.code, prompt)

    # ------------------------- การวินิจฉัย -------------------------
    def test_triage_success_records_summary(self):
        Triage = self.env["od19.health.ai.triage"]
        with patch(CHAT_COMPLETION, return_value="สาเหตุ: คิวงานล้น"):
            result = Triage._triage(self.incident)
        self.assertEqual(result.state, "done")
        self.assertEqual(result.summary, "สาเหตุ: คิวงานล้น")
        self.assertEqual(result.incident_id, self.incident)
        self.assertTrue(result.prompt)

    def test_triage_failure_is_captured(self):
        Triage = self.env["od19.health.ai.triage"]
        with patch(CHAT_COMPLETION, side_effect=RuntimeError("boom")):
            result = Triage._triage(self.incident)
        self.assertEqual(result.state, "error")
        self.assertIn("วินิจฉัยไม่สำเร็จ", result.summary)

    # ------------------------- ปุ่มบนหน้าจอ -------------------------
    def test_action_run_triage_requires_enabled(self):
        self.env["ir.config_parameter"].sudo().set_param(
            PARAM_AI_TRIAGE_ENABLED, "False"
        )
        self.env.invalidate_all()
        with self.assertRaises(UserError):
            self.incident.action_run_triage()

    def test_action_run_triage_creates_record(self):
        self.env["ir.config_parameter"].sudo().set_param(
            PARAM_AI_TRIAGE_ENABLED, "True"
        )
        self.env.invalidate_all()
        with patch(CHAT_COMPLETION, return_value="สรุป"):
            action = self.incident.action_run_triage()
        self.assertEqual(action["res_model"], "od19.health.ai.triage")
        self.assertEqual(self.incident.triage_count, 1)
