from datetime import date

from odoo.tests.common import TransactionCase


class TestSalesStampReport(TransactionCase):
    """Unit tests for the stamp date analysis view and engine."""

    def setUp(self):
        super().setUp()
        self.report_model = self.env["od19.sales.stamp.report"]
        self.analysis = self.env["od19.sales.stamp.report.analysis"]

    # ------------------------------------------------------------------
    # View model
    # ------------------------------------------------------------------
    def test_view_fields(self):
        for field in (
            "company_id",
            "stamp_date",
            "department_id",
            "sale_mode",
            "project_id",
            "project_owner_id",
            "partner_id",
            "user_id",
            "team_id",
            "confirmed_by_id",
            "order_count",
            "amount_untaxed",
            "amount_total",
        ):
            self.assertIn(field, self.report_model._fields)

    def test_view_is_readonly_sql_view(self):
        self.assertFalse(self.report_model._auto)

    # ------------------------------------------------------------------
    # Period helpers
    # ------------------------------------------------------------------
    def test_period_start_month(self):
        self.assertEqual(
            self.analysis._period_start(date(2026, 5, 17), "month"), date(2026, 5, 1)
        )

    def test_period_start_quarter(self):
        self.assertEqual(
            self.analysis._period_start(date(2026, 5, 17), "quarter"), date(2026, 4, 1)
        )

    def test_period_start_year(self):
        self.assertEqual(
            self.analysis._period_start(date(2026, 5, 17), "year"), date(2026, 1, 1)
        )

    def test_period_label(self):
        self.assertEqual(self.analysis._period_label(date(2026, 1, 1), "year"), "2026")
        self.assertEqual(
            self.analysis._period_label(date(2026, 4, 1), "quarter"), "2026 Q2"
        )
        self.assertEqual(
            self.analysis._period_label(date(2026, 5, 1), "month"), "2026-05"
        )

    def test_period_starts(self):
        starts = self.analysis._period_starts(
            date(2026, 1, 15), date(2026, 6, 10), "quarter"
        )
        self.assertEqual(starts, [date(2026, 1, 1), date(2026, 4, 1)])

    def test_growth_without_base(self):
        self.assertIsNone(self.analysis._growth(100.0, 0.0))
        self.assertEqual(self.analysis._growth(0.0, 0.0), 0.0)

    def test_growth_with_base(self):
        self.assertAlmostEqual(self.analysis._growth(150.0, 100.0), 50.0)

    # ------------------------------------------------------------------
    # Report assembly
    # ------------------------------------------------------------------
    def _filters(self, **overrides):
        filters = {
            "company_id": self.env.company.id,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "period_type": "month",
            "department_ids": [],
            "user_ids": [],
            "partner_ids": [],
            "sale_mode": False,
            "top_n": 5,
        }
        filters.update(overrides)
        return filters

    def test_build_report_data_structure(self):
        data = self.analysis.build_report_data(self._filters())
        self.assertIn("period_rows", data)
        self.assertIn("dimension_tables", data)
        self.assertIn("totals", data)
        self.assertIn("company", data)
        # One row per month of the requested year.
        self.assertEqual(len(data["period_rows"]), 12)
        self.assertEqual(data["period_rows"][0]["label"], "2026-01")

    def test_period_rows_have_growth_keys(self):
        rows = self.analysis.get_period_rows(self._filters(period_type="quarter"))
        self.assertEqual(len(rows), 4)
        for key in ("share_pct", "yoy_pct", "mom_pct", "prev_year_untaxed"):
            self.assertIn(key, rows[0])

    # ------------------------------------------------------------------
    # Wizard
    # ------------------------------------------------------------------
    def test_wizard_prepare_filters(self):
        wizard = self.env["od19.sales.stamp.report.wizard"].create(
            {
                "date_from": "2026-01-01",
                "date_to": "2026-12-31",
                "company_id": self.env.company.id,
                "period_type": "quarter",
                "top_n": 3,
            }
        )
        filters = wizard._prepare_filters()
        self.assertEqual(filters["period_type"], "quarter")
        self.assertEqual(filters["date_from"], "2026-01-01")
        self.assertEqual(filters["date_to"], "2026-12-31")
        self.assertEqual(filters["top_n"], 3)
        self.assertIsInstance(filters["department_ids"], list)
        self.assertEqual(filters["company_id"], self.env.company.id)
