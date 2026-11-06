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
