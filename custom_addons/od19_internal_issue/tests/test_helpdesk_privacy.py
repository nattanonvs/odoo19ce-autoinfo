from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssuePrivacy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.user_a = cls.env["res.users"].create(
            {"name": "User A", "login": "priv_a_issue_test"}
        )
        cls.user_b = cls.env["res.users"].create(
            {"name": "User B", "login": "priv_b_issue_test"}
        )

    def _ticket(self, visibility, **overrides):
        vals = {
            "name": "priv",
            "description": "<p>t</p>",
            "visibility": visibility,
            "reported_by_id": self.user_a.id,
        }
        vals.update(overrides)
        return self.Ticket.create(vals)

    def test_public_visible_to_others(self):
        ticket = self._ticket("public")
        self.assertTrue(ticket.with_user(self.user_b).read(["name"]))

    def test_private_hidden_from_others(self):
        ticket = self._ticket("private")
        visible = self.Ticket.with_user(self.user_b).search([("id", "=", ticket.id)])
        self.assertFalse(visible)

    def test_private_visible_to_reporter(self):
        ticket = self._ticket("private")
        visible = self.Ticket.with_user(self.user_a).search([("id", "=", ticket.id)])
        self.assertEqual(visible, ticket)
