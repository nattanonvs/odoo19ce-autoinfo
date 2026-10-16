from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class TestDashboardFormulaEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Engine test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Engine widget",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "this_month",
            }
        )

    def test_aggregate_specs_deduplicates(self):
        specs = self.source._aggregate_specs(["amount_total", "__count", "amount_total"])
        self.assertEqual(specs, ["amount_total:sum", "__count"])

    def test_slot_map_parses_json(self):
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count", "w1": 2}'
        self.assertEqual(
            self.widget._formula_slot_map(),
            {"a": "amount_total", "b": "__count", "w1": 2},
        )

    def test_slot_map_is_empty_on_bad_json(self):
        self.widget.formula_slots = "not json"
        self.assertEqual(self.widget._formula_slot_map(), {})

    def test_requests_in_measure_mode(self):
        self.widget.formula_mode = "measure"
        self.assertEqual(
            self.widget._aggregate_requests(),
            [("value", "amount_total", "amount_total:sum")],
        )

    def test_requests_in_preset_mode(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count"}'
        self.assertEqual(
            self.widget._aggregate_requests(),
            [("a", "amount_total", "amount_total:sum"), ("b", "__count", "__count")],
        )

    def test_requests_in_custom_mode_use_direct_names(self):
        self.widget.formula_mode = "custom"
        self.widget.formula_expression = "amount_total / count_records"
        self.assertEqual(
            self.widget._aggregate_requests(),
            [
                ("amount_total", "amount_total", "amount_total:sum"),
                ("count_records", "__count", "__count"),
            ],
        )

    def test_allowed_names_include_slots_and_goal(self):
        self.widget.formula_mode = "custom"
        self.widget.formula_expression = "a / goal"
        allowed = self.widget._allowed_names()
        for name in ("a", "b", "goal", "total_a", "count_records", "amount_total"):
            self.assertIn(name, allowed)
        self.assertNotIn("__count", allowed)

    def test_validate_formula_config_accepts_preset(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count"}'
        self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_missing_slot(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amount_total"}'
        with self.assertRaises(ValidationError):
            self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_unknown_name(self):
        self.widget.formula_mode = "custom"
        self.widget.formula_expression = "a / secret"
        with self.assertRaises(ValidationError):
            self.widget._validate_formula_config()

    def test_effective_expression_for_measure_mode(self):
        self.widget.formula_mode = "measure"
        self.assertEqual(self.widget._effective_expression(), "value")

    def test_effective_expression_for_preset_mode(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "growth"
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count"}'
        self.assertEqual(self.widget._effective_expression(), "(a - b) / b * 100")

    def test_validate_formula_config_accepts_literal_weight_slots(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "weighted_average"
        self.widget.formula_slots = (
            '{"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1}'
        )
        self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_unknown_slot_measure(self):
        self.widget.formula_mode = "preset"
        self.widget.formula_type = "ratio"
        self.widget.formula_slots = '{"a": "amout_total", "b": "__count"}'
        with self.assertRaises(ValidationError):
            self.widget._validate_formula_config()


class TestDashboardRuleEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Rule engine dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget A",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "this_month",
            }
        )
        cls.widget_b = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget B",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "__count",
            }
        )

    def _rule(self, **values):
        values.setdefault("widget_id", self.widget_a.id)
        values.setdefault("status", "red")
        return self.env["od19.dashboard.widget.rule"].create(values)

    def test_operand_constant(self):
        rule = self._rule(compare_type="constant", compare_value=12.5)
        self.assertEqual(rule._compare_operand({"value": 3.0}), 12.5)

    def test_operand_goal(self):
        rule = self._rule(compare_type="goal")
        self.assertEqual(rule._compare_operand({"value": 3.0, "goal": 900.0}), 900.0)

    def test_operand_percent_of_goal(self):
        rule = self._rule(compare_type="percent_of_goal", compare_percent=80.0)
        self.assertEqual(rule._compare_operand({"value": 3.0, "goal": 1000.0}), 800.0)

    def test_operand_shifted_period(self):
        rule = self._rule(compare_type="yty")
        self.assertEqual(rule._compare_operand({"shifts": {"yty": 42.0}}), 42.0)
        self.assertIsNone(rule._compare_operand({"shifts": {}}))

    def test_operand_other_widget(self):
        rule = self._rule(compare_type="widget", compare_widget_id=self.widget_b.id)
        context = {"widget_values": {self.widget_b.id: 7.0}}
        self.assertEqual(rule._compare_operand(context), 7.0)

    def test_evaluate_rules_first_match_wins(self):
        self._rule(sequence=10, operator="<=", compare_value=100.0, status="red")
        self._rule(sequence=20, operator="<=", compare_value=500.0, status="yellow")
        status, source = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual(status, "red")
        self.assertEqual(source, "rule")

    def test_evaluate_rules_continues_when_rule_does_not_match(self):
        self._rule(sequence=10, operator="<=", compare_value=10.0, status="red")
        self._rule(sequence=20, operator="<=", compare_value=500.0, status="yellow")
        status, source = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual((status, source), ("yellow", "rule"))

    def test_evaluate_rules_falls_back_to_default_status(self):
        self.widget_a.default_status = "grey"
        self.assertEqual(self.widget_a._evaluate_rules({"value": 50.0}), ("grey", "default"))

    def test_evaluate_rules_skips_inactive_rules(self):
        self._rule(compare_value=100.0, status="red", active=False)
        self.widget_a.default_status = "green"
        self.assertEqual(self.widget_a._evaluate_rules({"value": 50.0}), ("green", "default"))

    def test_evaluate_rules_ignores_none_value(self):
        self._rule(compare_value=100.0, status="red")
        self.widget_a.default_status = "grey"
        self.assertEqual(self.widget_a._evaluate_rules({"value": None}), ("grey", "default"))

    def test_required_shifts_collects_delta_rules_and_formula(self):
        self.widget_a.delta_basis = "mtm"
        self.widget_a.formula_mode = "custom"
        self.widget_a.formula_expression = "amount_total"
        self.widget_a.formula_basis = "qtq"
        self._rule(compare_type="yty", status="red")
        self.assertEqual(self.widget_a._required_shifts(), {"mtm", "qtq", "yty"})

    def test_required_shifts_skips_delta_when_hidden(self):
        self.widget_a.show_delta = False
        self.widget_a.delta_basis = "mtm"
        self.assertEqual(self.widget_a._required_shifts(), set())

    def test_date_bounds_applies_previous_shift(self):
        # ``apply_shift(..., "previous")`` uses inclusive bounds, so a 12 day
        # window (2026-03-05 → 2026-03-16) shifts to 2026-02-21 → 2026-03-04.
        # This mirrors ``test_shift_previous_keeps_period_length`` in
        # ``test_dashboard_formula.py``.
        bounds = self.widget_a._date_bounds("this_year", "2026-03-05", "2026-03-16", shift="previous")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-02-21 00:00:00"),
                ("date_order", "<=", "2026-03-04 23:59:59"),
            ],
        )

    def test_date_bounds_applies_yty_shift(self):
        bounds = self.widget_a._date_bounds("this_year", "2026-03-01", "2026-03-31", shift="yty")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2025-03-01 00:00:00"),
                ("date_order", "<=", "2025-03-31 23:59:59"),
            ],
        )

    def test_date_bounds_shift_none_keeps_the_period(self):
        bounds = self.widget_a._date_bounds("this_year", "2026-03-01", "2026-03-31")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-03-01 00:00:00"),
                ("date_order", "<=", "2026-03-31 23:59:59"),
            ],
        )

    def test_period_bounds_all_time_has_no_bounds(self):
        start, end, field_type = self.widget_a._period_bounds("all_time")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertEqual(field_type, "datetime")

    def test_period_bounds_without_date_key_has_no_bounds(self):
        start, end, field_type = self.widget_b._period_bounds("this_month")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertEqual(field_type, "date")

    def test_period_bounds_overdue_starts_at_none(self):
        today = fields.Date.context_today(self.widget_a)
        start, end, _field_type = self.widget_a._period_bounds("overdue")
        self.assertIsNone(start)
        self.assertEqual(end, today - timedelta(days=1))

    def test_date_bounds_on_a_date_field_has_no_time_suffix(self):
        widget = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Date field widget",
                "widget_type": "kpi",
                "source_id": self.env.ref("od19_dashboard.source_account_move").id,
                "measure_key": "amount_total",
                "date_key": "invoice_date",
                "date_range": "this_year",
            }
        )
        bounds = widget._date_bounds("this_year", "2026-03-01", "2026-03-31")
        self.assertEqual(
            bounds,
            [
                ("invoice_date", ">=", "2026-03-01"),
                ("invoice_date", "<=", "2026-03-31"),
            ],
        )

    def test_is_lower_better_inferred_from_the_first_red_rule(self):
        self.assertFalse(self.widget_a._is_lower_better())
        self._rule(operator="<=", compare_value=100.0, status="red")
        self.assertFalse(self.widget_a._is_lower_better())
        self.widget_a.rule_ids.unlink()
        self._rule(operator=">=", compare_value=100.0, status="red")
        self.assertTrue(self.widget_a._is_lower_better())

    def test_unresolved_names_detects_unbound_slot(self):
        self.widget_a.formula_mode = "custom"
        self.widget_a.formula_expression = "a + amount_total"
        self.assertEqual(self.widget_a._unresolved_names(), ["a"])
        self.widget_a.formula_slots = '{"a": "amount_total"}'
        self.assertEqual(self.widget_a._unresolved_names(), [])


