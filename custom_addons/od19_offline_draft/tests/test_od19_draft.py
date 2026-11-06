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
