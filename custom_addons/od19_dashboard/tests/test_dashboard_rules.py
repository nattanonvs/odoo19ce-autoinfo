from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDashboardRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Rule test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget A",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "__count",
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

    def test_widget_has_formula_fields(self):
        for name in (
            "formula_mode",
            "formula_type",
            "formula_slots",
            "formula_expression",
            "formula_id",
            "visible_expression",
            "formula_basis",
            "delta_basis",
            "default_status",
            "rule_ids",
        ):
            self.assertIn(name, self.env["od19.dashboard.widget"]._fields)

    def test_widget_formula_defaults(self):
        self.assertEqual(self.widget_a.formula_mode, "measure")
        self.assertEqual(self.widget_a.formula_basis, "previous")
        self.assertEqual(self.widget_a.delta_basis, "previous")
        self.assertEqual(self.widget_a.default_status, "green")
        self.assertEqual(self.widget_a.formula_slots, "{}")

    def test_rule_defaults(self):
        rule = self.env["od19.dashboard.widget.rule"].create(
            {"widget_id": self.widget_a.id, "status": "red"}
        )
        self.assertEqual(rule.operator, "<=")
        self.assertEqual(rule.compare_type, "constant")
        self.assertEqual(rule.sequence, 10)
        self.assertTrue(rule.active)

    def test_rule_rejects_self_reference(self):
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": self.widget_a.id,
                    "compare_type": "widget",
                    "compare_widget_id": self.widget_a.id,
                    "status": "red",
                }
            )

    def test_rule_accepts_cross_dashboard_widget(self):
        """A rule may compare with a widget of another dashboard (phase 2, item 6)."""
        other = self.env["od19.dashboard"].create({"name": "Other dashboard"})
        other_widget = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": other.id,
                "name": "Other widget",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        rule = self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": other_widget.id,
                "status": "red",
            }
        )
        self.assertEqual(rule.compare_widget_id, other_widget)

    def test_rule_exposes_the_alert_message(self):
        rule = self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "status": "red",
                "alert_message": "Sales below target",
            }
        )
        self.assertEqual(rule._to_values()["alert_message"], "Sales below target")

    def test_rule_requires_widget_target(self):
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {"widget_id": self.widget_a.id, "compare_type": "widget", "status": "red"}
            )

    def test_rule_requires_percent_for_percent_of_goal(self):
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": self.widget_a.id,
                    "compare_type": "percent_of_goal",
                    "compare_percent": 0,
                    "status": "red",
                }
            )

    def test_rule_ordering_is_sequence_then_id(self):
        first = self.env["od19.dashboard.widget.rule"].create(
            {"widget_id": self.widget_a.id, "sequence": 20, "status": "green"}
        )
        second = self.env["od19.dashboard.widget.rule"].create(
            {"widget_id": self.widget_a.id, "sequence": 10, "status": "red"}
        )
        self.assertEqual(self.widget_a.rule_ids[0], second)
        self.assertEqual(self.widget_a.rule_ids[1], first)


