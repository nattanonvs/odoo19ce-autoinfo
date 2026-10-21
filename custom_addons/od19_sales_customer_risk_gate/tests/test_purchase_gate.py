from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestPurchaseGate(CreditGateCommon):
    """A blacklisted partner is cut off from all purchase activities."""

    def _blacklist_vendor(self):
        self.vendor.with_user(self.reviewer).write(
            {"od19_blacklist_reason": "Repeated quality failures"}
        )
        self.vendor.with_user(self.reviewer).action_od19_set_blacklist()

    def _approve_procurement(self, rfq):
        """Clear the procurement approval precondition on an RFQ.

        ``od19_purchase_procurement_core`` requires every RFQ to be approved
        before it can be confirmed, and that check runs before the risk gate
        in the confirmation chain.  The test grants the approval through the
        module's internal context so the risk gate is then reached.
        """
        rfq.with_context(od19_allow_approval_state_write=True).write(
            {"od19_approval_state": "approved"}
        )

    def test_blacklisted_vendor_cannot_create_rfq(self):
        self._blacklist_vendor()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            self.env["purchase.order"].create(self._rfq_vals())

    def test_blacklist_after_rfq_blocks_confirm(self):
        rfq = self.env["purchase.order"].create(self._rfq_vals())
        self._approve_procurement(rfq)
        self._blacklist_vendor()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            rfq.button_confirm()

    def test_blacklisted_vendor_blocks_vendor_change(self):
        rfq = self.env["purchase.order"].create(self._rfq_vals())
        self._blacklist_vendor()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            rfq.partner_id = self.vendor

    def test_rfq_confirm_sets_risk_snapshot(self):
        rfq = self.env["purchase.order"].create(self._rfq_vals())
        self._approve_procurement(rfq)
        rfq.button_confirm()
        self.assertEqual(rfq.state, "purchase")
        self.assertEqual(rfq.od19_risk_status_snapshot, "normal")

    def test_blacklist_reason_visible_on_rfq(self):
        rfq = self.env["purchase.order"].create(self._rfq_vals())
        self._blacklist_vendor()
        self.assertIn("Blacklist", rfq.od19_gate_blocked_reason)

    def test_blacklist_logs_event_and_notifies_open_rfq(self):
        rfq = self.env["purchase.order"].create(self._rfq_vals())
        initial_activity_count = len(rfq.activity_ids)
        self._blacklist_vendor()
        event = self.env["od19.credit.gate.event"].search(
            [
                ("partner_id", "=", self.vendor.id),
                ("reason_code", "=", "blacklist"),
                ("stage", "=", "credit_revalidation"),
            ],
            limit=1,
        )
        self.assertTrue(event)
        self.assertGreater(len(rfq.activity_ids), initial_activity_count)
