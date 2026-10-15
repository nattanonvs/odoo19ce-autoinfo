from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    od19_project_type_id = fields.Many2one(
        "od19.project.type",
        string="Project Type",
        domain=[("project_ok", "=", True)],
        tracking=True,
        ondelete="restrict",
    )
    od19_department_id = fields.Many2one(
        "hr.department",
        string="Department",
        required=True,
        tracking=True,
        ondelete="restrict",
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
