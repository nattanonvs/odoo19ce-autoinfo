# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

CHAT_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion"
)
STREAM_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_assistant.chat_completion_stream"
)


@tagged("post_install", "-at_install")
class TestOd19AiAssistantService(TransactionCase):
    def _brain(self):
        return self.env["od19.ai.assistant"]

    # ------------------------------------------------------------------
    # Config / prompt / parse (ย้ายมาแล้วยังให้ผลเหมือนเดิม)
    # ------------------------------------------------------------------
    def test_config_defaults_unchanged(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=like", "od19_ai.%")]
        ).unlink()
        config = self._brain()._get_ai_config()
        self.assertEqual(config["provider"], "ollama")
        self.assertEqual(config["timeout"], 60)

    def test_parse_tool_call_delegated(self):
        self.assertEqual(
            self._brain()._parse_tool_call(
                '{"tool": "search_partners", "arguments": {"keyword": "x"}}'
            ),
            ("search_partners", {"keyword": "x"}),
        )
        self.assertIsNone(self._brain()._parse_tool_call("สวัสดีครับ"))

    # ------------------------------------------------------------------
    # ask()
    # ------------------------------------------------------------------
    def test_ask_without_chat_returns_answer(self):
        with patch(CHAT_COMPLETION, return_value="สวัสดีครับ"):
            result = self._brain().ask("สวัสดี")
        self.assertEqual(result["answer"], "สวัสดีครับ")
        self.assertIsNone(result["error"])

    def test_ask_empty_question_raises(self):
        with self.assertRaises(UserError):
            self._brain().ask("   ")

    def test_ask_with_chat_persists_history(self):
        chat = self.env["od19.ai.chat"].create({})
        with patch(CHAT_COMPLETION, return_value="ตอบ"):
            self._brain().ask("คำถาม", chat=chat)
        self.assertEqual(chat.state, "done")
        self.assertEqual(len(chat.message_ids), 2)

    def test_ask_runs_tool_once_then_answers(self):
        self.env["res.partner"].create({"name": "บริษัท ทดสอบ จำกัด"})
        calls = {"n": 0}

        def fake(base_url, model, messages, api_key=None, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return '{"tool": "search_partners", "arguments": {"keyword": "ทดสอบ"}}'
            return "พบ บริษัท ทดสอบ จำกัด"

        with patch(CHAT_COMPLETION, side_effect=fake):
            result = self._brain().ask("หาคู่ค้าทดสอบ")
        self.assertEqual(calls["n"], 2)
        self.assertIn("บริษัท ทดสอบ จำกัด", result["answer"])

    def test_ask_exceeding_rounds_returns_fallback(self):
        def always_tool(base_url, model, messages, api_key=None, timeout=None):
            return '{"tool": "search_partners", "arguments": {}}'

        with patch(CHAT_COMPLETION, side_effect=always_tool):
            result = self._brain().ask("ถาม")
        self.assertIn("หลายรอบเกินไป", result["answer"])

    def test_ask_error_marks_chat_and_returns_error(self):
        from odoo.addons.od19_ai_assistant.lib.client import AiClientError

        chat = self.env["od19.ai.chat"].create({})
        with patch(CHAT_COMPLETION, side_effect=AiClientError("boom")):
            result = self._brain().ask("test", chat=chat)
        self.assertEqual(chat.state, "error")
        self.assertEqual(result["error"], "boom")
        self.assertIsNone(result["answer"])

    # ------------------------------------------------------------------
    # stream()
    # ------------------------------------------------------------------
    def test_stream_yields_delta_then_done(self):
        chat = self.env["od19.ai.chat"].create({})

        def fake_stream(base_url, model, messages, api_key=None, timeout=None):
            for token in ("สวัสดี", "ครับ"):
                yield token

        with patch(STREAM_COMPLETION, side_effect=fake_stream):
            events = list(self._brain().stream("สวัสดี", chat=chat))
        types = [e["type"] for e in events]
        self.assertIn("delta", types)
        self.assertEqual(types[-1], "done")
        self.assertEqual(chat.state, "done")

    # ------------------------------------------------------------------
    # suggest_actions() / confirm_draft()
    # ------------------------------------------------------------------
    def test_suggest_actions_known_model(self):
        chips = self._brain().suggest_actions({"model": "sale.order"})
        self.assertTrue(chips)
        self.assertLessEqual(len(chips), 4)

    def test_suggest_actions_unknown_model_falls_back(self):
        chips = self._brain().suggest_actions({"model": "no.such.model"})
        self.assertTrue(chips)

    def test_suggest_actions_empty_context(self):
        self.assertTrue(self._brain().suggest_actions(None))

    def test_confirm_draft_delegates(self):
        self.env.user.od19_ai_capability_mode = "read_draft"
        self.env["ir.config_parameter"].sudo().set_param(
            "od19_ai.draft_models", "res.partner"
        )
        record = self._brain().confirm_draft("res.partner", {"name": "ร่างใหม่"})
        self.assertTrue(record.exists())
