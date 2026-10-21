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

    # _od19_get_pnl_values() lives in od19_project_analytic (the shared
    # project/analytic base) and is inherited here; see that module. Do not
    # re-implement the revenue/cost classification.
