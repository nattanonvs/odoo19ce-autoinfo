from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    project_job_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Project Job No. Sequence",
        check_company=True,
        help="Sequence for Job type projects. Prefix should be J + dept_code + %(y)s-",
    )
    project_pm_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Project PM No. Sequence",
        check_company=True,
        help="Sequence for Preventive Maintenance type projects. Prefix should be PM + dept_code + %(y)s-",
    )
    project_service_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Project Service No. Sequence",
        check_company=True,
        help="Sequence for Service type projects. Prefix should be S + dept_code + %(y)s-",
    )
