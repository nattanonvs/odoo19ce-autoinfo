from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestFixedAsset(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.asset_account = cls.env["account.account"].create(
            {
                "name": "Fixed Assets",
                "code": "131001",
                "account_type": "asset_fixed",
            }
        )
        cls.depreciation_account = cls.env["account.account"].create(
            {
                "name": "Accumulated Depreciation",
                "code": "132001",
                "account_type": "asset_fixed",
            }
        )
        cls.depreciation_expense_account = cls.env["account.account"].create(
            {
                "name": "Depreciation Expense",
                "code": "611001",
                "account_type": "expense",
            }
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111004",
                "account_type": "asset_cash",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Asset Journal",
                "type": "general",
                "code": "AST",
                "default_account_id": cls.cash_account.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Supplier", "is_company": True}
        )

    def test_create_fixed_asset(self):
        asset = self.env["account.asset"].create(
            {
                "name": "Office Equipment",
                "asset_account_id": self.asset_account.id,
                "depreciation_account_id": self.depreciation_account.id,
                "expense_account_id": self.depreciation_expense_account.id,
                "value": 120000.0,
                "salvage_value": 0.0,
                "method_number": 5,
                "method_period": 12,
                "date": "2024-01-01",
            }
        )
        self.assertEqual(asset.value, 120000.0)
        self.assertEqual(asset.state, "draft")

    def test_asset_requires_positive_value(self):
        with self.assertRaises(ValidationError):
            self.env["account.asset"].create(
                {
                    "name": "Invalid Asset",
                    "asset_account_id": self.asset_account.id,
                    "depreciation_account_id": self.depreciation_account.id,
                    "expense_account_id": self.depreciation_expense_account.id,
                    "value": -100.0,
                    "method_number": 5,
                    "method_period": 12,
                    "date": "2024-01-01",
                }
            )

    def test_validate_asset(self):
        asset = self.env["account.asset"].create(
            {
                "name": "Office Equipment",
                "asset_account_id": self.asset_account.id,
                "depreciation_account_id": self.depreciation_account.id,
                "expense_account_id": self.depreciation_expense_account.id,
                "value": 120000.0,
                "salvage_value": 0.0,
                "method_number": 5,
                "method_period": 12,
                "date": "2024-01-01",
            }
        )
        asset.validate()
        self.assertEqual(asset.state, "open")
        self.assertEqual(len(asset.depreciation_line_ids), 5)

    def test_depreciation_amount_calculation(self):
        asset = self.env["account.asset"].create(
            {
                "name": "Office Equipment",
                "asset_account_id": self.asset_account.id,
                "depreciation_account_id": self.depreciation_account.id,
                "expense_account_id": self.depreciation_expense_account.id,
                "value": 120000.0,
                "salvage_value": 0.0,
                "method_number": 5,
                "method_period": 12,
                "date": "2024-01-01",
            }
        )
        asset.validate()
        # Straight line: 120000 / 5 = 24000 per year
        first_line = asset.depreciation_line_ids[0]
        self.assertAlmostEqual(first_line.amount, 24000.0, places=2)

    def test_post_depreciation(self):
        asset = self.env["account.asset"].create(
            {
                "name": "Office Equipment",
                "asset_account_id": self.asset_account.id,
                "depreciation_account_id": self.depreciation_account.id,
                "expense_account_id": self.depreciation_expense_account.id,
                "value": 120000.0,
                "salvage_value": 0.0,
                "method_number": 5,
                "method_period": 12,
                "date": "2024-01-01",
                "journal_id": self.journal.id,
            }
        )
        asset.validate()
        first_line = asset.depreciation_line_ids[0]
        first_line.create_move()
        self.assertEqual(first_line.move_check, True)
        self.assertTrue(first_line.move_id)

    def test_dispose_asset(self):
        asset = self.env["account.asset"].create(
            {
                "name": "Office Equipment",
                "asset_account_id": self.asset_account.id,
                "depreciation_account_id": self.depreciation_account.id,
                "expense_account_id": self.depreciation_expense_account.id,
                "value": 120000.0,
                "salvage_value": 0.0,
                "method_number": 5,
                "method_period": 12,
                "date": "2024-01-01",
                "journal_id": self.journal.id,
            }
        )
        asset.validate()
        asset.set_to_close()
        self.assertEqual(asset.state, "close")
