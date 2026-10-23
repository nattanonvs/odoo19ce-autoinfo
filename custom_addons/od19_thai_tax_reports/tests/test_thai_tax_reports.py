# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests.common import TransactionCase


class TestThaiTaxReports(TransactionCase):
    """Basic tests for the Thai tax report wizard."""

    def _create_wizard(self, **overrides):
        vals = {
            "date_from": fields.Date.today(),
            "date_to": fields.Date.today(),
            "company_id": self.env.company.id,
            "report_type": "vat_sales",
        }
        vals.update(overrides)
        return self.env["thai.tax.report.wizard"].create(vals)

    def test_create_wizard_defaults(self):
        wizard = self._create_wizard()
        self.assertEqual(wizard.report_type, "vat_sales")
        self.assertEqual(wizard.company_id, self.env.company)
        self.assertTrue(wizard.date_from)
        self.assertTrue(wizard.date_to)

    def test_wizard_report_types(self):
        for report_type in ("vat_sales", "vat_purchase", "wht"):
            wizard = self._create_wizard(report_type=report_type)
            self.assertEqual(wizard.report_type, report_type)

    def test_wizard_date_range(self):
        date_from = fields.Date.today().replace(month=1, day=1)
        date_to = fields.Date.today().replace(month=12, day=31)
        wizard = self._create_wizard(date_from=date_from, date_to=date_to)
        self.assertEqual(wizard.date_from, date_from)
        self.assertEqual(wizard.date_to, date_to)

    def test_wht_certificate_report_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_wht_certificate")
        self.assertEqual(report.model, "withholding.tax.cert")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_wht_certificate_report_renders_cert_lines(self):
        """The certificate prints the amounts carried by the OCA cert lines."""
        partner = self.env["res.partner"].create({"name": "WHT Vendor Test"})
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": partner.id,
                "company_id": self.env.company.id,
                "date": fields.Date.today(),
                "income_tax_form": "pnd53",
                "wht_line": [
                    (
                        0,
                        0,
                        {
                            "wht_cert_income_type": "5",
                            "base": 1000.0,
                            "amount": 30.0,
                        },
                    )
                ],
            }
        )
        report = self.env.ref("od19_thai_tax_reports.action_wht_certificate")
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(report, cert.ids)
        rendered = html.decode()
        self.assertIn("หนังสือรับรองการหักภาษี", rendered)
        self.assertIn("1,000.00", rendered)
        self.assertIn("30.00", rendered)
