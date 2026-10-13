from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAdvance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_advance_account = cls.env["account.account"].create(
            {
                "name": "Customer Advance",
                "code": "214001",
                "account_type": "liability_current",
            }
        )
        cls.supplier_advance_account = cls.env["account.account"].create(
            {
                "name": "Supplier Advance",
                "code": "121001",
                "account_type": "asset_current",
            }
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111001",
                "account_type": "asset_cash",
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Test Customer", "is_company": True}
        )
        cls.supplier = cls.env["res.partner"].create(
            {"name": "Test Supplier", "is_company": True}
        )
        cls.customer_journal = cls.env["account.journal"].create(
            {
                "name": "Customer Advance Journal",
                "type": "general",
                "code": "CADV",
                "default_account_id": cls.cash_account.id,
            }
        )
        cls.supplier_journal = cls.env["account.journal"].create(
            {
                "name": "Supplier Advance Journal",
                "type": "general",
                "code": "SADV",
                "default_account_id": cls.cash_account.id,
            }
        )

    def test_create_customer_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
            }
        )
        self.assertEqual(advance.state, "draft")
        self.assertEqual(advance.remaining_amount, 50000.0)
        self.assertEqual(advance.used_amount, 0.0)

    def test_create_supplier_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "supplier",
                "partner_id": self.supplier.id,
                "amount": 30000.0,
                "date": "2024-01-15",
                "advance_account_id": self.supplier_advance_account.id,
            }
        )
        self.assertEqual(advance.state, "draft")
        self.assertEqual(advance.remaining_amount, 30000.0)

    def test_post_customer_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
                "journal_id": self.customer_journal.id,
            }
        )
        advance.action_post()
        self.assertEqual(advance.state, "posted")
        self.assertTrue(advance.move_id)

    def test_post_supplier_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "supplier",
                "partner_id": self.supplier.id,
                "amount": 30000.0,
                "date": "2024-01-15",
                "advance_account_id": self.supplier_advance_account.id,
                "journal_id": self.supplier_journal.id,
            }
        )
        advance.action_post()
        self.assertEqual(advance.state, "posted")
        self.assertTrue(advance.move_id)

    def test_advance_requires_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.env["account.advance"].create(
                {
                    "advance_type": "customer",
                    "partner_id": self.customer.id,
                    "amount": -100.0,
                    "date": "2024-01-15",
                    "advance_account_id": self.customer_advance_account.id,
                }
            )

    def test_cancel_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
                "journal_id": self.customer_journal.id,
            }
        )
        advance.action_post()
        advance.action_cancel()
        self.assertEqual(advance.state, "cancel")

    def test_cannot_cancel_draft(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
            }
        )
        with self.assertRaises(ValidationError):
            advance.action_cancel()
