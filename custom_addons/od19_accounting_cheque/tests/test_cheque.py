from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCheque(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Test Customer", "is_company": True}
        )
        cls.supplier = cls.env["res.partner"].create(
            {"name": "Test Supplier", "is_company": True}
        )
        cls.bank = cls.env["res.bank"].create(
            {"name": "Test Bank"}
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111001",
                "account_type": "asset_cash",
            }
        )
        cls.cheque_receivable_account = cls.env["account.account"].create(
            {
                "name": "Cheque Receivable",
                "code": "112001",
                "account_type": "asset_current",
            }
        )
        cls.cheque_payable_account = cls.env["account.account"].create(
            {
                "name": "Cheque Payable",
                "code": "212001",
                "account_type": "liability_current",
            }
        )

    def test_create_customer_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ001",
            }
        )
        self.assertEqual(cheque.state, "draft")
        self.assertEqual(cheque.cheque_type, "customer")

    def test_create_supplier_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "supplier",
                "partner_id": self.supplier.id,
                "bank_id": self.bank.id,
                "amount": 50000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ002",
            }
        )
        self.assertEqual(cheque.state, "draft")

    def test_cheque_requires_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.env["account.cheque"].create(
                {
                    "cheque_type": "customer",
                    "partner_id": self.customer.id,
                    "bank_id": self.bank.id,
                    "amount": -100.0,
                    "cheque_date": "2024-01-15",
                    "due_date": "2024-02-15",
                    "name": "CHQ003",
                }
            )

    def test_cheque_due_date_after_cheque_date(self):
        with self.assertRaises(ValidationError):
            self.env["account.cheque"].create(
                {
                    "cheque_type": "customer",
                    "partner_id": self.customer.id,
                    "bank_id": self.bank.id,
                    "amount": 100000.0,
                    "cheque_date": "2024-02-15",
                    "due_date": "2024-01-15",
                    "name": "CHQ004",
                }
            )

    def test_confirm_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ005",
            }
        )
        cheque.action_confirm()
        self.assertEqual(cheque.state, "confirmed")

    def test_deposit_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ006",
            }
        )
        cheque.action_confirm()
        cheque.action_deposit()
        self.assertEqual(cheque.state, "deposited")

    def test_clear_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ007",
            }
        )
        cheque.action_confirm()
        cheque.action_deposit()
        cheque.action_clear()
        self.assertEqual(cheque.state, "cleared")

    def test_bounce_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ008",
            }
        )
        cheque.action_confirm()
        cheque.action_bounce()
        self.assertEqual(cheque.state, "bounced")

    def test_cancel_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ009",
            }
        )
        cheque.action_confirm()
        cheque.action_cancel()
        self.assertEqual(cheque.state, "cancelled")
