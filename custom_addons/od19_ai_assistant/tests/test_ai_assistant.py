# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from datetime import date
from unittest.mock import patch

from odoo.tests.common import (
    HttpCase,
    JsonRpcException,
    TransactionCase,
    tagged,
)

CHAT_COMPLETION = (
    "odoo.addons.od19_ai_assistant.models.od19_ai_chat.chat_completion"
)
STREAM_COMPLETION = (
    "odoo.addons.od19_ai_assistant.controllers.main.chat_completion_stream"
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
        self.assertEqual(config["provider"], "ollama")
        self.assertEqual(config["base_url"], "http://localhost:11434/v1")
        self.assertEqual(config["model"], "qwen2.5:7b")
        self.assertEqual(config["timeout"], 60)

    def test_config_uses_groq_provider_preset(self):
        params = self.env["ir.config_parameter"].sudo()
        params.search([("key", "=like", "od19_ai.%")]).unlink()
        params.set_param("od19_ai.provider", "groq")
        config = self.env["od19.ai.chat"]._get_ai_config()
        self.assertEqual(config["provider"], "groq")
        self.assertEqual(config["base_url"], "https://api.groq.com/openai/v1")
        self.assertEqual(config["model"], "llama-3.3-70b-versatile")

    def test_config_explicit_endpoint_overrides_provider(self):
        params = self.env["ir.config_parameter"].sudo()
        params.search([("key", "=like", "od19_ai.%")]).unlink()
        params.set_param("od19_ai.provider", "groq")
        params.set_param("od19_ai.base_url", "http://example.test/v1")
        config = self.env["od19.ai.chat"]._get_ai_config()
        self.assertEqual(config["base_url"], "http://example.test/v1")
        # The model is still taken from the provider preset when unset.
        self.assertEqual(config["model"], "llama-3.3-70b-versatile")

    def test_settings_onchange_fills_provider_preset(self):
        settings = self.env["res.config.settings"].new(
            {
                "od19_ai_provider": "groq",
                "od19_ai_base_url": "http://localhost:11434/v1",
                "od19_ai_model": "qwen2.5:7b",
            }
        )
        settings._onchange_od19_ai_provider()
        self.assertEqual(
            settings.od19_ai_base_url, "https://api.groq.com/openai/v1"
        )
        self.assertEqual(settings.od19_ai_model, "llama-3.3-70b-versatile")

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


@tagged("post_install", "-at_install")
class TestOd19AiChatHttp(HttpCase):
    """JSON-RPC and streaming endpoints that back the OWL chat UI."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        cls.chat_user = cls.env["res.users"].create(
            {
                "name": "OD19 Chat User",
                "login": "od19_chat_user",
                "password": "od19_chat_user",
                "group_ids": [(6, 0, [group_user.id])],
            }
        )
        cls.other_user = cls.env["res.users"].create(
            {
                "name": "OD19 Chat Other",
                "login": "od19_chat_other",
                "password": "od19_chat_other",
                "group_ids": [(6, 0, [group_user.id])],
            }
        )

    def _login(self):
        self.authenticate("od19_chat_user", "od19_chat_user")

    def _make_chat(self, user):
        return self.env["od19.ai.chat"].create({"user_id": user.id})

    def test_create_returns_owned_chat(self):
        self._login()
        ids = self.make_jsonrpc_request("/od19_ai/chat/create")
        self.assertIsInstance(ids, list)
        self.assertEqual(len(ids), 1)
        chat = self.env["od19.ai.chat"].browse(ids[0])
        self.assertTrue(chat.exists())
        self.assertEqual(chat.user_id, self.chat_user)

    def test_list_includes_created_chat(self):
        self._login()
        [chat_id] = self.make_jsonrpc_request("/od19_ai/chat/create")
        listing = self.make_jsonrpc_request("/od19_ai/chat/list")
        self.assertIn(chat_id, [item["id"] for item in listing])

    def test_messages_returns_history(self):
        chat = self._make_chat(self.chat_user)
        chat._post_message("user", "สวัสดี")
        chat._post_message("assistant", "สวัสดีครับ")
        self._login()
        data = self.make_jsonrpc_request(
            "/od19_ai/chat/messages", {"chat_id": chat.id}
        )
        self.assertEqual(data["chat"]["id"], chat.id)
        self.assertEqual([m["role"] for m in data["messages"]],
                         ["user", "assistant"])
        self.assertEqual(data["messages"][0]["content"], "สวัสดี")

    def test_delete_removes_chat(self):
        self._login()
        [chat_id] = self.make_jsonrpc_request("/od19_ai/chat/create")
        result = self.make_jsonrpc_request(
            "/od19_ai/chat/delete", {"chat_id": chat_id}
        )
        self.assertTrue(result)
        self.assertFalse(self.env["od19.ai.chat"].browse(chat_id).exists())

    def test_cannot_read_other_user_chat(self):
        other = self._make_chat(self.other_user)
        self._login()
        with self.assertRaises(JsonRpcException) as ctx:
            self.make_jsonrpc_request(
                "/od19_ai/chat/messages", {"chat_id": other.id}
            )
        self.assertIn("AccessError", str(ctx.exception))

    def test_cannot_delete_other_user_chat(self):
        other = self._make_chat(self.other_user)
        self._login()
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/od19_ai/chat/delete", {"chat_id": other.id}
            )
        self.assertTrue(other.exists())

    def test_stream_endpoint_emits_sse(self):
        chat = self._make_chat(self.chat_user)

        def fake_stream(base_url, model, messages, api_key=None, timeout=None):
            yield "สวัสดี"
            yield "ครับ"

        self._login()
        with patch(STREAM_COMPLETION, side_effect=fake_stream):
            response = self.url_open(
                "/od19_ai/chat/stream",
                json={"chat_id": chat.id, "message": "ทักทาย"},
            )
        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertIn('"type": "delta"', body)
        self.assertIn("สวัสดี", body)
        self.assertIn('"type": "done"', body)


@tagged("post_install", "-at_install")
class TestOrmGuard(TransactionCase):
    def _guard(self):
        from odoo.addons.od19_ai_assistant.lib import orm_guard

        return orm_guard

    def test_safe_limit_caps_and_defaults(self):
        guard = self._guard()
        self.assertEqual(guard.safe_limit(100), 20)
        self.assertEqual(guard.safe_limit(0), 1)
        self.assertEqual(guard.safe_limit("bad"), 5)
        self.assertEqual(guard.safe_limit(None, default=7), 7)

    def test_safe_offset_never_negative(self):
        guard = self._guard()
        self.assertEqual(guard.safe_offset(-5), 0)
        self.assertEqual(guard.safe_offset("3"), 3)
        self.assertEqual(guard.safe_offset("bad"), 0)

    def test_validate_fields_rejects_unknown_field(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_fields(self.env, "res.partner", ["no_such_field"])

    def test_validate_fields_defaults_to_display_name(self):
        guard = self._guard()
        self.assertEqual(
            guard.validate_fields(self.env, "res.partner", None), ["display_name"]
        )

    def test_validate_domain_accepts_safe_operator(self):
        guard = self._guard()
        domain = guard.validate_domain(
            self.env, "res.partner", [["name", "ilike", "abc"]]
        )
        self.env["res.partner"].create({"name": "abc co"})
        self.assertTrue(self.env["res.partner"].search_count(domain))

    def test_validate_domain_rejects_unknown_operator(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(
                self.env, "res.partner", [["name", "regex", "abc"]]
            )

    def test_validate_domain_rejects_unknown_field(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(
                self.env, "res.partner", [["nope", "=", 1]]
            )

    def test_validate_domain_accepts_dotted_path(self):
        guard = self._guard()
        domain = guard.validate_domain(
            self.env, "res.partner", [["user_ids.login", "ilike", "admin"]]
        )
        self.assertTrue(self.env["res.partner"].search_count(domain))

    def test_validate_domain_rejects_non_stored_compute(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(
                self.env, "res.partner", [["display_name", "=", "x"]]
            )

    def test_check_model_rejects_missing_model(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.check_model(self.env, "does.not.exist")

    def test_validate_order_rejects_unknown_field(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_order(self.env, "res.partner", "nope desc")

    def test_validate_aggregates_rejects_unknown_function(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_aggregates(self.env, "res.partner", ["id:median"])

    def test_validate_groupby_rejects_bad_granularity(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_groupby(
                self.env, "res.partner", ["create_date:fortnight"]
            )

    def test_validate_domain_accepts_nested_logic(self):
        guard = self._guard()
        domain = guard.validate_domain(
            self.env,
            "res.partner",
            ["|", ["name", "=", "nested-a"], ["name", "=", "nested-b"]],
        )
        self.env["res.partner"].create({"name": "nested-a"})
        self.assertTrue(self.env["res.partner"].search_count(domain))

    def test_validate_domain_accepts_in_with_list_value(self):
        guard = self._guard()
        domain = guard.validate_domain(self.env, "res.partner", [["id", "in", [1, 2]]])
        self.assertTrue(self.env["res.partner"].search_count(domain))

    def test_validate_domain_rejects_in_with_non_list_value(self):
        guard = self._guard()
        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(self.env, "res.partner", [["id", "in", "abc"]])

    def test_validate_domain_rejects_domain_instance(self):
        guard = self._guard()
        from odoo.fields import Domain

        with self.assertRaises(guard.OrmGuardError):
            guard.validate_domain(self.env, "res.partner", Domain([("name", "=", "x")]))


@tagged("post_install", "-at_install")
class TestGenericExplorer(TransactionCase):
    def test_generic_tools_are_available(self):
        names = [t["name"] for t in self.env["od19.ai.tool"].available_tools()]
        for expected in (
            "list_models",
            "describe_model",
            "search_records",
            "aggregate_records",
        ):
            self.assertIn(expected, names)

    def test_list_models_returns_partner(self):
        result = self.env["od19.ai.tool"].execute(
            "list_models", {"keyword": "res.partner"}
        )
        self.assertIn("res.partner", result)

    def test_list_models_respects_limit(self):
        result = self.env["od19.ai.tool"].execute("list_models", {"limit": 3})
        lines = [line for line in result.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(lines), 3)

    def test_describe_model_lists_fields(self):
        result = self.env["od19.ai.tool"].execute(
            "describe_model", {"model": "res.partner"}
        )
        self.assertIn("res.partner", result)
        self.assertIn("name", result)

    def test_describe_model_rejects_unknown_model(self):
        result = self.env["od19.ai.tool"].execute(
            "describe_model", {"model": "does.not.exist"}
        )
        self.assertIn("ไม่พบโมเดล", result)

    def test_search_records_finds_created_partner(self):
        self.env["res.partner"].create({"name": "บริษัท ทดสอบทั่วไป จำกัด"})
        result = self.env["od19.ai.tool"].execute(
            "search_records",
            {
                "model": "res.partner",
                "domain": [["name", "ilike", "ทดสอบทั่วไป"]],
                "fields": ["name"],
            },
        )
        self.assertIn("บริษัท ทดสอบทั่วไป จำกัด", result)

    def test_search_records_rejects_bad_domain(self):
        result = self.env["od19.ai.tool"].execute(
            "search_records",
            {"model": "res.partner", "domain": [["name", "regex", "x"]]},
        )
        self.assertIn("ไม่ได้รับอนุญาต", result)

    def test_search_records_caps_limit(self):
        self.env["res.partner"].create([{"name": "ลูกค้า %s" % i} for i in range(30)])
        result = self.env["od19.ai.tool"].execute(
            "search_records", {"model": "res.partner", "fields": ["name"], "limit": 500}
        )
        lines = [line for line in result.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(lines), 20)

    def test_aggregate_records_counts(self):
        self.env["res.partner"].create([{"name": "agg %s" % i} for i in range(3)])
        result = self.env["od19.ai.tool"].execute(
            "aggregate_records",
            {
                "model": "res.partner",
                "domain": [["name", "ilike", "agg"]],
                "aggregates": ["__count"],
            },
        )
        self.assertIn("จำนวน", result)
        self.assertIn("3", result)

    def test_aggregate_records_rejects_bad_function(self):
        result = self.env["od19.ai.tool"].execute(
            "aggregate_records",
            {"model": "res.partner", "aggregates": ["id:median"]},
        )
        self.assertIn("ไม่ได้รับอนุญาต", result)


@tagged("post_install", "-at_install")
class TestCapabilityIndex(TransactionCase):
    def test_prompt_index_lists_tools_without_schemas(self):
        index = self.env["od19.ai.tool"].prompt_index()
        self.assertIn("search_partners", index)
        self.assertIn("search_records", index)
        # Argument schemas must NOT be inlined in the index.
        self.assertNotIn("จำนวนผลสูงสุด", index)

    def test_prompt_index_respects_char_budget(self):
        index = self.env["od19.ai.tool"].prompt_index()
        self.assertLessEqual(
            len(index), self.env["od19.ai.tool"].MAX_INDEX_CHARS
        )

    def test_prompt_index_never_cuts_a_tool_line(self):
        tool_model = self.env["od19.ai.tool"]
        fake_tools = [
            {"name": "fake_tool_%03d" % i, "description": "description %03d" % i}
            for i in range(400)
        ]
        with patch.object(
            type(tool_model), "available_tools", return_value=fake_tools
        ):
            index = tool_model.prompt_index()
        budget = tool_model.MAX_INDEX_CHARS
        self.assertLessEqual(len(index), budget)
        lines = index.splitlines()
        # The budget must actually cut tools off (break branch executed).
        self.assertTrue(lines)
        self.assertLess(len(lines), len(fake_tools))
        whole_lines = {
            "- %s: %s" % (t["name"], t["description"]) for t in fake_tools
        }
        for line in lines:
            self.assertTrue(line.startswith("- "), line)
            self.assertIn(": ", line, line)
            self.assertIn(line, whole_lines, line)

    def test_tool_help_returns_argument_schema(self):
        help_text = self.env["od19.ai.tool"].execute(
            "tool_help", {"name": "search_records"}
        )
        self.assertIn("search_records", help_text)
        self.assertIn("domain", help_text)

    def test_tool_help_unknown_tool(self):
        help_text = self.env["od19.ai.tool"].execute(
            "tool_help", {"name": "no_such_tool"}
        )
        self.assertIn("ไม่พบเครื่องมือ", help_text)

    def test_full_schema_returns_arguments(self):
        schema = self.env["od19.ai.tool"].full_schema("search_partners")
        self.assertIn("keyword", schema["arguments"])

    def test_system_prompt_uses_index(self):
        prompt = self.env["od19.ai.chat"]._build_system_prompt("BASE")
        self.assertIn("tool_help", prompt)
        self.assertIn("search_partners", prompt)
