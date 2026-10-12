from datetime import date

from odoo.exceptions import UserError, ValidationError
from .common import MoneyInReportCommon


class TestMoneyInReportWizard(MoneyInReportCommon):
    def test_date_validation_invalid(self):
        """TR-5.1: date_from > date_to raises ValidationError (AC-11)."""
        with self.assertRaises(ValidationError):
            self.env["od19.money.in.report.wizard"].create(
                {
                    "date_from": date(2026, 10, 31),
                    "date_to": date(2026, 10, 1),
                    "phase": "phase1_invoice_based",
                    "company_id": self.company.id,
                }
            )

    def test_date_validation_valid(self):
        wizard = self._create_wizard(
            date_from=date(2026, 10, 1), date_to=date(2026, 10, 31)
        )
        self.assertEqual(wizard.date_from, date(2026, 10, 1))

    def test_generate_report_success(self):
        """TR-5.2: action_generate_report creates run + lines."""
        self._create_invoice(product=self.product, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(phase="phase1_invoice_based")
        action = wizard.action_generate_report()
        self.assertEqual(action["type"], "ir.actions.act_window")

    def test_generate_report_no_lines_raises(self):
        """TR-5.3: action_generate_report raises when no lines generated."""
        wizard = self._create_wizard(
            phase="phase1_invoice_based",
            date_from=date(2020, 1, 1),
            date_to=date(2020, 1, 31),
        )
        with self.assertRaises(UserError):
            wizard.action_generate_report()

    def test_preview_counts_on_wizard(self):
        self._create_invoice(product=self.product, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(phase="phase1_invoice_based")
        self.assertGreater(wizard.matching_line_count, 0)
