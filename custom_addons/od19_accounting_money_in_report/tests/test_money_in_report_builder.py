from datetime import date

from .common import MoneyInReportCommon


class TestMoneyInReportBuilder(MoneyInReportCommon):
    def test_phase1_generates_invoice_lines(self):
        """TR-4.1: Phase 1 generates lines from posted invoices in date range (AC-3)."""
        invoice = self._create_invoice(
            product=self.product, qty=2.0, price=100.0, invoice_date=date(2026, 10, 5)
        )
        wizard = self._create_wizard(phase="phase1_invoice_based")
        counts = self.env["od19.money.in.report.builder"].get_preview_counts(wizard)
        self.assertGreaterEqual(counts["invoice_candidate_count"], 1)
        run = self.env["od19.money.in.report.builder"].create_run_from_wizard(wizard)
        self.assertEqual(run.status, "done")
        self.assertGreater(run.line_count, 0)
        line = run.line_ids[0]
        self.assertEqual(line.partner_id, self.partner)
        self.assertEqual(line.recognition_mode, "invoice_proxy")
        self.assertEqual(line.phase, "phase1_invoice_based")
        self.assertEqual(line.invoice_id, invoice)

    def test_phase1_recognized_amount(self):
        """TR-4.2: recognized_amount = invoice line subtotal in company currency (AC-3)."""
        self._create_invoice(product=self.product, qty=3.0, price=100.0, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(phase="phase1_invoice_based")
        run = self.env["od19.money.in.report.builder"].create_run_from_wizard(wizard)
        line = run.line_ids.filtered(lambda l: l.product_id == self.product)
        self.assertAlmostEqual(line.recognized_amount, 300.0, places=2)

    def test_phase2_generates_cash_lines(self):
        """TR-4.3/4.4: Phase 2A generates lines from cash events (AC-4)."""
        invoice = self._create_invoice(
            product=self.product, qty=1.0, price=100.0, invoice_date=date(2026, 10, 1)
        )
        payment = self.env["account.payment"].create(
            {
                "partner_id": self.partner.id,
                "partner_type": "customer",
                "payment_type": "inbound",
                "amount": 100.0,
                "date": date(2026, 10, 10),
                "journal_id": self.bank_journal.id,
            }
        )
        payment.action_post()
        # Reconcile payment with invoice
        receivable_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
        )
        payment_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
        )
        if receivable_lines and payment_lines:
            (receivable_lines + payment_lines).reconcile()

        wizard = self._create_wizard(phase="phase2_cash_invoice_based")
        run = self.env["od19.money.in.report.builder"].create_run_from_wizard(wizard)
        self.assertGreater(run.line_count, 0)
        line = run.line_ids[0]
        self.assertEqual(line.recognition_mode, "cash_based")
        self.assertAlmostEqual(line.paid_amount, 100.0, places=2)
        self.assertEqual(line.payment_date, date(2026, 10, 10))

    def test_preview_counts(self):
        """TR-4.5: preview counts compute correctly (AC-5)."""
        self._create_invoice(product=self.product, qty=1.0, price=100.0, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(phase="phase1_invoice_based")
        counts = self.env["od19.money.in.report.builder"].get_preview_counts(wizard)
        self.assertGreaterEqual(counts["invoice_candidate_count"], 1)
        self.assertGreaterEqual(counts["matching_line_count"], 1)

    def test_filter_by_partner(self):
        """TR-4.6: filter by partner works (AC-6)."""
        partner2 = self.env["res.partner"].create({"name": "Other Customer"})
        self._create_invoice(partner=self.partner, product=self.product, invoice_date=date(2026, 10, 5))
        self._create_invoice(partner=partner2, product=self.product, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(
            phase="phase1_invoice_based", partner_ids=[(6, 0, [self.partner.id])]
        )
        run = self.env["od19.money.in.report.builder"].create_run_from_wizard(wizard)
        for line in run.line_ids:
            self.assertEqual(line.partner_id, self.partner)

    def test_filter_by_product_category(self):
        """TR-4.7: filter by product category works (AC-6)."""
        self._create_invoice(product=self.product, invoice_date=date(2026, 10, 5))
        self._create_invoice(product=self.product_2, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(
            phase="phase1_invoice_based",
            product_categ_ids=[(6, 0, [self.product_category_2.id])],
        )
        run = self.env["od19.money.in.report.builder"].create_run_from_wizard(wizard)
        for line in run.line_ids:
            self.assertEqual(line.product_categ_id, self.product_category_2)

    def test_phase1_profit_preliminary(self):
        """Phase 1 profit is preliminary and computed when cost reliable."""
        self._create_invoice(product=self.product, qty=1.0, price=100.0, invoice_date=date(2026, 10, 5))
        wizard = self._create_wizard(phase="phase1_invoice_based")
        run = self.env["od19.money.in.report.builder"].create_run_from_wizard(wizard)
        line = run.line_ids[0]
        self.assertTrue(line.is_preliminary_profit)
        self.assertTrue(line.cost_preliminary_available)
        self.assertAlmostEqual(line.recognized_profit, 60.0, places=2)
