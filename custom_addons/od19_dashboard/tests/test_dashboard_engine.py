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