class TestDashboardBuilderMeta(TransactionCase):
    """The builder reads the formula catalogues; the legacy thresholds are gone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Meta test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_model = cls.env["od19.dashboard.widget"]

    def _base_values(self, **overrides):
        values = {
            "dashboard_id": self.dashboard.id,
            "name": "Meta widget",
            "widget_type": "kpi",
            "source_id": self.source.id,
            "measure_key": "amount_total",
        }
        values.update(overrides)
        return values

    def test_widget_no_longer_carries_the_threshold_fields(self):
        for name in ("threshold_mode", "warning_value", "critical_value"):
            self.assertNotIn(name, self.widget_model._fields)

    def test_builder_meta_publishes_the_formula_modes(self):
        meta = self.env["od19.dashboard"].get_builder_meta()
        self.assertNotIn("threshold_modes", meta)
        self.assertEqual(
            [item["key"] for item in meta["formula_modes"]],
            ["measure", "preset", "custom", "library"],
        )
        formula_types = {item["key"]: item for item in meta["formula_types"]}
        self.assertIn("ratio", formula_types)
        # The builder draws the slot table from the catalogue, so every preset
        # must ship its slots, its variadic flag and its expression.
        self.assertEqual(formula_types["ratio"]["slots"], ["a", "b"])
        self.assertEqual(
            formula_types["weighted_average"]["slots"], ["a", "b", "w1", "w2"]
        )
        self.assertEqual(formula_types["ratio"]["expression"], "a / b")
        self.assertFalse(formula_types["ratio"]["variadic"])
        self.assertTrue(formula_types["sum"]["variadic"])
        self.assertTrue(formula_types["average"]["variadic"])
        for item in meta["formula_types"]:
            self.assertTrue(
                item["slots"], "Preset '%s' must declare its slots." % item["key"]
            )

    def test_builder_meta_publishes_the_rule_catalogues(self):
        meta = self.env["od19.dashboard"].get_builder_meta()
        self.assertEqual(
            [item["key"] for item in meta["operators"]],
            [">", ">=", "<", "<=", "==", "!="],
        )
        compare_keys = [item["key"] for item in meta["compare_types"]]
        for key in ("constant", "goal", "percent_of_goal", "widget", "prev", "yty", "mtm", "qtq"):
            self.assertIn(key, compare_keys)
        self.assertEqual(
            [item["key"] for item in meta["statuses"]],
            ["red", "yellow", "green", "grey"],
        )
        self.assertEqual(
            [item["key"] for item in meta["period_bases"]],
            ["previous", "yty", "mtm", "qtq"],
        )

    def test_to_config_serialises_the_formula_and_the_rules(self):
        widget = self.widget_model.create(
            self._base_values(
                formula_mode="preset",
                formula_type="ratio",
                formula_slots='{"a": "amount_total", "b": "__count"}',
                rule_ids=[
                    (0, 0, {"operator": "<", "compare_type": "constant", "compare_value": 10, "status": "red"}),
                    (0, 0, {"operator": ">=", "compare_type": "yty", "status": "green"}),
                ],
            )
        )
        config = widget._to_config()
        for key in (
            "formula_mode",
            "formula_type",
            "formula_slots",
            "formula_expression",
            "formula_id",
            "visible_expression",
            "formula_basis",
            "delta_basis",
            "default_status",
            "rule_ids",
        ):
            self.assertIn(key, config)
        for name in ("threshold_mode", "warning_value", "critical_value"):
            self.assertNotIn(name, config)
        self.assertEqual(config["formula_expression"], "a / b")
        self.assertEqual(len(config["rule_ids"]), 2)
        self.assertEqual(config["rule_ids"][0]["status"], "red")
        self.assertTrue(config["rule_ids"][0]["id"], "Existing rules keep their id for the builder.")

    def test_creating_a_widget_with_a_broken_formula_is_refused(self):
        with self.assertRaises(ValidationError):
            self.widget_model.create(
                self._base_values(
                    formula_mode="custom",
                    formula_expression="__import__('os').system('dir')",
                )
            )
        with self.assertRaises(ValidationError):
            self.widget_model.create(
                self._base_values(
                    formula_mode="preset",
                    formula_type="ratio",
                    formula_slots='{"a": "amount_total"}',
                )
            )

    def test_updating_a_widget_with_a_broken_formula_is_refused(self):
        widget = self.widget_model.create(self._base_values())
        with self.assertRaises(ValidationError):
            widget.write({"formula_mode": "custom", "formula_expression": "unknown_measure + 1"})

    def test_a_single_measure_widget_is_still_accepted(self):
        widget = self.widget_model.create(self._base_values())
        self.assertEqual(widget.formula_mode, "measure")
        self.assertEqual(widget.default_status, "green")
