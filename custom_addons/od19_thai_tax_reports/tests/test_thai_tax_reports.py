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
        for report_type in ("vat_sales", "vat_purchase", "wht", "pnd54"):
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

    def test_pnd54_register_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_pnd54_register")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_pnd54_register_gathers_pnd54_withholding(self):
        """Only withholding moves flagged PND54 are listed by the register."""
        wht_account = self.env["account.account"].create(
            {
                "code": "X991001",
                "name": "WHT Payable PND54 Test",
                "account_type": "asset_current",
                "wht_account": True,
            }
        )
        base_account = self.env["account.account"].create(
            {
                "code": "X991002",
                "name": "PND54 Base Test",
                "account_type": "expense",
            }
        )
        wht_tax = self.env["account.withholding.tax"].create(
            {
                "name": "WHT PND54 3%",
                "account_id": wht_account.id,
                "amount": 3.0,
                "income_tax_form": "pnd54",
            }
        )
        partner = self.env["res.partner"].create({"name": "PND54 Vendor"})
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Base",
                            "debit": 1000.0,
                            "account_id": base_account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT",
                            "credit": 1000.0,
                            "account_id": wht_account.id,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        wht_move = self.env["account.withholding.move"].create(
            {
                "move_id": move.id,
                "partner_id": partner.id,
                "amount_income": 1000.0,
                "amount_wht": 30.0,
                "wht_tax_id": wht_tax.id,
                "company_id": self.env.company.id,
            }
        )
        values = (
            self.env["report.od19_thai_tax_reports.pnd54_register"]
            .with_context(
                date_from=fields.Date.today(),
                date_to=fields.Date.today(),
                company_id=self.env.company.id,
            )
            ._get_report_values(wht_move.ids)
        )
        self.assertEqual(len(values["lines"]), 1)
        self.assertEqual(values["lines"][0]["partner_name"], "PND54 Vendor")
        self.assertAlmostEqual(values["total_base"], 1000.0)
        self.assertAlmostEqual(values["total_wht"], 30.0)

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
