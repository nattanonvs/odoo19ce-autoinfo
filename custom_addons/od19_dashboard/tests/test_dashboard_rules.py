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

    def test_rule_rejects_cross_dashboard_widget(self):
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
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": self.widget_a.id,
                    "compare_type": "widget",
                    "compare_widget_id": other_widget.id,
                    "status": "red",
                }
            )

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
