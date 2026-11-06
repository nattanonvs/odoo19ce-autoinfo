from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOd19DraftCore(TransactionCase):
    def test_create_draft_defaults(self):
        draft = self.env["od19.draft"].create(
            {"model_name": "sale.order", "res_id": 0, "payload": {"note": "hello"}}
        )
        self.assertEqual(draft.user_id, self.env.user)
        self.assertEqual(draft.company_id, self.env.company)
        self.assertEqual(draft.state, "active")
        self.assertEqual(draft.payload_version, 1)

    def test_name_computed_from_model_and_res_id(self):
        existing = self.env["od19.draft"].create(
            {"model_name": "sale.order", "res_id": 42}
        )
        new_record = self.env["od19.draft"].create(
            {"model_name": "sale.order", "res_id": 0}
        )
        self.assertEqual(existing.name, "sale.order#42")
        self.assertEqual(new_record.name, "sale.order#new")

    def test_upsert_creates_then_updates_same_draft(self):
        draft_model = self.env["od19.draft"]
        first = draft_model.upsert_draft("sale.order", 0, {"note": "v1"})
        second = draft_model.upsert_draft("sale.order", 0, {"note": "v2"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(draft_model.search_count([("state", "=", "active")]), 1)

    def test_fetch_returns_payload(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "hello"})
        result = draft_model.fetch_draft("sale.order", 0)
        self.assertTrue(result)
        self.assertEqual(result["payload"], {"note": "hello"})
        self.assertEqual(result["payload_version"], 1)

    def test_fetch_returns_false_when_no_draft(self):
        self.assertFalse(self.env["od19.draft"].fetch_draft("sale.order", 999))

    def test_discard_removes_draft(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "hello"})
        draft_model.discard_draft("sale.order", 0)
        self.assertFalse(draft_model.fetch_draft("sale.order", 0))
        self.assertEqual(draft_model.search_count([]), 0)

    def test_mark_applied_removes_draft(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "hello"})
        draft_model.mark_applied("sale.order", 0)
        self.assertEqual(draft_model.search_count([]), 0)

    def test_fetch_expires_when_payload_version_mismatch(self):
        draft_model = self.env["od19.draft"]
        draft = draft_model.create(
            {
                "model_name": "sale.order",
                "res_id": 0,
                "payload": {"note": "old"},
                "payload_version": 999,
            }
        )
        self.assertFalse(draft_model.fetch_draft("sale.order", 0))
        self.assertTrue(draft.exists())
        self.assertEqual(draft.state, "expired")

    def test_enabled_models_contains_defaults(self):
        enabled = self.env["od19.draft"]._get_enabled_models()
        self.assertIn("sale.order", enabled)
        self.assertIn("purchase.order", enabled)
        self.assertIn("purchase.request", enabled)
        self.assertIn("account.analytic.line", enabled)

    def test_client_config_shape(self):
        config = self.env["od19.draft"]._get_client_config()
        self.assertEqual(config["debounce_ms"], 2000)
        self.assertEqual(config["ttl_days"], 7)
        self.assertEqual(config["payload_version"], 1)
        self.assertIn("sale.order", config["enabled_models"])

    def test_upsert_rejects_disabled_model(self):
        with self.assertRaises(UserError):
            self.env["od19.draft"].upsert_draft("res.partner", 0, {"note": "x"})

    def test_cron_expires_only_past_drafts(self):
        draft_model = self.env["od19.draft"]
        draft_model.upsert_draft("sale.order", 0, {"note": "expired"})
        draft_model.sudo().search([("res_id", "=", 0)]).write(
            {"expires_at": "2000-01-01 00:00:00"}
        )
        draft_model.upsert_draft("sale.order", 77, {"note": "fresh"})
        removed = draft_model._cron_expire_drafts()
        self.assertEqual(removed, 1)
        self.assertTrue(draft_model.fetch_draft("sale.order", 77))
