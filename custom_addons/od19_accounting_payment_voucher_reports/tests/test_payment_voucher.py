# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


# ``res.partner`` carries fields made required by other installed modules (for
# instance ``group_rfq`` from ``purchase_stock``). While this module is being
# installed the registry does not carry them yet, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestPaymentVoucherNumber(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "is_company": True}
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Bank",
                "code": "TBNK",
                "type": "bank",
                "company_id": cls.env.company.id,
            }
        )

    def _create_payment(self, payment_type, partner_type):
        return self.env["account.payment"].create(
            {
                "payment_type": payment_type,
                "partner_type": partner_type,
                "partner_id": self.partner.id,
                "amount": 1000.0,
                "journal_id": self.journal.id,
                "date": "2026-10-21",
            }
        )

    def test_supplier_payment_gets_pv_number(self):
        payment = self._create_payment("outbound", "supplier")
        self.assertFalse(payment.od19_voucher_no)
        payment._od19_assign_voucher_number()
        self.assertTrue(payment.od19_voucher_no)
        self.assertTrue(payment.od19_voucher_no.startswith("PV"))

    def test_customer_payment_gets_rv_number(self):
        payment = self._create_payment("inbound", "customer")
        payment._od19_assign_voucher_number()
        self.assertTrue(payment.od19_voucher_no)
        self.assertTrue(payment.od19_voucher_no.startswith("RV"))

    def test_voucher_number_is_not_reassigned(self):
        payment = self._create_payment("outbound", "supplier")
        payment._od19_assign_voucher_number()
        first_number = payment.od19_voucher_no
        payment._od19_assign_voucher_number()
        self.assertEqual(payment.od19_voucher_no, first_number)
