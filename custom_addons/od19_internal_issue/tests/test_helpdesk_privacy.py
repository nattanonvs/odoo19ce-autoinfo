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
        cls.dept_x = cls.env["hr.department"].create({"name": "Dept X (test)"})
        cls.dept_y = cls.env["hr.department"].create({"name": "Dept Y (test)"})
        cls.user_x = cls._user_with_department(
            "User X", "priv_x_issue_test", cls.dept_x
        )
        cls.user_y = cls._user_with_department(
            "User Y", "priv_y_issue_test", cls.dept_y
        )

    @classmethod
    def _user_with_department(cls, name, login, department):
        user = cls.env["res.users"].create({"name": name, "login": login})
        # od19_security_roles mirrors the department from hr.employee on create,
        # which would clear it here; set it explicitly for a deterministic fixture.
        user.with_context(od19_skip_department_sync=True).write(
            {"od19_department_id": department.id}
        )
        return user

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
        visible = self.Ticket.with_user(self.user_b).search([("id", "=", ticket.id)])
        self.assertEqual(visible, ticket)

    def test_private_hidden_from_others(self):
        ticket = self._ticket("private")
        visible = self.Ticket.with_user(self.user_b).search([("id", "=", ticket.id)])
        self.assertFalse(visible)

    def test_private_visible_to_reporter(self):
        ticket = self._ticket("private")
        visible = self.Ticket.with_user(self.user_a).search([("id", "=", ticket.id)])
        self.assertEqual(visible, ticket)

    def test_department_visible_to_same_department(self):
        ticket = self._ticket("department", visibility_department_id=self.dept_x.id)
        visible = self.Ticket.with_user(self.user_x).search([("id", "=", ticket.id)])
        self.assertEqual(visible, ticket)

    def test_department_hidden_from_other_department(self):
        ticket = self._ticket("department", visibility_department_id=self.dept_x.id)
        visible = self.Ticket.with_user(self.user_y).search([("id", "=", ticket.id)])
        self.assertFalse(visible)

    def test_triage_email_alias_configured(self):
        alias = self.env.ref(
            "od19_internal_issue.alias_issue_triage", raise_if_not_found=False
        )
        self.assertTrue(alias, "ต้องมีบันทึก alias email ของทีม Triage")
        self.assertEqual(alias.alias_name, "internal-issue")
        self.assertEqual(alias.alias_model_id.model, "helpdesk.ticket")
        self.assertIn("issue_stream", alias.alias_defaults or "")
