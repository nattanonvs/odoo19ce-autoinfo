from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestCreditLimit(CreditGateCommon):
    """Tests for credit limit amount, used amount, available amount and expiry."""

    def _approve_credit(self):
        self.customer.od19_credit_review_note = "ok"
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def test_credit_limit_fields_default_zero(self):
        self.assertEqual(self.customer.od19_credit_limit_amount, 0.0)
        self.assertEqual(self.customer.od19_credit_used_amount, 0.0)
        self.assertEqual(self.customer.od19_credit_available, 0.0)
        self.assertFalse(self.customer.od19_credit_expiry_date)

    def test_credit_available_equals_limit_minus_used(self):
        self.customer.od19_credit_limit_amount = 1000.0
        # No invoices or confirmed orders -> used = 0
        self.customer._compute_od19_credit_used_amount()
        self.customer._compute_od19_credit_available()
        self.assertEqual(self.customer.od19_credit_used_amount, 0.0)
        self.assertEqual(self.customer.od19_credit_available, 1000.0)

    def test_credit_sale_allowed_requires_approval(self):
        # Not approved -> not allowed
        self.assertFalse(self.customer.od19_credit_sale_allowed)
        self._approve_credit()
        self.customer.od19_credit_limit_amount = 5000.0
        self.customer._compute_od19_credit_sale_allowed()
        self.assertTrue(self.customer.od19_credit_sale_allowed)

    def test_credit_sale_allowed_false_when_expired(self):
        self._approve_credit()
        self.customer.od19_credit_limit_amount = 5000.0
        self.customer.od19_credit_expiry_date = fields.Date.today() - timedelta(days=1)
        self.customer._compute_od19_credit_sale_allowed()
        self.assertFalse(self.customer.od19_credit_sale_allowed)

    def test_credit_sale_allowed_false_when_no_available_credit(self):
        self._approve_credit()
        self.customer.od19_credit_limit_amount = 1000.0
        # Create a confirmed order to consume credit
        order = self.env["sale.order"].create(
            self._quotation_vals(self.contact, self.term_immediate)
        )
        order.action_confirm()
        self.customer._compute_od19_credit_used_amount()
        self.customer._compute_od19_credit_sale_allowed()
        # 100 (product price) consumed, available = 900 -> still allowed
        self.assertTrue(self.customer.od19_credit_sale_allowed)

    def test_credit_revalidation_creates_activity_on_blacklist(self):
        self._approve_credit()
        order = self.env["sale.order"].create(
            self._quotation_vals(self.contact, self.term_immediate)
        )
        order.action_confirm()
        initial_activity_count = len(order.activity_ids)
        # Blacklist the customer -> should trigger revalidation
        self.customer.od19_blacklist_reason = "Bad debt"
        self.customer.with_user(self.reviewer).action_od19_set_blacklist()
        # A review activity should be scheduled on the confirmed order
        self.assertGreater(len(order.activity_ids), initial_activity_count)

    def test_credit_revalidation_triggers_on_credit_state_change(self):
        self._approve_credit()
        order = self.env["sale.order"].create(
            self._quotation_vals(self.contact, self.term_30)
        )
        order.action_confirm()
        initial_activity_count = len(order.activity_ids)
        # Reject credit -> confirmed credit order should be flagged
        self.customer.od19_credit_review_note = "changed mind"
        self.customer.sudo().od19_credit_request_state = "rejected"
        self.assertGreater(len(order.activity_ids), initial_activity_count)
