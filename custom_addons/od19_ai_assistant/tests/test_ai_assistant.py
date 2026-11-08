# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from datetime import date
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

    # ------------------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------------------
    def test_tool_catalog_lists_installed_tools(self):
        tools = self.env["od19.ai.tool"]
        names = [t["name"] for t in tools.available_tools()]
        self.assertIn("search_partners", names)
        self.assertIn("search_partners", tools.prompt_catalog())

    def test_system_prompt_includes_tool_catalog(self):
        prompt = self.env["od19.ai.chat"]._build_system_prompt("BASE")
        self.assertIn("BASE", prompt)
        self.assertIn("search_partners", prompt)

    def test_parse_tool_call_variants(self):
        Chat = self.env["od19.ai.chat"]
        self.assertEqual(
            Chat._parse_tool_call(
                '{"tool": "search_partners", "arguments": {"keyword": "x"}}'
            ),
            ("search_partners", {"keyword": "x"}),
        )
        self.assertEqual(
            Chat._parse_tool_call(
                '```json\n{"tool": "search_products", "arguments": {}}\n```'
            ),
            ("search_products", {}),
        )
        self.assertEqual(
            Chat._parse_tool_call(
                'โปรดรอ {"tool": "search_invoices", "arguments": {}} ครับ'
            ),
            ("search_invoices", {}),
        )
        self.assertIsNone(Chat._parse_tool_call("สวัสดีครับ"))
        self.assertIsNone(Chat._parse_tool_call(""))

    def test_safe_limit_is_clamped(self):
        tools = self.env["od19.ai.tool"]
        self.assertEqual(tools._safe_limit(100), 20)
        self.assertEqual(tools._safe_limit(0), 1)
        self.assertEqual(tools._safe_limit("bad"), 5)

    def test_search_partners_tool_returns_match(self):
        self.env["res.partner"].create({"name": "บริษัท ABC การบัญชี จำกัด"})
        result = self.env["od19.ai.tool"].execute(
            "search_partners", {"keyword": "ABC"}
        )
        self.assertIn("บริษัท ABC การบัญชี จำกัด", result)

    def test_execute_unknown_tool_is_reported(self):
        result = self.env["od19.ai.tool"].execute("no_such_tool", {})
        self.assertIn("ไม่พบเครื่องมือ", result)

    def test_action_ask_runs_tool_then_answers(self):
        self.env["res.partner"].create({"name": "บริษัท ทดสอบ จำกัด"})
        chat = self.env["od19.ai.chat"].create({"prompt": "หาคู่ค้าชื่อทดสอบ"})
        calls = {"n": 0}

        def fake_chat_completion(base_url, model, messages, api_key=None, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return '{"tool": "search_partners", "arguments": {"keyword": "ทดสอบ"}}'
            return "พบคู่ค้าชื่อ บริษัท ทดสอบ จำกัด"

        with patch(CHAT_COMPLETION, side_effect=fake_chat_completion):
            chat.action_ask()

        tool_msgs = chat.message_ids.filtered(lambda m: m.role == "tool")
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("บริษัท ทดสอบ จำกัด", tool_msgs.content)
        self.assertEqual(calls["n"], 2)
        last = chat.message_ids.sorted("id")[-1]
        self.assertEqual(last.role, "assistant")
        self.assertIn("พบคู่ค้า", last.content)
        self.assertEqual(chat.state, "done")

    # ------------------------------------------------------------------
    # Extended tool catalog (A1 / A2)
    # ------------------------------------------------------------------
    def test_extended_tool_catalog_is_declared(self):
        names = [t["name"] for t in self.env["od19.ai.tool"]._tool_definitions()]
        for expected in (
            "search_purchase_orders",
            "search_journal_items",
            "search_stock_quants",
            "search_employees",
            "sales_summary",
            "tax_summary",
            "overdue_receivables",
        ):
            self.assertIn(expected, names)

    def test_parse_date_accepts_common_formats(self):
        tools = self.env["od19.ai.tool"]
        self.assertEqual(tools._parse_date("2026-01-15"), date(2026, 1, 15))
        self.assertEqual(tools._parse_date("15/01/2026"), date(2026, 1, 15))
        self.assertEqual(tools._parse_date(date(2026, 3, 1)), date(2026, 3, 1))
        self.assertIsNone(tools._parse_date(""))
        self.assertIsNone(tools._parse_date("ไม่ใช่วันที่"))

    def test_plain_value_normalises_orm_values(self):
        tools = self.env["od19.ai.tool"]
        partner = self.env["res.partner"].create({"name": "ทดสอบค่า"})
        self.assertEqual(tools._plain_value(partner), "ทดสอบค่า")
        self.assertEqual(tools._plain_value(1500.0), 1500.0)
        self.assertEqual(tools._plain_value(date(2026, 2, 3)), "2026-02-03")
        self.assertEqual(tools._plain_value(False), "")

    def test_format_groups_renders_rows(self):
        tools = self.env["od19.ai.tool"]
        text = tools._format_groups(
            [("sale", 1500.0, 3)], ["ประเภท"], ["ยอดรวม", "จำนวน"]
        )
        self.assertIn("ประเภท=sale", text)
        self.assertIn("ยอดรวม=1500.0", text)
        self.assertIn("จำนวน=3", text)
        self.assertEqual(tools._format_groups([], ["a"], ["b"]), "ไม่พบข้อมูล")

    def test_group_model_aggregates_with_read_group(self):
        self.env["res.partner"].create(
            {"name": "OD19 Aggregate Co", "company_type": "company"}
        )
        rows = self.env["od19.ai.tool"]._group_model(
            "res.partner",
            [("name", "ilike", "OD19 Aggregate")],
            ["name"],
            ["id:count"],
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0][0], "OD19 Aggregate Co")
        self.assertGreaterEqual(rows[0][1], 1)

    # ------------------------------------------------------------------
    # Access rights (A3)
    # ------------------------------------------------------------------
    def _plain_user(self, login):
        return self.env["res.users"].create(
            {
                "name": "OD19 Plain User",
                "login": login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

    def test_check_read_access_allows_admin(self):
        self.assertTrue(
            self.env["od19.ai.tool"]._check_read_access("res.partner")
        )

    def test_check_read_access_denies_plain_user(self):
        tools = self.env["od19.ai.tool"].with_user(self._plain_user("od19_acl_a"))
        self.assertFalse(tools._check_read_access("account.move.line"))

    def test_execute_denies_tool_without_rights(self):
        tools = self.env["od19.ai.tool"].with_user(self._plain_user("od19_acl_b"))
        result = tools.execute("search_journal_items", {})
        self.assertIn("ไม่มีสิทธิ์อ่านข้อมูล", result)
