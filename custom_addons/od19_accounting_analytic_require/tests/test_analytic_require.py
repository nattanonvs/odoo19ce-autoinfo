# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged, TransactionCase


@tagged("od19_accounting_analytic_require")
class TestAnalyticRequire(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.cash_account = cls.env["account.account"].search(
            [("account_type", "=", "asset_cash"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.analytic_account = cls.env["account.analytic.account"].create({
            "name": "Test Analytic",
            "plan_id": cls.env["account.analytic.plan"].search([], limit=1).id
            or cls.env["account.analytic.plan"].create({"name": "Default"}).id,
        })

    def _create_move(self, with_analytic=False):
        analytic_distribution = (
            {str(self.analytic_account.id): 100.0} if with_analytic else False
        )
        return self.env["account.move"].create({
            "journal_id": self.journal.id,
            "line_ids": [
                (0, 0, {
                    "name": "Test expense",
                    "account_id": self.expense_account.id,
                    "debit": 100,
                    "credit": 0,
                    "analytic_distribution": analytic_distribution,
                }),
                (0, 0, {
                    "name": "Test cash",
                    "account_id": self.cash_account.id,
                    "debit": 0,
                    "credit": 100,
                }),
            ],
        })

    def test_no_requirement_allows_posting(self):
        self.company.write({"od19_analytic_required_account_ids": [(6, 0, [])]})
        move = self._create_move(with_analytic=False)
        move.action_post()
        self.assertEqual(move.state, "posted")

    def test_requirement_blocks_without_analytic(self):
        self.company.write({
            "od19_analytic_required_account_ids": [(6, 0, self.expense_account.ids)],
        })
        move = self._create_move(with_analytic=False)
        with self.assertRaises(UserError):
            move.action_post()

    def test_requirement_allows_with_analytic(self):
        self.company.write({
            "od19_analytic_required_account_ids": [(6, 0, self.expense_account.ids)],
        })
        move = self._create_move(with_analytic=True)
        move.action_post()
        self.assertEqual(move.state, "posted")
