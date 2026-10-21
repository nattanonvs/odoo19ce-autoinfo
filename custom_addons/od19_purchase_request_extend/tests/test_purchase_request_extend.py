from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPurchaseRequestExtend(TransactionCase):
    """Tests for the Thai purchase request extension."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env["purchase.request"]
        cls.Product = cls.env["product.product"]

    def _create_request(self, **overrides):
        vals = {}
        vals.update(overrides)
        return self.Request.create(vals)

    # ------------------------------------------------------------------
    # Defaults & computes
    # ------------------------------------------------------------------
    def test_default_priority_is_normal(self):
        request = self._create_request()
        self.assertEqual(request.od19_priority, "normal")

    def test_budget_year_default_is_buddhist_era(self):
        request = self._create_request()
        expected = str(fields.Date.context_today(self.env.user).year + 543)
        self.assertEqual(request.od19_budget_year, expected)

    def test_justification_required_false_for_normal(self):
        request = self._create_request(od19_priority="normal")
        self.assertFalse(request.od19_justification_required)

    def test_justification_required_true_for_urgent(self):
        request = self._create_request(od19_priority="urgent")
        self.assertTrue(request.od19_justification_required)

    def test_justification_required_true_for_emergency(self):
        request = self._create_request(od19_priority="emergency")
        self.assertTrue(request.od19_justification_required)

    def test_request_reason_can_be_stored(self):
        request = self._create_request(
            od19_priority="urgent",
            od19_request_reason="Machine breakdown",
        )
        self.assertEqual(request.od19_request_reason, "Machine breakdown")

    # ------------------------------------------------------------------
    # department_id (canonical field merged from former
    # od19_requested_department_id)
    # ------------------------------------------------------------------
    def _create_user_with_department(self, login, department):
        user = self.env["res.users"].create({"name": login, "login": login})
        self.env["hr.employee"].create(
            {
                "name": login,
                "user_id": user.id,
                "department_id": department.id,
            }
        )
        return user

    def test_department_is_editable(self):
        request = self._create_request()
        department = self.env["hr.department"].create({"name": "Manual Dept C6"})
        request.department_id = department
        self.assertEqual(request.department_id, department)

    def test_department_computed_from_requested_by(self):
        department = self.env["hr.department"].create({"name": "Test PR Dept"})
        user = self._create_user_with_department("pr_requester_c6", department)
        request = self._create_request()
        request.requested_by = user
        self.assertEqual(request.department_id, department)

    def test_default_get_department_from_user_employee(self):
        department = self.env["hr.department"].create({"name": "Default Dept C6"})
        user = self._create_user_with_department("default_dept_user_c6", department)
        defaults = self.Request.with_user(user).default_get(["department_id"])
        self.assertEqual(defaults.get("department_id"), department.id)

    # ------------------------------------------------------------------
    # button_to_approve guard
    # ------------------------------------------------------------------
    def test_button_to_approve_urgent_without_reason_raises(self):
        request = self._create_request(od19_priority="urgent")
        with self.assertRaises(UserError):
            request.button_to_approve()
        self.assertEqual(request.state, "draft")

    def test_button_to_approve_emergency_without_reason_raises(self):
        request = self._create_request(od19_priority="emergency")
        with self.assertRaises(UserError):
            request.button_to_approve()
        self.assertEqual(request.state, "draft")
