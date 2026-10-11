from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestSaleGate(CreditGateCommon):
    def _approve(self):
        self.customer.od19_credit_review_note = "ok"
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def _blacklist(self):
        self.customer.od19_blacklist_reason = "Bad debt"
        self.customer.with_user(self.reviewer).action_od19_set_blacklist()

    def test_blacklisted_cannot_create_quotation(self):
        self._blacklist()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            self.env["sale.order"].create(self._quotation_vals(self.contact))

    def test_blacklist_after_quotation_blocks_confirm(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        self._blacklist()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            order.action_confirm()

    def test_not_approved_non_credit_quotation_confirms(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertFalse(order.od19_is_credit_sale)

    def test_not_approved_credit_term_quotation_blocked(self):
        for state in ("not_requested", "pending", "rejected"):
            self.customer.sudo().od19_credit_request_state = state
            with self.assertRaisesRegex(UserError, "credit"):
                self.env["sale.order"].create(self._quotation_vals(term=self.term_30))

    def test_switching_to_credit_term_blocked(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        with self.assertRaisesRegex(UserError, "credit"):
            order.payment_term_id = self.term_30

    def test_approved_customer_credit_sale_confirms_with_snapshot(self):
        self._approve()
        order = self.env["sale.order"].create(self._quotation_vals(self.contact, self.term_30))
        order.action_confirm()
        self.assertTrue(order.od19_is_credit_sale)
        self.assertEqual(order.od19_credit_state_snapshot, "approved")
        self.assertEqual(order.od19_risk_status_snapshot, "normal")

    def test_rejected_after_quotation_blocks_credit_confirm(self):
        self._approve()
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_30))
        self.customer.sudo().od19_credit_request_state = "rejected"
        with self.assertRaisesRegex(UserError, "credit"):
            order.action_confirm()

    def test_blocked_reason_visible_on_order(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        self._blacklist()
        self.assertIn("Blacklist", order.od19_gate_blocked_reason)

    def test_confirmed_orders_not_revalidated(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        order.action_confirm()
        self._blacklist()
        order.write({"note": "after blacklist"})
        self.assertEqual(order.state, "sale")
