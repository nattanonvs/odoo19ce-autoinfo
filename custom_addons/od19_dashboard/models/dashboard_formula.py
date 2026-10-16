"""Pure helpers backing the dashboard formula engine.

Nothing in this module touches the ORM: it accepts plain values so the
formula semantics can be unit tested without a database. ``dashboard.py``
owns the orchestration (read groups, cross widget ordering, fail-soft).
"""

import ast
import calendar
from datetime import date, timedelta

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

#: Preset formula labels exposed to the builder.
FORMULA_TYPES = [
    ("ratio", "Ratio (A ÷ B)"),
    ("difference", "Difference (A − B)"),
    ("growth", "Growth %"),
    ("share", "Share %"),
    ("sum", "Sum"),
    ("average", "Average"),
    ("weighted_average", "Weighted Average"),
    ("percent_of_goal", "% of Goal"),
    ("min", "Min"),
    ("max", "Max"),
    ("cumulative_change", "Cumulative Change"),
    ("run_rate", "Run Rate"),
    ("conversion_rate", "Conversion Rate"),
    ("variance", "Variance"),
]

#: Simple slot formulas; ``sum``, ``average`` and ``cumulative_change`` are built dynamically.
PRESET_EXPRESSIONS = {
    "ratio": "a / b",
    "difference": "a - b",
    "growth": "(a - b) / b * 100",
    "share": "a / total_a * 100",
    "weighted_average": "(a * w1 + b * w2) / (w1 + w2)",
    "percent_of_goal": "a / goal * 100",
    "min": "min(a, b)",
    "max": "max(a, b)",
    "run_rate": "a * days_in_period / days_elapsed",
    "conversion_rate": "a / b * 100",
    "variance": "abs(a - b)",
}

#: Slots a preset formula cannot run without.
PRESET_REQUIRED_SLOTS = {
    "ratio": ("a", "b"),
    "difference": ("a", "b"),
    "growth": ("a", "b"),
    "share": ("a",),
    "sum": ("a", "b"),
    "average": ("a", "b"),
    "weighted_average": ("a", "b", "w1", "w2"),
    "percent_of_goal": ("a",),
    "min": ("a", "b"),
    "max": ("a", "b"),
    "cumulative_change": ("a",),
    "run_rate": ("a",),
    "conversion_rate": ("a", "b"),
    "variance": ("a", "b"),
}

#: Measure slots, in the order used to build the sum / average expressions.
SLOT_KEYS = ("a", "b", "c", "d", "e")
WEIGHT_KEYS = ("w1", "w2")
ALL_SLOT_KEYS = SLOT_KEYS + WEIGHT_KEYS

#: Alias of ``__count``: safe_eval forbids any name containing two underscores.
COUNT_ALIAS = "count_records"

#: Builtin functions a formula may call (all present in safe_eval._BUILTINS).
ALLOWED_CALLS = frozenset({"min", "max", "abs", "round"})

#: Builtin names implicitly exposed to every formula.
IMPLICIT_NAMES = frozenset({"goal", "total_a", "days_in_period", "days_elapsed", COUNT_ALIAS})

ALLOWED_NODES = (
    ast.Expression,
    ast.Name,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
)


def build_preset_expression(formula_type, slots):
    """Return the expression a preset formula stands for.

    ``slots`` maps a slot key to a measure key (string) or to a weight
    (number). Only the slots actually bound by the user are used, so
    ``sum`` and ``average`` follow what the user filled in.
    """
    bound = [key for key in SLOT_KEYS if key in slots]
    if formula_type == "sum":
        return " + ".join(bound) if bound else "0"
    if formula_type == "average":
        return "(%s) / %s" % (" + ".join(bound), len(bound)) if bound else "0"
    if formula_type == "cumulative_change":
        return bound[0] if bound else "0"
    expression = PRESET_EXPRESSIONS.get(formula_type)
    if expression is None:
        raise ValidationError(_("Unknown preset formula '%s'.") % formula_type)
    return expression


def expression_names(expression):
    """Return the ``Name`` identifiers used by ``expression`` (empty on syntax error)."""
    try:
        tree = ast.parse(expression or "", mode="eval")
    except SyntaxError:
        return set()
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def validate_expression(expression, allowed_names):
    """Validate the syntax, the AST shape and the names of a custom expression.

    Only arithmetic, comparisons, boolean logic and the four whitelisted
    builtins are accepted; attribute access, subscripts, comprehensions,
    lambdas and imports are rejected.
    """
    try:
        tree = ast.parse(expression or "", mode="eval")
    except SyntaxError as error:
        raise ValidationError(
            _("The formula is not a valid expression: %s") % error
        ) from error

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS:
                raise ValidationError(
                    _("Only the functions %s can be used in a formula.")
                    % ", ".join(sorted(ALLOWED_CALLS))
                )
            continue
        if isinstance(node, ast.Name):
            if node.id in ALLOWED_CALLS:
                continue
            if node.id not in allowed_names:
                raise ValidationError(
                    _("Unknown name '%s' in the formula. Allowed names: %s.")
                    % (node.id, ", ".join(sorted(allowed_names)))
                )
            continue
        if isinstance(node, ALLOWED_NODES):
            continue
        raise ValidationError(
            _("The formula uses an unsupported construct: %s.") % type(node).__name__
        )
    return tree


def evaluate_expression(expression, context):
    """Evaluate ``expression`` with ``safe_eval`` and return ``float``.

    Raises the underlying arithmetic / name error so the caller can fail
    soft and explain the widget instead of breaking the dashboard.
    """
    result = safe_eval(expression, context)
    if isinstance(result, bool):
        return 1.0 if result else 0.0
    return float(result)


def compare_values(left, operator, right):
    """Apply the rule operator. Returns False when an operand is None."""
    if left is None or right is None:
        return False
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    return False


def shift_months(value, months):
    """Shift ``value`` by ``months``, clamping the day and snapping month ends."""
    total = (value.year * 12 + value.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    last_target = calendar.monthrange(year, month)[1]
    last_source = calendar.monthrange(value.year, value.month)[1]
    day = last_target if value.day == last_source else min(value.day, last_target)
    return value.replace(year=year, month=month, day=day)


def shift_years(value, years):
    """Shift ``value`` by ``years``; 29 February falls back to 28 February."""
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, month=2, day=28)


def apply_shift(start, end, shift):
    """Return the ``(start, end)`` bounds of the reference period ``shift``."""
    if not start or not end:
        return start, end
    if shift == "previous":
        length = (end - start).days + 1
        new_end = start - timedelta(days=1)
        return new_end - timedelta(days=length - 1), new_end
    if shift == "yty":
        return shift_years(start, 1), shift_years(end, 1)
    if shift == "mtm":
        return shift_months(start, -1), shift_months(end, -1)
    if shift == "qtq":
        return shift_months(start, -3), shift_months(end, -3)
    return start, end
