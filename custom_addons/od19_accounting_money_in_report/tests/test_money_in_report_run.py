from odoo.exceptions import UserError

from .common import MoneyInReportCommon


class TestMoneyInReportRun(MoneyInReportCommon):
    def setUp(self):
        super().setUp()
        self.run = self.env["od19.money.in.report.run"].create(
            {
                "name": "Test Run",
                "company_id": self.company.id,
                "date_from": "2026-10-01",
                "date_to": "2026-10-31",
                "phase": "phase1_invoice_based",
            }
        )

    def test_lock_snapshot_fields_on_done(self):
        """TR-2.1: write locked field on done run raises UserError (AC-1)."""
        self.run.status = "done"
        with self.assertRaises(UserError):
            self.run.write({"date_from": "2026-09-01"})

    def test_cannot_revert_done(self):
        """TR-2.2: write status done -> draft raises UserError (AC-2)."""
        self.run.status = "done"
        with self.assertRaises(UserError):
            self.run.write({"status": "draft"})

    def test_non_locked_field_editable_on_done(self):
        """TR-2.3: write non-locked field (notes) on done run succeeds."""
        self.run.status = "done"
        self.run.write({"notes": "Updated notes"})
        self.assertEqual(self.run.notes, "Updated notes")

    def test_locked_field_editable_on_draft(self):
        """TR-2.4: write locked field on draft run succeeds."""
        self.run.write({"date_from": "2026-09-01"})
        self.assertEqual(str(self.run.date_from), "2026-09-01")

    def test_line_count_compute(self):
        line = self.env["od19.money.in.report.line"].create(
            {
                "run_id": self.run.id,
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "recognized_amount": 100.0,
            }
        )
        self.run.invalidate_recordset(["line_count"])
        self.assertEqual(self.run.line_count, 1)
