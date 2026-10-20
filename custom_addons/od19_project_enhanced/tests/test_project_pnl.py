from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectPnl(TransactionCase):
    """Project P&L read from posted analytic lines (spec 6.6)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dept = cls.env["hr.department"].create({"name": "PNL Dept"})
        cls.project = cls.env["project.project"].create(
            {
                "name": "PNL Project",
                "od19_department_id": cls.dept.id,
            }
        )
        cls.analytic = cls.project.account_id
        cls.income = cls.env["account.account"].search(
            [("account_type", "=", "income"), ("company_ids", "in", cls.company.id)],
            limit=1,
        )
        cls.expense = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "in", cls.company.id)],
            limit=1,
        )
        # An equity account is neither revenue nor loss, so its analytic lines
        # are reported as "uncategorized" by the Odoo 19 core classification.
        cls.uncategorized = cls.env["account.account"].search(
            [("account_type", "=", "equity"), ("company_ids", "in", cls.company.id)],
            limit=1,
        )
        cls.counter = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_current"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )

    def _post_entry(self, account, balance, date=None, post=True):
        """Create a two-line entry with 100% analytic distribution.

        ``balance`` is ``debit - credit`` on the analytic line, so its analytic
        amount is ``-balance`` (Odoo 19 core: amount = -move_line.balance).
        """
        date = date or fields.Date.to_date("2026-06-15")
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "analytic line",
                            "account_id": account.id,
                            "debit": balance if balance > 0 else 0.0,
                            "credit": -balance if balance < 0 else 0.0,
                            "analytic_distribution": {str(self.analytic.id): 100},
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "counter line",
                            "account_id": self.counter.id,
                            "debit": -balance if balance < 0 else 0.0,
                            "credit": balance if balance > 0 else 0.0,
                        },
                    ),
                ],
            }
        )
        if post:
            move.action_post()
        return move

    def test_revenue_and_cost_split_with_sign(self):
        self._post_entry(self.income, -1000.0)  # credit income -> revenue 1000
        self._post_entry(self.expense, 400.0)  # debit expense -> cost 400
        values = self.project._od19_get_pnl_values()
        self.assertAlmostEqual(values["revenue"], 1000.0, 2)
        self.assertAlmostEqual(values["cost"], 400.0, 2)
        self.assertAlmostEqual(values["gross_margin"], 600.0, 2)
        self.assertAlmostEqual(values["margin_percent"], 60.0, 2)
        self.assertTrue(values["has_analytic"])

    def test_draft_move_is_excluded(self):
        self._post_entry(self.income, -1000.0, post=False)
        values = self.project._od19_get_pnl_values()
        self.assertAlmostEqual(values["revenue"], 0.0, 2)
        self.assertAlmostEqual(values["cost"], 0.0, 2)

    def test_uncategorized_is_reported_separately(self):
        self._post_entry(self.income, -1000.0)
        self._post_entry(self.uncategorized, 250.0)
        values = self.project._od19_get_pnl_values()
        self.assertAlmostEqual(values["revenue"], 1000.0, 2)
        self.assertAlmostEqual(values["cost"], 0.0, 2)
        self.assertAlmostEqual(values["uncategorized_amount"], -250.0, 2)

    def test_date_range_filters_lines(self):
        self._post_entry(self.income, -1000.0, date=fields.Date.to_date("2026-01-15"))
        self._post_entry(self.income, -500.0, date=fields.Date.to_date("2026-07-15"))
        values = self.project._od19_get_pnl_values(
            date_from=fields.Date.to_date("2026-06-01"),
            date_to=fields.Date.to_date("2026-12-31"),
        )
        self.assertAlmostEqual(values["revenue"], 500.0, 2)

    def test_zero_revenue_does_not_divide_by_zero(self):
        self._post_entry(self.expense, 400.0)
        values = self.project._od19_get_pnl_values()
        self.assertEqual(values["margin_percent"], 0.0)

    def test_project_without_analytic_account_returns_zero_and_flag(self):
        project = self.env["project.project"].create({"name": "No Analytic"})
        project.account_id = False
        values = project._od19_get_pnl_values()
        self.assertFalse(values["has_analytic"])
        self.assertEqual(values["revenue"], 0.0)
        self.assertEqual(values["cost"], 0.0)
        self.assertEqual(values["margin_percent"], 0.0)
