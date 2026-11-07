# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

CHAT_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_chat.chat_completion"
)
AI_CLIENT_ERROR = "odoo.addons.od19_ai_assistant.lib.client.AiClientError"


@tagged("post_install", "-at_install")
class TestOd19AiAssistant(TransactionCase):
    def test_config_reads_system_parameters(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("od19_ai.base_url", "http://example.test/v1")
        params.set_param("od19_ai.model", "test-model")
        config = self.env["od19.ai.chat"]._get_ai_config()
        self.assertEqual(config["base_url"], "http://example.test/v1")
        self.assertEqual(config["model"], "test-model")

    def test_config_falls_back_to_defaults(self):
        params = self.env["ir.config_parameter"].sudo()
        params.search([("key", "=like", "od19_ai.%")]).unlink()
        config = self.env["od19.ai.chat"]._get_ai_config()
        self.assertEqual(config["base_url"], "http://localhost:11434/v1")
        self.assertEqual(config["model"], "qwen2.5:7b")
        self.assertEqual(config["timeout"], 60)

    def test_action_ask_stores_answer(self):
        chat = self.env["od19.ai.chat"].create({"prompt": "สวัสดี"})
        with patch(CHAT_COMPLETION, return_value="สวัสดีครับ"):
            chat.action_ask()
        self.assertEqual(chat.response, "สวัสดีครับ")
        self.assertEqual(chat.state, "done")

    def test_action_ask_records_error(self):
        from odoo.addons.od19_ai_assistant.lib.client import AiClientError

        chat = self.env["od19.ai.chat"].create({"prompt": "test"})
        with patch(CHAT_COMPLETION, side_effect=AiClientError("boom")):
            result = chat.action_ask()
        self.assertEqual(chat.state, "error")
        self.assertIn("boom", chat.error_message)
        self.assertEqual(result.get("tag"), "display_notification")

    def test_name_is_derived_from_prompt(self):
        chat = self.env["od19.ai.chat"].create({"prompt": "ขอรายงานภาษีซื้อ\nบรรทัดที่สอง"})
        self.assertEqual(chat.name, "ขอรายงานภาษีซื้อ")
