from odoo.tests.common import TransactionCase


class TestSalesReporting(TransactionCase):
    def test_project_revenue_view_contains_project(self):
        report_model = self.env["od19.sales.project.revenue.report"]
        self.assertIn("project_id", report_model._fields)

    def test_project_revenue_view_contains_company_id(self):
        report_model = self.env["od19.sales.project.revenue.report"]
        self.assertIn("company_id", report_model._fields)

    def test_repeat_business_view_contains_owner_and_contractor(self):
        report_model = self.env["od19.sales.repeat.business.report"]
        self.assertIn("commercial_customer_id", report_model._fields)
        self.assertIn("project_owner_id", report_model._fields)

    def test_repeat_business_view_contains_company_id(self):
        report_model = self.env["od19.sales.repeat.business.report"]
        self.assertIn("company_id", report_model._fields)

