from odoo.exceptions import ValidationError
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
        bounds = self.widget_a._date_bounds("this_year", "2026-03-05", "2026-03-16", shift="previous")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-02-22 00:00:00"),
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
