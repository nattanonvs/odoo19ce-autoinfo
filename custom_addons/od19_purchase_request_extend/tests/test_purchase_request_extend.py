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
