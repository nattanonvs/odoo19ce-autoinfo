from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectRiskReport(TransactionCase):
    """Risk scoring contract (spec 6.7) and SQL view / Python helper parity."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dept = cls.env["hr.department"].create({"name": "Risk Dept"})
        cls.project = cls.env["project.project"].create(
            {
                "name": "Risk Project",
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
        cls.counter = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_current"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.Report = cls.env["od19.project.risk.report"]

    def _post_entry(self, account, balance, date=None):
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
        move.action_post()
        return move

    def test_order_has_no_non_stored_field(self):
        self.assertEqual(self.Report._order, "id")

    def test_risk_level_boundaries(self):
        # low < 40, medium >= 40, high >= 70
        self.assertEqual(self.Report.new({"risk_score": 39}).risk_level, "low")
        self.assertEqual(self.Report.new({"risk_score": 40}).risk_level, "medium")
        self.assertEqual(self.Report.new({"risk_score": 69}).risk_level, "medium")
        self.assertEqual(self.Report.new({"risk_score": 70}).risk_level, "high")

    def test_risk_score_skips_margin_when_no_revenue(self):
        # DD-1: work in progress (no recognized revenue) must not be scored as
        # a margin risk, otherwise every open project turns risky.
        rec = self.Report.new({"revenue": 0.0, "actual_cost": 500.0})
        self.assertEqual(rec.risk_score, 0)

    def test_risk_score_adds_margin_penalty_with_low_margin(self):
        rec = self.Report.new({"revenue": 1000.0, "actual_cost": 900.0})
        self.assertEqual(rec.risk_score, 40)

    def test_risk_score_combines_margin_and_overdue(self):
        rec = self.Report.new(
            {"revenue": 1000.0, "actual_cost": 900.0, "overdue_ar": 100.0}
        )
        self.assertEqual(rec.risk_score, 70)
        self.assertEqual(rec.risk_level, "high")

    def test_sql_view_agrees_with_python_pnl(self):
        self._post_entry(self.income, -1000.0)
        self._post_entry(self.expense, 400.0)
        report = self.Report.search([("project_id", "=", self.project.id)], limit=1)
        self.assertTrue(report)
        values = self.project._od19_get_pnl_values()
        self.assertAlmostEqual(report.revenue, values["revenue"], 2)
        self.assertAlmostEqual(report.actual_cost, values["cost"], 2)
        self.assertAlmostEqual(
            report.uncategorized_amount, values["uncategorized_amount"], 2
        )
        self.assertAlmostEqual(report.gross_margin, values["gross_margin"], 2)
        self.assertAlmostEqual(report.margin_percent, values["margin_percent"], 2)

    def test_pnl_warning_flags_missing_analytic(self):
        rec = self.Report.new({"analytic_account_id": False})
        self.assertTrue(rec.pnl_warning)
