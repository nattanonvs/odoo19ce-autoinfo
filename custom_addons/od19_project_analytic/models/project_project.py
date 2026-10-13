from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = "project.project"

    job_no = fields.Char(
        string="Job Number",
        copy=False,
        tracking=True,
        index=True,
    )
    job_type = fields.Selection(
        [
            ("construction", "Construction"),
            ("service", "Service"),
            ("supply", "Supply"),
            ("other", "Other"),
        ],
        string="Job Type",
        required=True,
        default="construction",
        tracking=True,
    )
    department = fields.Char(
        string="Department",
        tracking=True,
    )
    project_owner_id = fields.Many2one(
        "res.partner",
        string="Project Owner",
        tracking=True,
        domain="[('od19_is_project_owner', '=', True)]",
    )
    contractor_ids = fields.Many2many(
        "res.partner",
        "project_contractor_rel",
        "project_id",
        "partner_id",
        string="Contractors",
        domain="[('od19_is_contractor', '=', True)]",
    )

    _sql_constraints = [
        (
            "job_no_unique",
            "unique(job_no)",
            "Job Number must be unique.",
        ),
    ]

    @api.constrains("job_no")
    def _check_job_no_uniqueness(self):
        for project in self:
            if project.job_no:
                duplicate = self.search(
                    [("job_no", "=", project.job_no), ("id", "!=", project.id)],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError("Job Number must be unique.")

    @api.constrains("project_owner_id")
    def _check_project_owner_role(self):
        for project in self:
            if (
                project.project_owner_id
                and not project.project_owner_id.od19_is_project_owner
            ):
                raise ValidationError(
                    "Project owner must have the Project Owner role."
                )

    @api.constrains("contractor_ids")
    def _check_contractor_roles(self):
        for project in self:
            invalid = project.contractor_ids.filtered(
                lambda p: not p.od19_is_contractor
            )
            if invalid:
                raise ValidationError(
                    "All contractors must have the Contractor role."
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("job_no"):
                duplicate = self.search(
                    [("job_no", "=", vals.get("job_no"))], limit=1
                )
                if duplicate:
                    raise ValidationError("Job Number must be unique.")
            if not vals.get("account_id"):
                vals["account_id"] = self._create_analytic_account(vals).id
        return super().create(vals_list)

    def _create_analytic_account(self, vals):
        analytic_name = vals.get("job_no") or vals.get("name") or "Project"
        analytic = self.env["account.analytic.account"].create(
            {
                "name": analytic_name,
                "plan_id": self._get_default_analytic_plan_id(),
            }
        )
        return analytic

    @api.model
    def _get_default_analytic_plan_id(self):
        plan = self.env["account.analytic.plan"].search(
            [("name", "=", "Projects")], limit=1
        )
        if not plan:
            plan = self.env["account.analytic.plan"].search([], limit=1)
        return plan.id if plan else False