class TestDashboardOrdering(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Ordering dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls._make_widget(cls, "Widget A")
        cls.widget_b = cls._make_widget(cls, "Widget B")
        cls.widget_c = cls._make_widget(cls, "Widget C")

    def _make_widget(self, name):
        return self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": name,
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )

    def test_dependency_ids_from_rule_and_expression(self):
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": self.widget_b.id,
                "status": "green",
            }
        )
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_a.id
        self.assertEqual(self.widget_a._dependency_ids(), [self.widget_b.id])
        self.assertEqual(self.widget_c._dependency_ids(), [self.widget_a.id])

    def test_dependency_ids_never_contains_the_widget_itself(self):
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_c.id
        self.assertEqual(self.widget_c._dependency_ids(), [])

    def test_compute_order_places_dependencies_first(self):
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_a.id
        ordered = self.dashboard._compute_order()
        self.assertLess(ordered.index(self.widget_a), ordered.index(self.widget_c))

    def test_compute_order_survives_a_cycle(self):
        self.widget_a.formula_mode = "custom"
        self.widget_a.formula_expression = "count_records + widget_%s" % self.widget_b.id
        self.widget_b.formula_mode = "custom"
        self.widget_b.formula_expression = "count_records + widget_%s" % self.widget_a.id
        ordered = self.dashboard._compute_order()
        # Widget C has no dependency, so it is emitted first. The A/B pair is a
        # cycle and cannot be ordered: the fallback emits the remaining widgets
        # in (sequence, id) order, which here is A then B. No widget is lost.
        self.assertEqual(ordered, [self.widget_c, self.widget_a, self.widget_b])

    def test_compute_order_skips_inactive_widgets(self):
        self.widget_b.active = False
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % self.widget_b.id
        ordered = self.dashboard._compute_order()
        # An inactive widget is never emitted, but reading it must not block
        # the widget that refers to it.
        self.assertEqual(ordered, [self.widget_a, self.widget_c])

    def test_compute_order_ignores_a_dependency_outside_the_dashboard(self):
        other = self.env["od19.dashboard"].create({"name": "Other ordering dashboard"})
        foreign = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": other.id,
                "name": "Foreign widget",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        self.widget_c.formula_mode = "custom"
        self.widget_c.formula_expression = "count_records + widget_%s" % foreign.id
        ordered = self.dashboard._compute_order()
        # A dependency that is not part of this dashboard is already satisfied,
        # so it must neither deadlock the sort nor be emitted.
        self.assertEqual(len(ordered), 3)
        self.assertNotIn(foreign, ordered)

    def test_get_dashboard_data_returns_every_widget_with_a_cross_widget_rule(self):
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": self.widget_b.id,
                "operator": ">",
                "status": "green",
            }
        )
        data = self.env["od19.dashboard"].get_dashboard_data(self.dashboard.id)
        self.assertEqual(len(data["widgets"]), 3)
        self.assertEqual(
            {widget["id"] for widget in data["widgets"]},
            {self.widget_a.id, self.widget_b.id, self.widget_c.id},
        )
        # Widget A reads Widget B, so B must be rendered (and therefore
        # computed) before A: the emitted order proves the dependency wins.
        self.assertEqual(
            [widget["id"] for widget in data["widgets"]],
            [self.widget_b.id, self.widget_c.id, self.widget_a.id],
        )
        self.assertIn("status_source", data["widgets"][0])


