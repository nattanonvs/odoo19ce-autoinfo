from odoo import fields, models

from . import dashboard_formula as formula_tools


class Od19DashboardFormula(models.Model):
    """A named formula a designer can reuse across widgets and dashboards.

    The expression is evaluated with the same ``safe_eval`` engine as a
    custom widget expression. Every name the expression uses (and that is not
    an implicit name or a whitelisted function) becomes a *slot* the widget
    binding the formula has to fill in, which is what the builder shows as the
    slot table.
    """

    _name = "od19.dashboard.formula"
    _description = "Dashboard Named Formula"
    _order = "name, id"

    name = fields.Char(required=True)
    expression = fields.Char(
        required=True,
        help="Expression evaluated by the dashboard formula engine, e.g. 'a / b * 100'.",
    )
    description = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _name_company_default = models.Constraint(
        "unique(name, company_id)",
        "A named formula with this name already exists for this company.",
    )

    def _to_meta(self):
        """Return the formula as the builder dialog expects it."""
        self.ensure_one()
        names = formula_tools.expression_names(self.expression)
        names -= set(formula_tools.IMPLICIT_NAMES)
        names -= set(formula_tools.ALLOWED_CALLS)
        return {
            "id": self.id,
            "name": self.name,
            "expression": self.expression,
            "description": self.description or "",
            "names": sorted(names),
        }
