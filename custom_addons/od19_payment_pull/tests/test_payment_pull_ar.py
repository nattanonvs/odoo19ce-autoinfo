# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentPullAr(AccountTestInvoicingCommon):
    """AR: pull open customer invoices into draft receipt vouchers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.od19_require_vendor_bill_for_payment = False
        cls.bank_journal = cls.company_data["default_journal_bank"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _invoice(self, amount, partner=None):
        return self._create_invoice_one_line(
            price_unit=amount,
            move_type="out_invoice",
            partner_id=partner or self.partner_a,
            tax_ids=[],
            post=True,
        )

    def _wizard(self, **kwargs):
        values = {"journal_id": self.bank_journal.id, "payment_type": "inbound"}
        values.update(kwargs)
        return self.env["od19.payment.pull.wizard"].create(values)

    def _inbound_payments(self):
        return self.env["account.payment"].search(
            [("payment_type", "=", "inbound")]
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_two_invoices_two_customers_become_two_vouchers(self):
        self._invoice(1000.0, self.partner_a)
        self._invoice(2000.0, self.partner_b)

        wizard = self._wizard()
        self.assertEqual(len(wizard.line_ids), 2)
        self.assertEqual(wizard.planned_voucher_count, 2)

        wizard.action_pull()

        payments = self._inbound_payments()
        self.assertEqual(len(payments), 2)
        self.assertEqual(sum(payments.mapped("amount")), 3000.0)
        self.assertEqual(set(payments.mapped("partner_type")), {"customer"})
        self.assertEqual(set(payments.mapped("state")), {"draft"})
        self.assertEqual(set(payments.mapped("od19_prepare_state")), {"draft"})
        self.assertEqual(
            set(payments.mapped("partner_id")), set(self.partner_a | self.partner_b)
        )

    def test_two_invoices_one_customer_become_one_voucher(self):
        self._invoice(1000.0, self.partner_a)
        self._invoice(2000.0, self.partner_a)

        wizard = self._wizard()
        self.assertEqual(wizard.planned_voucher_count, 1)

        wizard.action_pull()

        payments = self._inbound_payments()
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.amount, 3000.0)
        self.assertEqual(payments.partner_id, self.partner_a)

    def test_outbound_pull_ignores_customer_invoices(self):
        self._invoice(1000.0, self.partner_a)

        wizard = self._wizard(payment_type="outbound")

        self.assertFalse(wizard.line_ids)
