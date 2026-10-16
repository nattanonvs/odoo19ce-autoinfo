from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models import dashboard_formula as fx


class TestDashboardFormula(TransactionCase):
    def test_preset_expressions(self):
        cases = {
            "ratio": {"a": "x", "b": "y"},
            "difference": {"a": "x", "b": "y"},
            "growth": {"a": "x", "b": "y"},
            "share": {"a": "x"},
            "percent_of_goal": {"a": "x"},
            "min": {"a": "x", "b": "y"},
            "max": {"a": "x", "b": "y"},
            "conversion_rate": {"a": "x", "b": "y"},
            "variance": {"a": "x", "b": "y"},
            "weighted_average": {"a": "x", "b": "y", "w1": 2, "w2": 1},
            "run_rate": {"a": "x"},
            "cumulative_change": {"a": "x"},
        }
        for formula_type, slots in cases.items():
            expression = fx.build_preset_expression(formula_type, slots)
            self.assertTrue(expression.strip(), formula_type)

    def test_preset_sum_and_average_follow_bound_slots(self):
        self.assertEqual(fx.build_preset_expression("sum", {"a": "x", "b": "y", "c": "z"}), "a + b + c")
        self.assertEqual(fx.build_preset_expression("average", {"a": "x", "b": "y"}), "(a + b) / 2")
        self.assertEqual(fx.build_preset_expression("average", {"a": "x"}), "(a) / 1")

    def test_preset_unknown_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            fx.build_preset_expression("does_not_exist", {"a": "x"})

    def test_validate_accepts_allowed_names(self):
        fx.validate_expression(
            "(a - b) / b * 100",
            {"a", "b", "count_records", "goal"},
        )
        fx.validate_expression("min(a, b) + max(goal, 0)", {"a", "b", "goal"})

    def test_validate_rejects_unknown_name(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a / secret", {"a"})

    def test_validate_rejects_dunder_count(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("__count / a", {"a", "count_records"})

    def test_validate_rejects_attribute_access(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a.real", {"a"})

    def test_validate_rejects_disallowed_call(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("open(a)", {"a"})

    def test_validate_rejects_import(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("__import__('os').getcwd()", {"a"})

    def test_validate_rejects_syntax_error(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a /", {"a"})

    def test_evaluate_expression(self):
        context = {"a": 10.0, "b": 4.0, "goal": 100.0, "count_records": 3.0}
        self.assertAlmostEqual(fx.evaluate_expression("a / b", context), 2.5)
        self.assertAlmostEqual(fx.evaluate_expression("(a - b) / b * 100", context), 150.0)
        self.assertAlmostEqual(fx.evaluate_expression("min(a, b)", context), 4.0)

    def test_evaluate_expression_raises_on_zero_division(self):
        with self.assertRaises(ZeroDivisionError):
            fx.evaluate_expression("a / b", {"a": 1.0, "b": 0.0})

    def test_compare_values(self):
        self.assertTrue(fx.compare_values(1.0, "<=", 1.0))
        self.assertTrue(fx.compare_values(2.0, ">", 1.0))
        self.assertTrue(fx.compare_values(1.0, "==", 1.0))
        self.assertTrue(fx.compare_values(1.0, "!=", 2.0))
        self.assertFalse(fx.compare_values(2.0, "<", 1.0))

    def test_shift_previous_keeps_period_length(self):
        start, end = fx.apply_shift(date(2026, 3, 5), date(2026, 3, 16), "previous")
        self.assertEqual((start, end), (date(2026, 2, 21), date(2026, 3, 4)))

    def test_shift_yty_handles_leap_day(self):
        start, end = fx.apply_shift(date(2024, 2, 29), date(2024, 3, 5), "yty")
        self.assertEqual((start, end), (date(2023, 2, 28), date(2023, 3, 5)))

    def test_shift_mtm_snaps_month_end(self):
        start, end = fx.apply_shift(date(2026, 3, 1), date(2026, 3, 31), "mtm")
        self.assertEqual((start, end), (date(2026, 2, 1), date(2026, 2, 28)))

    def test_shift_qtq_uses_previous_quarter(self):
        start, end = fx.apply_shift(date(2026, 4, 1), date(2026, 6, 30), "qtq")
        self.assertEqual((start, end), (date(2026, 1, 1), date(2026, 3, 31)))

    def test_operand_names_helper(self):
        names = fx.expression_names("a + count_records / goal")
        self.assertEqual(names, {"a", "count_records", "goal"})
        self.assertEqual(fx.expression_names("a /"), set())

    def test_operand_names_skip_function_names(self):
        self.assertEqual(fx.expression_names("min(a, b)"), {"a", "b"})
        self.assertEqual(fx.expression_names("abs(a - b) * round(goal)"), {"a", "b", "goal"})

    def test_preset_catalogue_is_complete(self):
        self.assertEqual(len(fx.FORMULA_TYPES), 14)
        self.assertEqual(
            {key for key, _label in fx.FORMULA_TYPES},
            set(fx.PRESET_REQUIRED_SLOTS),
        )

    def test_every_preset_type_builds_an_expression(self):
        for formula_type, _label in fx.FORMULA_TYPES:
            required = fx.PRESET_REQUIRED_SLOTS[formula_type]
            slots = {key: "x" for key in required if key in fx.SLOT_KEYS}
            slots.update({key: 1 for key in required if key in fx.WEIGHT_KEYS})
            self.assertTrue(
                fx.build_preset_expression(formula_type, slots).strip(),
                formula_type,
            )

    def test_preset_sum_and_average_without_slots_return_zero(self):
        self.assertEqual(fx.build_preset_expression("sum", {}), "0")
        self.assertEqual(fx.build_preset_expression("average", {}), "0")
        self.assertEqual(fx.build_preset_expression("cumulative_change", {}), "0")

    def test_validate_rejects_subscript_comprehension_and_lambda(self):
        for expression in ("a[0]", "[x for x in a]", "lambda: 1"):
            with self.assertRaises(ValidationError, msg=expression):
                fx.validate_expression(expression, {"a", "x"})

    def test_validate_rejects_power(self):
        with self.assertRaises(ValidationError):
            fx.validate_expression("a ** b", {"a", "b"})

    def test_compare_values_returns_false_on_none(self):
        self.assertFalse(fx.compare_values(None, "<", 1.0))
        self.assertFalse(fx.compare_values(1.0, "<", None))
