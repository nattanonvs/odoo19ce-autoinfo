from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Od19SalesProject(models.Model):
    _name = "od19.sales.project"
    _description = "Sales Project Context"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    project_owner_id = fields.Many2one("res.partner", required=True, tracking=True)
    contractor_ids = fields.Many2many("res.partner", string="Known Contractors")
    active = fields.Boolean(default=True)

    @api.constrains("project_owner_id", "contractor_ids")
    def _check_partner_roles(self):
        for project in self:
            if (
                project.project_owner_id
                and not project.project_owner_id.od19_is_project_owner
            ):
                raise ValidationError(
                    "Project owner must have the Project Owner role."
                )

            invalid_contractors = project.contractor_ids.filtered(
                lambda partner: not partner.od19_is_contractor
            )
            if invalid_contractors:
                raise ValidationError(
                    "All contractors must have the Contractor role."
                )
