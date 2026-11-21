# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentPullAp(AccountTestInvoicingCommon):
    """AP: pull open vendor bills into draft vouchers, one per partner."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The bill-first AP rule is out of scope for these tests.
        cls.env.company.od19_require_vendor_bill_for_payment = False
        cls.bank_journal = cls.company_data["default_journal_bank"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _bill(self, amount, partner=None, **kwargs):
        return self._create_invoice_one_line(
            price_unit=amount,
            move_type="in_invoice",
            partner_id=partner or self.partner_a,
            tax_ids=[],
            post=True,
            **kwargs,
        )

    def _wizard(self, **kwargs):
        values = {"journal_id": self.bank_journal.id}
        values.update(kwargs)
        return self.env["od19.payment.pull.wizard"].create(values)

    def _outbound_payments(self):
        return self.env["account.payment"].search(
            [("payment_type", "=", "outbound")]
        )

    # ------------------------------------------------------------------
    # Full amounts
    # ------------------------------------------------------------------
    def test_two_bills_one_vendor_become_one_draft_voucher(self):
        self._bill(1000.0)
        self._bill(2000.0)

        wizard = self._wizard(payment_type="outbound")
        self.assertEqual(len(wizard.line_ids), 2)
        self.assertTrue(all(wizard.line_ids.mapped("selected")))
        self.assertEqual(wizard.selected_count, 2)
        self.assertEqual(wizard.selected_amount, 3000.0)
        self.assertEqual(wizard.planned_voucher_count, 1)

        wizard.action_pull()

        payments = self._outbound_payments()
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.amount, 3000.0)
        self.assertEqual(payments.partner_id, self.partner_a)
        self.assertEqual(payments.state, "draft")
        self.assertEqual(payments.od19_prepare_state, "draft")
        # Both payable lines are staged to be settled once the voucher posts.
        self.assertEqual(len(payments.od19_pending_reconcile_line_ids), 2)

    def test_posted_voucher_settles_every_bill(self):
        bills = self._bill(1000.0) + self._bill(2000.0)

        self._wizard(payment_type="outbound").action_pull()
        payments = self._outbound_payments()
        self.assertEqual(len(payments), 1)

        payments.action_post()

        self.assertIn(payments.state, ("in_process", "paid"))
        self.assertEqual(set(bills.mapped("payment_state")), {"paid"})

    def test_group_by_partner_off_creates_one_voucher_per_bill(self):
        self._bill(1000.0)
        self._bill(2000.0)

        wizard = self._wizard(payment_type="outbound", group_by_partner=False)
        self.assertEqual(wizard.planned_voucher_count, 2)

        wizard.action_pull()

        payments = self._outbound_payments()
        self.assertEqual(len(payments), 2)
        self.assertEqual(sorted(payments.mapped("amount")), [1000.0, 2000.0])

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def test_partner_filter_limits_the_documents(self):
        self._bill(1000.0, partner=self.partner_a)
        self._bill(2000.0, partner=self.partner_b)

        wizard = self._wizard(payment_type="outbound", partner_id=self.partner_a.id)

        self.assertEqual(len(wizard.line_ids), 1)
        self.assertEqual(wizard.line_ids.partner_id, self.partner_a)

    def test_paid_bill_is_not_pulled(self):
        bill = self._bill(1000.0)
        # Settle the bill outside the wizard so it leaves the work queue.
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=bill.ids
        ).create({"group_payment": True})._create_payments()
        self.assertEqual(bill.payment_state, "paid")

        wizard = self._wizard(payment_type="outbound")

        self.assertFalse(wizard.line_ids)
