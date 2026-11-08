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
        assistant = chat.message_ids.filtered(lambda m: m.role == "assistant")
        self.assertEqual(assistant.content, "สวัสดีครับ")
        self.assertEqual(chat.state, "done")
        self.assertFalse(chat.prompt)

    def test_action_ask_keeps_history(self):
        chat = self.env["od19.ai.chat"].create({})
        captured = []

        def fake_chat_completion(base_url, model, messages, api_key=None, timeout=None):
            captured.append([(m["role"], m["content"]) for m in messages])
            return "ตอบครั้งที่ %d" % len(captured)

        with patch(CHAT_COMPLETION, side_effect=fake_chat_completion):
            chat.prompt = "คำถามแรก"
            chat.action_ask()
            chat.prompt = "คำถามที่สอง"
            chat.action_ask()

        # First call: system prompt + the single user question.
        self.assertEqual(captured[0][0][0], "system")
        self.assertEqual(captured[0][1:], [("user", "คำถามแรก")])
        # Second call replays the whole conversation before the new question.
        self.assertEqual(
            captured[1][1:],
            [
                ("user", "คำถามแรก"),
                ("assistant", "ตอบครั้งที่ 1"),
                ("user", "คำถามที่สอง"),
            ],
        )
        self.assertEqual(len(chat.message_ids), 4)

    def test_action_ask_records_error(self):
        from odoo.addons.od19_ai_assistant.lib.client import AiClientError

        chat = self.env["od19.ai.chat"].create({"prompt": "test"})
        with patch(CHAT_COMPLETION, side_effect=AiClientError("boom")):
            result = chat.action_ask()
        self.assertEqual(chat.state, "error")
        system = chat.message_ids.filtered(lambda m: m.role == "system")
        self.assertIn("boom", system.content)
        self.assertEqual(result.get("tag"), "display_notification")

    def test_name_is_derived_from_message(self):
        chat = self.env["od19.ai.chat"].create({})
        chat._post_message("user", "ขอรายงานภาษีซื้อ\nบรรทัดที่สอง")
        self.assertEqual(chat.name, "ขอรายงานภาษีซื้อ")
