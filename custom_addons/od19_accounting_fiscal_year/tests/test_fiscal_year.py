from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo import fields


class TestFiscalYear(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.revenue_account = cls.env["account.account"].create(
            {
                "name": "Revenue",
                "code": "411001",
                "account_type": "income",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Expense",
                "code": "511003",
                "account_type": "expense",
            }
        )
        cls.retained_earnings_account = cls.env["account.account"].create(
            {
                "name": "Retained Earnings",
                "code": "312001",
                "account_type": "equity",
            }
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111003",
                "account_type": "asset_cash",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Closing Journal",
                "type": "general",
                "code": "CLS",
                "default_account_id": cls.cash_account.id,
            }
        )

    def test_create_fiscal_year(self):
        fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY 2024",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )
        self.assertEqual(fy.state, "draft")
        self.assertEqual(fy.name, "FY 2024")

    def test_fiscal_year_date_validation(self):
        with self.assertRaises(ValidationError):
            self.env["account.fiscal.year"].create(
                {
                    "name": "FY Invalid",
                    "date_from": "2024-12-31",
                    "date_to": "2024-01-01",
                }
            )

    def test_fiscal_year_overlap(self):
        self.env["account.fiscal.year"].create(
            {
                "name": "FY 2024",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["account.fiscal.year"].create(
                {
                    "name": "FY 2024 Overlap",
                    "date_from": "2024-06-01",
                    "date_to": "2025-05-31",
                }
            )

    def test_open_fiscal_year(self):
        fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY 2024",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )
        fy.action_open()
        self.assertEqual(fy.state, "open")

    def test_close_fiscal_year(self):
        fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY 2024",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )
        fy.action_open()
        fy.action_close()
        self.assertEqual(fy.state, "closed")

    def test_year_end_closing_wizard(self):
        fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY 2024",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )
        fy.action_open()

        # Create some revenue and expense moves
        move_revenue = self.env["account.move"].create(
            {
                "date": "2024-06-15",
                "journal_id": self.journal.id,
                "line_ids": [
                    (0, 0, {
                        "account_id": self.cash_account.id,
                        "debit": 100000.0,
                        "credit": 0.0,
                        "name": "Cash",
                    }),
                    (0, 0, {
                        "account_id": self.revenue_account.id,
                        "debit": 0.0,
                        "credit": 100000.0,
                        "name": "Revenue",
                    }),
                ],
            }
        )
        move_revenue.action_post()

        move_expense = self.env["account.move"].create(
            {
                "date": "2024-07-15",
                "journal_id": self.journal.id,
                "line_ids": [
                    (0, 0, {
                        "account_id": self.expense_account.id,
                        "debit": 40000.0,
                        "credit": 0.0,
                        "name": "Expense",
                    }),
                    (0, 0, {
                        "account_id": self.cash_account.id,
                        "debit": 0.0,
                        "credit": 40000.0,
                        "name": "Cash",
                    }),
                ],
            }
        )
        move_expense.action_post()

        wizard = self.env["account.year.end.closing"].create(
            {
                "fiscal_year_id": fy.id,
                "retained_earnings_account_id": self.retained_earnings_account.id,
                "journal_id": self.journal.id,
                "date": "2024-12-31",
            }
        )
        result = wizard.action_close_fiscal_year()
        self.assertTrue(result)
        self.assertEqual(fy.state, "closed")
