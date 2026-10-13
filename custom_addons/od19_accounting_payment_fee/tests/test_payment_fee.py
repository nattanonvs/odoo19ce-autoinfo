# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged("od19_accounting_payment_fee")
class TestPaymentFee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create({
                "name": "Test Bank",
                "code": "TBK",
                "type": "bank",
                "company_id": cls.company.id,
            })
        cls.fee_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        )

    def _create_payment(self, amount=1000, fee=50):
        return self.env["account.payment"].create({
            "partner_id": self.partner.id,
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": amount,
            "fee_amount": fee,
            "fee_account_id": self.fee_account.id,
            "journal_id": self.bank_journal.id,
        })

    def test_payment_fee_creates_fee_line(self):
        payment = self._create_payment(amount=1000, fee=50)
        payment.action_post()
        move = payment.move_id
        fee_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.fee_account
        )
        self.assertTrue(fee_lines, "Fee line should be created")
        self.assertEqual(sum(fee_lines.mapped("debit")), 50.0)

    def test_fee_without_account_raises(self):
        payment = self._create_payment(amount=1000, fee=50)
        payment.fee_account_id = False
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_negative_fee_raises(self):
        with self.assertRaises(ValidationError):
            self.env["account.payment"].create({
                "partner_id": self.partner.id,
                "payment_type": "inbound",
                "partner_type": "customer",
                "amount": 1000,
                "fee_amount": -50,
                "fee_account_id": self.fee_account.id,
                "journal_id": self.bank_journal.id,
            })

    def test_no_fee_normal_payment(self):
        payment = self._create_payment(amount=1000, fee=0)
        payment.action_post()
        move = payment.move_id
        fee_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.fee_account
        )
        self.assertFalse(fee_lines, "No fee line when fee is zero")
