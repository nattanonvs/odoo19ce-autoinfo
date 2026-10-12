from datetime import date

from .common import MoneyInReportCommon


class TestMoneyInReportLine(MoneyInReportCommon):
    def _create_line(self, **vals):
        base = {
            "run_id": self.env["od19.money.in.report.run"]
            .create(
                {
                    "name": "Line Test Run",
                    "company_id": self.company.id,
                    "date_from": "2026-10-01",
                    "date_to": "2026-10-31",
                }
            )
            .id,
            "company_id": self.company.id,
            "partner_id": self.partner.id,
        }
        base.update(vals)
        return self.env["od19.money.in.report.line"].create(base)

    def test_net_cash_compute(self):
        """TR-3.1: net_cash_amount = paid_amount - refund_amount (AC-8)."""
        line = self._create_line(paid_amount=500.0, refund_amount=100.0)
        self.assertEqual(line.net_cash_amount, 400.0)

    def test_profit_when_cost_available(self):
        """TR-3.2: profit = amount - cost when cost_preliminary_available=True (AC-9)."""
        line = self._create_line(
            recognized_amount=1000.0,
            recognized_cost=400.0,
            cost_preliminary_available=True,
        )
        self.assertEqual(line.recognized_profit, 600.0)
        self.assertEqual(line.recognized_margin_pct, 60.0)
        self.assertTrue(line.profit_preliminary_available)

    def test_profit_when_cost_unavailable(self):
        """TR-3.3: profit = False when cost_preliminary_available=False (AC-9)."""
        line = self._create_line(
            recognized_amount=1000.0,
            recognized_cost=0.0,
            cost_preliminary_available=False,
        )
        self.assertFalse(line.recognized_profit)
        self.assertFalse(line.recognized_margin_pct)
        self.assertFalse(line.profit_preliminary_available)

    def test_margin_pct(self):
        """TR-3.4: margin = (profit / amount) * 100 (AC-9)."""
        line = self._create_line(
            recognized_amount=500.0,
            recognized_cost=100.0,
            cost_preliminary_available=True,
        )
        self.assertAlmostEqual(line.recognized_margin_pct, 80.0, places=2)

    def test_cycle_days(self):
        """TR-3.5: cycle_days = (end - start).days (AC-10)."""
        line = self._create_line(
            cycle_start_date=date(2026, 10, 1),
            cycle_end_date=date(2026, 10, 11),
        )
        self.assertEqual(line.cycle_days, 10)

    def test_missing_start_date_when_no_stamp(self):
        """TR-3.6: missing_start_date = True when stamp_date is empty (AC-10)."""
        line = self._create_line(
            stamp_date=False,
            cycle_start_date=date(2026, 10, 1),
            cycle_end_date=date(2026, 10, 11),
        )
        self.assertTrue(line.missing_start_date)
