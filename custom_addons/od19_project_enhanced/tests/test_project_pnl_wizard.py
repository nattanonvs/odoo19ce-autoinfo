from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectPnlWizard(TransactionCase):
    """Project P&L wizard (D7) and its agreement with the risk report view."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dept = cls.env["hr.department"].create({"name": "Wizard Dept"})
        cls.project = cls.env["project.project"].create(
            {
                "name": "Wizard Project",
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

    def _wizard(self, projects=None):
        return self.env["od19.project.pnl.report"].create(
            {
                "date_from": fields.Date.to_date("2026-01-01"),
                "date_to": fields.Date.to_date("2026-12-31"),
                "company_ids": [(6, 0, self.company.ids)],
                "project_ids": [(6, 0, projects.ids)] if projects is not None else False,
            }
        )

    def test_generate_lines_for_selected_projects(self):
        wizard = self._wizard(self.project)
        wizard.action_generate()
        self.assertTrue(wizard.line_ids)
        self.assertEqual(wizard.line_ids.project_id, self.project)

    def test_wizard_warns_when_project_has_no_analytic(self):
        project = self.env["project.project"].create({"name": "Wizard No Analytic"})
        project.account_id = False
        wizard = self._wizard(project)
        wizard.action_generate()
        line = wizard.line_ids.filtered(lambda l: l.project_id == project)
        self.assertTrue(line)
        self.assertFalse(line.has_analytic)
        self.assertTrue(line.warning)

    def test_risk_report_and_pnl_agree_for_full_range(self):
        self._post_entry(self.income, -1000.0)
        self._post_entry(self.expense, 400.0)
        wizard = self._wizard(self.project)
        wizard.action_generate()
        line = wizard.line_ids.filtered(lambda l: l.project_id == self.project)
        self.assertTrue(line)
        report = self.env["od19.project.risk.report"].search(
            [("project_id", "=", self.project.id)], limit=1
        )
        self.assertTrue(report)
        self.assertAlmostEqual(line.revenue, report.revenue, 2)
        self.assertAlmostEqual(line.cost, report.actual_cost, 2)
        self.assertAlmostEqual(line.gross_margin, report.gross_margin, 2)
        self.assertAlmostEqual(line.margin_percent, report.margin_percent, 2)
        self.assertFalse(line.warning)