# These tests create ``sale.order`` records. Another installed module
# (``od19_sales_project_context``) adds a required field on ``sale.order`` that
# the registry does not carry yet while ``od19_dashboard`` is being installed,
# so the class runs during ``post_install`` where the registry is complete.
# The tests are neither skipped nor weakened: they run in the same
# ``--test-enable`` pass.
@tagged("post_install", "-at_install")
class TestDashboardPreview(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Preview test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.base_values = {
            "dashboard_id": cls.dashboard.id,
            "name": "Preview widget",
            "widget_type": "kpi",
            "source_id": cls.source.id,
            "measure_key": "amount_total",
            "date_key": "date_order",
            "date_range": "all_time",
        }

    def _preview(self, **overrides):
        values = dict(self.base_values)
        values.update(overrides)
        return self.env["od19.dashboard"].preview_widget(values)

    def test_preview_returns_a_value_and_a_count(self):
        result = self._preview()
        self.assertIn("value", result)
        self.assertIsInstance(result["record_count"], int)
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["status_source"], "default")

    def test_preview_evaluates_a_preset_formula(self):
        result = self._preview(
            formula_mode="preset",
            formula_type="ratio",
            formula_slots='{"a": "amount_total", "b": "__count"}',
        )
        self.assertEqual(result["formula_expression"], "a / b")
        self.assertEqual([item["alias"] for item in result["operands"]], ["a", "b"])

    def test_preview_evaluates_a_literal_weight_slot(self):
        result = self._preview(
            formula_mode="preset",
            formula_type="weighted_average",
            formula_slots='{"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1}',
        )
        operands = {item["alias"]: item["value"] for item in result["operands"]}
        expected = (operands["a"] * 2 + operands["b"] * 1) / 3
        self.assertAlmostEqual(result["value"], expected)

    def test_preview_applies_the_first_matching_rule(self):
        result = self._preview(
            rule_ids=[
                (0, 0, {
                    "operator": "<",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "red",
                }),
                (0, 0, {
                    "operator": ">=",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "yellow",
                }),
            ],
        )
        self.assertEqual(result["status"], "yellow")
        self.assertEqual(result["status_source"], "rule")

    def test_preview_refuses_a_broken_formula(self):
        with self.assertRaises(ValidationError):
            self._preview(formula_mode="custom", formula_expression="__import__('os').system('dir')")
        with self.assertRaises(ValidationError):
            self._preview(formula_mode="preset", formula_type="ratio", formula_slots='{"a": "amount_total"}')

    def test_preview_writes_nothing(self):
        before = self.env["od19.dashboard.widget"].search_count(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self._preview()
        after = self.env["od19.dashboard.widget"].search_count(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self.assertEqual(before, after)

    def test_preview_returns_a_series_preview_for_charts(self):
        result = self._preview(widget_type="bar", groupby_key="state", limit=5)
        self.assertLessEqual(len(result["series_preview"]), 5)

    def test_preview_reads_the_aggregate_of_an_ungrouped_row(self):
        """A KPI reads one row without a group value, so alias 0 maps to row[0]."""
        partner = self.env["res.partner"].create({"name": "Preview customer"})
        self.env["sale.order"].create({"partner_id": partner.id})
        expected = float(self.env["sale.order"].search_count([]))
        self.assertGreater(expected, 0)
        result = self._preview(
            measure_key="__count",
            formula_mode="custom",
            formula_expression="count_records",
        )
        self.assertEqual(result["value"], expected)

    def test_preview_reads_the_aggregate_of_a_grouped_row(self):
        """A chart reads grouped rows: the group value precedes the aggregates."""
        rows = self.env["sale.order"]._read_group([], ["state"], ["__count"])
        self.assertLessEqual(len(rows), 5)
        result = self._preview(
            widget_type="bar",
            groupby_key="state",
            limit=50,
            measure_key="__count",
            formula_mode="custom",
            formula_expression="count_records",
        )
        self.assertEqual(
            sum(item["value"] for item in result["series_preview"]),
            float(sum(count for _state, count in rows)),
        )

    def test_preview_ignores_non_creation_rule_commands(self):
        """Link / clear / delete commands must not become empty create commands."""
        rule = {
            "operator": ">",
            "compare_type": "constant",
            "compare_value": 1,
            "status": "red",
        }
        values = self.env["od19.dashboard"]._normalise_preview_values(
            {
                "name": "Draft",
                "rule_ids": [(4, 7, 0), (5, 0, 0), (2, 7, 0), (0, 0, rule)],
            }
        )
        self.assertEqual(values["rule_ids"], [(0, 0, rule)])

    def test_preview_reads_a_chained_dependency(self):
        """A widget the draft reads must itself be computed after its own dependency."""
        other = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Constant",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "all_time",
                "sequence": 20,
                "formula_mode": "custom",
                "formula_expression": "100",
            }
        )
        dependent = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Chained",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "all_time",
                "sequence": 5,
                "formula_mode": "custom",
                "formula_expression": "widget_%s + 1" % other.id,
            }
        )
        result = self._preview(
            formula_mode="custom", formula_expression="widget_%s" % dependent.id
        )
        self.assertEqual(result["value"], 101.0)

    def test_preview_shares_a_bucket_against_the_displayed_buckets(self):
        partner = self.env["res.partner"].create({"name": "Share customer"})
        self.env["sale.order"].create({"partner_id": partner.id})
        result = self._preview(
            widget_type="pie",
            groupby_key="state",
            limit=50,
            measure_key="__count",
            formula_mode="preset",
            formula_type="share",
            formula_slots='{"a": "__count"}',
        )
        series = result["series_preview"]
        self.assertTrue(series)
        self.assertAlmostEqual(sum(item["value"] for item in series), 100.0)

    def test_number_text_keeps_a_single_minus_sign(self):
        widget = self.env["od19.dashboard.widget"].new({"name": "Number text"})
        self.assertEqual(widget._number_text(-1234.5, 2), "-1,234.5")
        self.assertEqual(widget._number_text(1234.5, 2), "1,234.5")
        self.assertEqual(widget._number_text(0, 0), "0")
