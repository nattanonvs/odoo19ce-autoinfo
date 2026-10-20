from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    od19_project_type_id = fields.Many2one(
        "od19.project.type",
        string="Project Category",
        domain=[("project_ok", "=", True)],
        tracking=True,
        ondelete="restrict",
        help="Business category of the project. The operational "
             "Sale/Service/PM/Job type (od19_project_type) is set by "
             "od19_project_document_sequence; the owning department "
             "(od19_department_id) is defined by od19_project_analytic.",
    )
    od19_responsible_person_ids = fields.Many2many(
        "hr.employee",
        "project_od19_responsible_rel",
        "project_id",
        "employee_id",
        string="Responsible Persons",
        tracking=True,
    )
    od19_coordinator_ids = fields.Many2many(
        "hr.employee",
        "project_od19_coordinator_rel",
        "project_id",
        "employee_id",
        string="Coordinators",
        tracking=True,
    )
    od19_scope_of_work = fields.Text(
        string="Scope of Work",
        tracking=True,
    )
    od19_document_requirements = fields.Text(
        string="Document Requirements",
        tracking=True,
    )

    def _od19_get_pnl_values(self, date_from=None, date_to=None, company_ids=None):
        """Return project P&L values read from posted analytic lines.

        Single P&L contract for the whole domain (spec 6.6): revenue/cost are
        derived from account.analytic.line.analytic_profitability, which Odoo 19
        computes from the general account type. Never re-implement the
        revenue/cost classification here.
        """
        self.ensure_one()
        company_ids = company_ids or self.env.companies.ids
        result = {
            "analytic_account_id": self.account_id.id or False,
            "has_analytic": bool(self.account_id),
            "revenue": 0.0,
            "cost": 0.0,
            "gross_margin": 0.0,
            "margin_percent": 0.0,
            "uncategorized_amount": 0.0,
        }
        if not self.account_id:
            return result
        base_domain = [
            ("account_id", "=", self.account_id.id),
            ("company_id", "in", list(company_ids)),
            ("move_line_id", "!=", False),
            ("move_line_id.parent_state", "=", "posted"),
        ]
        if date_from:
            base_domain.append(("date", ">=", date_from))
        if date_to:
            base_domain.append(("date", "<=", date_to))

        def _sum(profitability):
            lines = self.env["account.analytic.line"].search(
                base_domain + [("analytic_profitability", "in", [profitability])]
            )
            return sum(lines.mapped("amount"))

        revenue = _sum("revenue")
        cost = -_sum("loss")
        result.update(
            revenue=revenue,
            cost=cost,
            gross_margin=revenue - cost,
            margin_percent=(revenue - cost) / revenue * 100.0 if revenue else 0.0,
            uncategorized_amount=_sum("uncategorized"),
        )
        return result
