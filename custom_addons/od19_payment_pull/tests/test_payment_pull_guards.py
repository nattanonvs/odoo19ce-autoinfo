# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentPullGuards(AccountTestInvoicingCommon):
    """Edge cases of the payment pull wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        values = {"journal_id": self.bank_journal.id, "payment_type": "outbound"}
        values.update(kwargs)
        return self.env["od19.payment.pull.wizard"].create(values)

    def _outbound_payments(self):
        return self.env["account.payment"].search(
            [("payment_type", "=", "outbound")]
        )

    # ------------------------------------------------------------------
    # Selection / amount validation
    # ------------------------------------------------------------------
    def test_no_selection_raises(self):
        self._bill(1000.0)

        wizard = self._wizard()
        wizard.line_ids.selected = False

        with self.assertRaises(UserError):
            wizard.action_pull()

    def test_zero_amount_raises(self):
        self._bill(1000.0)

        wizard = self._wizard()
        wizard.line_ids.amount_to_pay = 0.0

        with self.assertRaises(UserError):
            wizard.action_pull()

    def test_amount_over_residual_raises(self):
        self._bill(1000.0)

        wizard = self._wizard()
        wizard.line_ids.amount_to_pay = 1500.0

        with self.assertRaises(UserError):
            wizard.action_pull()

    # ------------------------------------------------------------------
    # Partial payments
    # ------------------------------------------------------------------
    def test_partial_amount_creates_a_dedicated_draft_voucher(self):
        self._bill(1000.0)

        wizard = self._wizard()
        wizard.line_ids.amount_to_pay = 400.0
        self.assertTrue(wizard.line_ids.is_partial)

        wizard.action_pull()

        payments = self._outbound_payments()
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.amount, 400.0)
        self.assertEqual(payments.state, "draft")

    def test_partial_post_leaves_the_remaining_residual(self):
        bill = self._bill(1000.0)

        wizard = self._wizard()
        wizard.line_ids.amount_to_pay = 400.0
        wizard.action_pull()

        payments = self._outbound_payments()
        self.assertEqual(len(payments), 1)
        payments.action_post()

        self.assertAlmostEqual(bill.amount_residual, 600.0, places=2)

    # ------------------------------------------------------------------
    # Fail-safe filtering
    # ------------------------------------------------------------------
    def test_blocked_bill_is_excluded(self):
        bill = self._bill(1000.0)
        bill.action_toggle_block_payment()

        wizard = self._wizard()

        self.assertFalse(wizard.line_ids)

    def test_mixed_currency_splits_into_two_vouchers(self):
        eur = self.setup_other_currency("EUR")
        self._bill(1000.0)
        self._bill(1000.0, currency_id=eur.id)

        wizard = self._wizard()
        self.assertEqual(len(wizard.line_ids), 2)
        self.assertEqual(wizard.planned_voucher_count, 2)

        wizard.action_pull()

        payments = self._outbound_payments()
        self.assertEqual(len(payments), 2)
        self.assertEqual(
            set(payments.mapped("currency_id")),
            set(self.env.company.currency_id | eur),
        )

    # ------------------------------------------------------------------
    # Prepare -> Approve gate is preserved
    # ------------------------------------------------------------------
    def test_draft_voucher_is_gated_on_post(self):
        self.env.company.od19_enforce_prepare_approval = True
        self._bill(1000.0)

        self._wizard().action_pull()
        payment = self._outbound_payments()
        self.assertEqual(payment.state, "draft")

        with self.assertRaises(UserError):
            payment.action_post()

        # Releasing the gate lets the draft voucher post and settle the bill.
        self.env.company.od19_enforce_prepare_approval = False
        payment.action_post()
        self.assertNotEqual(payment.state, "draft")
