# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestOd19AiContext(TransactionCase):
    def _brain(self):
        return self.env["od19.ai.assistant"]

    def test_build_context_readable_record(self):
        partner = self.env["res.partner"].create({"name": "บริษัท บริบท จำกัด"})
        ctx = self._brain().build_context("res.partner", partner.id, "form")
        self.assertEqual(ctx["model"], "res.partner")
        self.assertEqual(ctx["res_id"], partner.id)
        self.assertEqual(ctx["display_name"], "บริษัท บริบท จำกัด")
        self.assertEqual(ctx["view_type"], "form")
        self.assertLessEqual(len(ctx["fields"]), 30)

    def test_build_context_list_without_res_id(self):
        ctx = self._brain().build_context("res.partner", False, "list")
        self.assertEqual(ctx["model"], "res.partner")
        self.assertFalse(ctx["res_id"])
        self.assertEqual(ctx["view_type"], "list")

    def test_build_context_unknown_model_is_none(self):
        self.assertIsNone(self._brain().build_context("no.such.model", 1, "form"))

    def test_build_context_missing_record_is_none(self):
        self.assertIsNone(
            self._brain().build_context("res.partner", 99999999, "form")
        )

    def test_build_context_denied_by_record_rule_is_none(self):
        partner = self.env["res.partner"].create({"name": "ลับสุดยอด"})
        user = new_test_user(
            self.env, login="od19_ctx_denied", groups="base.group_user"
        )
        self.env["ir.rule"].create(
            {
                "name": "OD19 ctx deny rule",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": "[('id', '=', 0)]",
                "groups": [(6, 0, user.group_ids.ids)],
            }
        )
        self.assertIsNone(
            self.env["od19.ai.assistant"]
            .with_user(user)
            .build_context("res.partner", partner.id, "form")
        )

    def test_context_brief_is_truncated(self):
        ctx = {
            "model": "res.partner",
            "res_id": 1,
            "view_type": "form",
            "display_name": "ก" * 2000,
            "fields": ["name"],
            "snippet": "ข" * 2000,
        }
        brief = self._brain().context_brief(ctx)
        self.assertLessEqual(len(brief), 800)
        self.assertIn("res.partner", brief)

    def test_context_brief_empty(self):
        self.assertEqual(self._brain().context_brief(None), "")

    def test_suggest_actions_capped_at_four(self):
        for model in ("sale.order", "account.move", "res.partner"):
            self.assertLessEqual(len(self._brain().suggest_actions({"model": model})), 4)
