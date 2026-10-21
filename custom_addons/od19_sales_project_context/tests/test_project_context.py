from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create(
            {
                "name": "Main Contractor",
                "is_company": True,
                "od19_is_contractor": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Project Owner",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Commercial Customer",
                "is_company": True,
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )

    def _create_project(self, name, owner=None, contractor=None, job_no=None):
        vals = {
            "name": name,
            "job_no": job_no or f"JOB-{name[:4].upper()}-001",
        }
        if owner:
            vals["project_owner_id"] = owner.id
        if contractor:
            vals["contractor_ids"] = [(6, 0, contractor.ids)]
        return self.env["project.project"].create(vals)

    def test_sale_order_requires_project_context_consistency(self):
        project = self._create_project("Airport Expansion", owner=self.owner)

        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

        self.assertEqual(
            order.od19_project_id.project_owner_id, order.od19_project_owner_id
        )

    def test_project_owner_mismatch_is_blocked(self):
        project = self._create_project("Hospital Retrofit", owner=self.owner)
        another_owner = self.env["res.partner"].create({"name": "Another Owner"})

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": self.customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": another_owner.id,
                }
            )

    def test_project_owner_role_is_enforced_at_model_level(self):
        """Project owner role is validated on the model, not only via the view
        domain, so imports and automated flows cannot bypass the rule."""
        not_an_owner = self.env["res.partner"].create(
            {"name": "Not An Owner", "is_company": True}
        )

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": self.customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_owner_id": not_an_owner.id,
                }
            )

    def test_sale_order_accepts_any_partner_for_core_compatibility(self):
        """Core Odoo modules create sale orders with regular partners.

        Partner role validation is enforced at the view level (domain on
        partner_id), not at the model level, to preserve core compatibility.
        """
        regular_partner = self.env["res.partner"].create(
            {"name": "Regular Partner", "is_company": True}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": regular_partner.id,
                "od19_sale_mode": "one_time",
            }
        )
        self.assertEqual(order.partner_id, regular_partner)

    def test_onchange_project_sets_project_owner(self):
        project = self._create_project("Onchange Project", owner=self.owner)
        order = self.env["sale.order"].new(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
            }
        )
        order.od19_project_id = project
        order._onchange_od19_project_id()
        self.assertEqual(order.od19_project_owner_id, self.owner)

    # ------------------------------------------------------------------
    # B7 - Project cost & profit analysis before quoting
    # ------------------------------------------------------------------

    def _create_sale_order(self, project=None):
        vals = {
            "partner_id": self.customer.id,
            "od19_sale_mode": "one_time",
        }
        if project:
            vals["od19_project_id"] = project.id
        return self.env["sale.order"].create(vals)

    def _setup_analytic_accounts(self):
        company = self.env.company
        income = self.env["account.account"].search(
            [("account_type", "=", "income"), ("company_ids", "in", company.id)],
            limit=1,
        )
        expense = self.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "in", company.id)],
            limit=1,
        )
        counter = self.env["account.account"].search(
            [
                ("account_type", "=", "asset_current"),
                ("company_ids", "in", company.id),
            ],
            limit=1,
        )
        return income, expense, counter

    def _post_analytic_entry(self, project, account, balance, counter):
        """Post a two-line entry with 100% analytic distribution on project."""
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.to_date("2026-06-15"),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "analytic line",
                            "account_id": account.id,
                            "debit": balance if balance > 0 else 0.0,
                            "credit": -balance if balance < 0 else 0.0,
                            "analytic_distribution": {
                                str(project.account_id.id): 100
                            },
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "counter line",
                            "account_id": counter.id,
                            "debit": -balance if balance < 0 else 0.0,
                            "credit": balance if balance > 0 else 0.0,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def test_action_open_project_pnl_analysis_returns_wizard_action(self):
        project = self._create_project("Analysis Project", owner=self.owner)
        order = self._create_sale_order(project=project)
        action = order.action_open_project_pnl_analysis()
        self.assertEqual(action["res_model"], "od19.sale.order.pnl.analysis")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_sale_order_id"], order.id)

    def test_pnl_analysis_wizard_computes_project_margin(self):
        project = self._create_project("Margin Project", owner=self.owner)
        income, expense, counter = self._setup_analytic_accounts()
        self._post_analytic_entry(project, income, -1000.0, counter)
        self._post_analytic_entry(project, expense, 400.0, counter)
        order = self._create_sale_order(project=project)

        wizard = self.env["od19.sale.order.pnl.analysis"].create(
            {
                "sale_order_id": order.id,
                "date_from": fields.Date.to_date("2026-01-01"),
                "date_to": fields.Date.to_date("2026-12-31"),
            }
        )
        self.assertAlmostEqual(wizard.revenue, 1000.0, 2)
        self.assertAlmostEqual(wizard.cost, 400.0, 2)
        self.assertAlmostEqual(wizard.gross_margin, 600.0, 2)
        self.assertAlmostEqual(wizard.margin_percent, 60.0, 2)
        self.assertTrue(wizard.has_analytic)

    def test_pnl_analysis_wizard_without_project_shows_note(self):
        order = self._create_sale_order()
        wizard = self.env["od19.sale.order.pnl.analysis"].create(
            {"sale_order_id": order.id}
        )
        self.assertFalse(wizard.project_id)
        self.assertEqual(wizard.revenue, 0.0)
        self.assertTrue(wizard.note)

    def test_pnl_analysis_default_get_from_context(self):
        project = self._create_project("Context Project", owner=self.owner)
        order = self._create_sale_order(project=project)
        wizard = (
            self.env["od19.sale.order.pnl.analysis"]
            .with_context(default_sale_order_id=order.id)
            .create({})
        )
        self.assertEqual(wizard.sale_order_id, order)
