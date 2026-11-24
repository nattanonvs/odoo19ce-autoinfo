from odoo import _, api, fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    od19_project_ref = fields.Char(
        string="Project",
        compute="_compute_od19_project_ref",
        help="Human-readable reference to the project(s) linked to this "
             "analytic account, shown under the analytic name on the form.",
    )

    @api.depends("project_ids", "project_ids.job_no", "project_ids.name")
    def _compute_od19_project_ref(self):
        for analytic in self:
            projects = analytic.project_ids
            if not projects:
                analytic.od19_project_ref = False
            elif len(projects) == 1:
                project = projects[0]
                analytic.od19_project_ref = (
                    f"{project.job_no} · {project.name}"
                    if project.job_no
                    else project.name
                )
            else:
                analytic.od19_project_ref = _(
                    "%(count)s projects", count=len(projects)
                )
