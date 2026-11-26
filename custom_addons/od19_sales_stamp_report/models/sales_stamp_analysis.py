from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import _, models

REPORT_MODEL = "od19.sales.stamp.report"

# Number of period steps that make up one year, per period type.
STEPS_PER_YEAR = {"year": 1, "quarter": 4, "month": 12}

# Dimensions offered by the wizard / report (technical field -> label).
DIMENSIONS = [
    ("department_id", "Department"),
    ("partner_id", "Customer"),
    ("user_id", "Salesperson"),
    ("sale_mode", "Sale Mode"),
    ("project_id", "Project"),
    ("team_id", "Sales Team"),
    ("project_owner_id", "Project Owner"),
    ("confirmed_by_id", "Confirmed By"),
]

AGGREGATES = [
    "order_count:sum",
    "amount_untaxed:sum",
    "amount_total:sum",
]


class Od19SalesStampAnalysis(models.AbstractModel):
    """Reusable grouping / comparison engine for the stamp date report.

    Turns the raw ``od19.sales.stamp.report`` view into period and dimension
    summaries enriched with share %, Year-over-Year and Month-over-Month
    growth. Shared by the PDF report and the XLSX export.
    """

    _name = "od19.sales.stamp.report.analysis"
    _description = "Sales Stamp Report Analysis Engine"

    # ------------------------------------------------------------------
    # Period helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        return value

    @classmethod
    def _period_start(cls, value, period_type):
        value = cls._to_date(value)
        if period_type == "year":
            return value.replace(month=1, day=1)
        if period_type == "quarter":
            return value.replace(month=((value.month - 1) // 3) * 3 + 1, day=1)
        return value.replace(day=1)

    @classmethod
    def _shift_period(cls, start, period_type, steps):
        if period_type == "year":
            return start.replace(year=start.year + steps)
        if period_type == "quarter":
            return start + relativedelta(months=3 * steps)
        return start + relativedelta(months=steps)

    @classmethod
    def _period_label(cls, start, period_type):
        if period_type == "year":
            return str(start.year)
        if period_type == "quarter":
            return "%s Q%d" % (start.year, (start.month - 1) // 3 + 1)
        return start.strftime("%Y-%m")

    @classmethod
    def _shift_date_by_years(cls, value, years):
        value = cls._to_date(value)
        return value.replace(year=value.year + years)

    @classmethod
    def _period_starts(cls, date_from, date_to, period_type):
        start = cls._period_start(date_from, period_type)
        end = cls._period_start(date_to, period_type)
        starts = []
        while start <= end:
            starts.append(start)
            start = cls._shift_period(start, period_type, 1)
        return starts

    @staticmethod
    def _growth(current, previous):
        """Return percentage growth, ``None`` when there is no base value."""
        if previous:
            return (current - previous) / previous * 100.0
        return None if current else 0.0

    # ------------------------------------------------------------------
    # Domains
    # ------------------------------------------------------------------
    def _base_domain(self, filters, date_from=None, date_to=None):
        domain = []
        if date_from and date_to:
            domain += [
                ("stamp_date", ">=", date_from),
                ("stamp_date", "<=", date_to),
            ]
        if filters.get("company_id"):
            domain.append(("company_id", "=", filters["company_id"]))
        if filters.get("department_ids"):
            domain.append(("department_id", "in", filters["department_ids"]))
        if filters.get("sale_mode"):
            domain.append(("sale_mode", "=", filters["sale_mode"]))
        if filters.get("user_ids"):
            domain.append(("user_id", "in", filters["user_ids"]))
        if filters.get("partner_ids"):
            domain.append(("partner_id", "in", filters["partner_ids"]))
        return domain

    # ------------------------------------------------------------------
    # Low level reads
    # ------------------------------------------------------------------
    def _read_day_buckets(self, domain):
        """Return ``{date: (orders, untaxed, total)}`` keyed by stamp date."""
        groups = self.env[REPORT_MODEL]._read_group(
            domain,
            groupby=["stamp_date:day"],
            aggregates=AGGREGATES,
        )
        buckets = {}
        for stamp, orders, untaxed, total in groups:
            key = self._to_date(stamp)
            buckets[key] = (orders or 0, untaxed or 0.0, total or 0.0)
        return buckets

    def _aggregate_periods(self, buckets, date_from, date_to, period_type):
        agg = {}
        for day, (orders, untaxed, total) in buckets.items():
            if day < date_from or day > date_to:
                continue
            start = self._period_start(day, period_type)
            cur = agg.get(start, (0, 0.0, 0.0))
            agg[start] = (
                cur[0] + orders,
                cur[1] + untaxed,
                cur[2] + total,
            )
        return agg

    # ------------------------------------------------------------------
    # Public summaries
    # ------------------------------------------------------------------
    def get_period_rows(self, filters):
        """Return one row per period with share %, YoY and MoM."""
        period_type = filters["period_type"]
        date_from = self._to_date(filters["date_from"])
        date_to = self._to_date(filters["date_to"])
        steps = STEPS_PER_YEAR[period_type]

        first_period = self._period_start(date_from, period_type)
        window_from = self._shift_period(first_period, period_type, -steps)
        window_domain = self._base_domain(filters, window_from, date_to)
        window_agg = self._aggregate_periods(
            self._read_day_buckets(window_domain), window_from, date_to, period_type
        )

        starts = self._period_starts(date_from, date_to, period_type)
        display_total = sum(
            window_agg.get(start, (0, 0.0, 0.0))[1] for start in starts
        )

        rows = []
        for start in starts:
            orders, untaxed, total = window_agg.get(start, (0, 0.0, 0.0))
            prev = window_agg.get(self._shift_period(start, period_type, -1), (0, 0.0, 0.0))
            prev_year = window_agg.get(
                self._shift_period(start, period_type, -steps), (0, 0.0, 0.0)
            )
            rows.append(
                {
                    "key": start,
                    "label": self._period_label(start, period_type),
                    "orders": orders,
                    "amount_untaxed": untaxed,
                    "amount_total": total,
                    "share_pct": (untaxed / display_total * 100.0)
                    if display_total
                    else 0.0,
                    "prev_year_untaxed": prev_year[1],
                    "yoy_pct": self._growth(untaxed, prev_year[1]),
                    "prev_period_untaxed": prev[1],
                    "mom_pct": self._growth(untaxed, prev[1]),
                }
            )
        return rows

    def _dimension_label(self, dimension, value):
        if value in (False, None):
            return _("Undefined")
        if isinstance(value, str):
            field = self.env[REPORT_MODEL]._fields.get(dimension)
            selection = dict(field.selection) if field and field.selection else {}
            return selection.get(value, value)
        return value.display_name

    def get_dimension_rows(self, filters, dimension):
        """Return one row per dimension value with share % and YoY."""
        date_from = self._to_date(filters["date_from"])
        date_to = self._to_date(filters["date_to"])
        cur_domain = self._base_domain(filters, date_from, date_to)
        groups = self.env[REPORT_MODEL]._read_group(
            cur_domain,
            groupby=[dimension],
            aggregates=AGGREGATES,
        )
        rows = []
        for value, orders, untaxed, total in groups:
            rows.append(
                {
                    "key": value.id if hasattr(value, "id") else value,
                    "label": self._dimension_label(dimension, value),
                    "orders": orders or 0,
                    "amount_untaxed": untaxed or 0.0,
                    "amount_total": total or 0.0,
                }
            )

        total_untaxed = sum(row["amount_untaxed"] for row in rows)

        prev_domain = self._base_domain(
            filters,
            self._shift_date_by_years(date_from, -1),
            self._shift_date_by_years(date_to, -1),
        )
        prev_groups = self.env[REPORT_MODEL]._read_group(
            prev_domain,
            groupby=[dimension],
            aggregates=["amount_untaxed:sum"],
        )
        prev_map = {}
        for value, untaxed in prev_groups:
            key = value.id if hasattr(value, "id") else value
            prev_map[key] = untaxed or 0.0

        for row in rows:
            row["share_pct"] = (
                (row["amount_untaxed"] / total_untaxed * 100.0)
                if total_untaxed
                else 0.0
            )
            previous = prev_map.get(row["key"], 0.0)
            row["prev_year_untaxed"] = previous
            row["yoy_pct"] = self._growth(row["amount_untaxed"], previous)

        rows.sort(key=lambda r: r["amount_untaxed"], reverse=True)
        top_n = filters.get("top_n") or 0
        if top_n > 0:
            rows = rows[:top_n]
        return rows

    def build_report_data(self, filters):
        """Assemble every table consumed by the PDF report and XLSX export."""
        period_rows = self.get_period_rows(filters)
        dimension_tables = []
        for field, label in DIMENSIONS:
            rows = self.get_dimension_rows(filters, field)
            if rows:
                dimension_tables.append(
                    {"field": field, "label": label, "rows": rows}
                )

        totals = {
            "orders": sum(row["orders"] for row in period_rows),
            "amount_untaxed": sum(row["amount_untaxed"] for row in period_rows),
            "amount_total": sum(row["amount_total"] for row in period_rows),
        }
        company = self.env["res.company"].browse(
            filters.get("company_id") or self.env.company.id
        )
        return {
            "filters": filters,
            "period_rows": period_rows,
            "dimension_tables": dimension_tables,
            "totals": totals,
            "company": company,
            "period_label": dict(
                [("month", "Monthly"), ("quarter", "Quarterly"), ("year", "Yearly")]
            ).get(filters["period_type"], filters["period_type"]),
        }
