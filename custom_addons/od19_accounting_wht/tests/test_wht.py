from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWHT(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wht_account = cls.env["account.account"].create(
            {
                "name": "WHT Payable",
                "code": "213001",
                "account_type": "liability_payable",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Expense",
                "code": "511001",
                "account_type": "expense",
            }
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111001",
                "account_type": "asset_cash",
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Supplier", "is_company": True}
        )
        cls.wht_type = cls.env["wht.type"].create(
            {
                "name": "WHT 3%",
                "percent": 3.0,
                "account_id": cls.wht_account.id,
            }
        )

    def test_wht_type_creation(self):
        self.assertEqual(self.wht_type.name, "WHT 3%")
        self.assertEqual(self.wht_type.percent, 3.0)
        self.assertEqual(self.wht_type.account_id, self.wht_account)

    def test_wht_type_percent_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.env["wht.type"].create(
                {
                    "name": "WHT Negative",
                    "percent": -1.0,
                    "account_id": self.wht_account.id,
                }
            )

    def test_wht_type_percent_not_exceed_100(self):
        with self.assertRaises(ValidationError):
            self.env["wht.type"].create(
                {
                    "name": "WHT Over",
                    "percent": 101.0,
                    "account_id": self.wht_account.id,
                }
            )

    def test_wht_type_percent_zero_is_allowed(self):
        wht_type = self.env["wht.type"].create(
            {
                "name": "WHT 0%",
                "percent": 0.0,
                "account_id": self.wht_account.id,
            }
        )
        self.assertEqual(wht_type.percent, 0.0)

    def test_wht_amount_computation(self):
        """WHT amount = base * percent / 100"""
        payment = self.env["account.payment"].new(
            {
                "wht_type_id": self.wht_type.id,
                "wht_base_amount": 100000.0,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.assertEqual(payment.wht_amount, 3000.0)
        self.assertEqual(payment.wht_net_amount, 97000.0)

    def test_wht_amount_zero_without_type(self):
        payment = self.env["account.payment"].new(
            {
                "wht_base_amount": 100000.0,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.assertEqual(payment.wht_amount, 0.0)
        self.assertEqual(payment.wht_net_amount, 100000.0)

    def test_wht_amount_zero_without_base(self):
        payment = self.env["account.payment"].new(
            {
                "wht_type_id": self.wht_type.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.assertEqual(payment.wht_amount, 0.0)
        self.assertEqual(payment.wht_net_amount, 0.0)
