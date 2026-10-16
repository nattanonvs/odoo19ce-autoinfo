from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Operators allowed in the left-hand comparison of a status rule.
OPERATORS = [
    (">", "Greater than"),
    (">=", "Greater than or equal"),
    ("<", "Less than"),
    ("<=", "Less than or equal"),
    ("==", "Equal to"),
    ("!=", "Not equal to"),
]

#: Right-hand operand of a status rule.
COMPARE_TYPES = [
    ("constant", "Constant value"),
    ("goal", "Goal"),
    ("percent_of_goal", "Percent of goal"),
    ("widget", "Another widget"),
    ("prev", "Previous period"),
    ("yty", "Same period last year"),
    ("mtm", "Previous month"),
    ("qtq", "Previous quarter"),
]

#: Status colours shared with the KPI baseline.
STATUSES = [
    ("red", "Red"),
    ("yellow", "Yellow"),
    ("green", "Green"),
    ("grey", "Grey"),
]

#: Compare types that need the widget value of a shifted period.
PERIOD_COMPARE_TYPES = ("prev", "yty", "mtm", "qtq")


class Od19DashboardWidgetRule(models.Model):
    """One row of a widget status table.

    The left-hand side of every comparison is always the value of the widget
    that owns the rule; the right-hand side is selected through
    ``compare_type``. Rules are evaluated top to bottom and the first match
    wins, which is why the model is ordered by ``sequence`` then ``id``.
    """

    _name = "od19.dashboard.widget.rule"
    _description = "Dashboard Widget Status Rule"
    _order = "sequence, id"

    widget_id = fields.Many2one(
        "od19.dashboard.widget",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(help="Short label shown in the rule table, e.g. 'Below 20% of goal'.")
    active = fields.Boolean(default=True)

    operator = fields.Selection(selection=OPERATORS, required=True, default="<=")
    compare_type = fields.Selection(
        selection=COMPARE_TYPES,
        required=True,
        default="constant",
    )
    compare_value = fields.Float(help="Used when the compare type is a constant value.")
    compare_percent = fields.Float(
        help="Used with 'Percent of goal': 80 means 80% of the widget goal.",
    )
    compare_widget_id = fields.Many2one(
        "od19.dashboard.widget",
        ondelete="cascade",
        string="Compare with",
    )
    status = fields.Selection(selection=STATUSES, required=True, default="red")

    @api.constrains("widget_id", "compare_widget_id")
    def _check_compare_widget(self):
        for rule in self:
            if not rule.compare_widget_id or not rule.widget_id:
                continue
            if rule.compare_widget_id == rule.widget_id:
                raise ValidationError(
                    _("A status rule cannot compare a widget with itself (rule: %s).")
                    % (rule.name or rule.id)
                )
            if rule.compare_widget_id.dashboard_id != rule.widget_id.dashboard_id:
                raise ValidationError(
                    _("A status rule can only compare widgets of the same dashboard (rule: %s).")
                    % (rule.name or rule.id)
                )

    @api.constrains("compare_type", "compare_widget_id", "compare_percent")
    def _check_compare_target(self):
        for rule in self:
            label = rule.name or rule.id
            if rule.compare_type == "widget" and not rule.compare_widget_id:
                raise ValidationError(
                    _("Choose the widget to compare with (rule: %s).") % label
                )
            if rule.compare_type == "percent_of_goal" and not rule.compare_percent:
                raise ValidationError(
                    _("Set the percentage of the goal to compare with (rule: %s).") % label
                )
